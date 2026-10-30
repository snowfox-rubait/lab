/**
 * Cloudflare Worker for Personal URL Shortener (short.snowfox.live)
 * 
 * Features:
 * 1. Strict Bangladesh-Only Geo-Fence for public redirection (request.cf.country === 'BD')
 * 2. High-performance KV lookup (<15ms response time globally / edge-cached)
 * 3. Token-authenticated REST API for private vmbr1 management UI (/api/*)
 * 4. 24/7/365 edge availability independent of homelab power schedule
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const country = request.cf?.country || "UNKNOWN";
    const userAgent = request.headers.get("User-Agent") || "";

    // ─────────────────────────────────────────────────────────────────────────
    // 1. Authenticated Management API Routes (/api/*)
    // ─────────────────────────────────────────────────────────────────────────
    if (url.pathname.startsWith("/api/")) {
      const authHeader = request.headers.get("Authorization");
      const expectedToken = env.SHORTENER_SECRET_TOKEN;

      // Ensure secret token is configured
      if (!expectedToken) {
        return new Response(JSON.stringify({ error: "Server misconfiguration: SHORTENER_SECRET_TOKEN is not set" }), {
          status: 500,
          headers: { "Content-Type": "application/json" }
        });
      }

      // Verify Bearer Token
      if (!authHeader || authHeader !== `Bearer ${expectedToken}`) {
        return new Response(JSON.stringify({ error: "Unauthorized: Invalid or missing Bearer token" }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        });
      }

      // POST /api/shorten -> Create or update a short link
      if (request.method === "POST" && url.pathname === "/api/shorten") {
        try {
          const body = await request.json();
          let { slug, destination, title } = body;

          if (!destination || typeof destination !== "string") {
            return new Response(JSON.stringify({ error: "Missing or invalid 'destination' URL" }), {
              status: 400,
              headers: { "Content-Type": "application/json" }
            });
          }

          // Ensure destination is a valid URL
          if (!destination.startsWith("http://") && !destination.startsWith("https://")) {
            destination = "https://" + destination;
          }

          try {
            new URL(destination);
          } catch {
            return new Response(JSON.stringify({ error: "Destination must be a valid HTTP/HTTPS URL" }), {
              status: 400,
              headers: { "Content-Type": "application/json" }
            });
          }

          // Auto-generate slug if not specified
          if (!slug || slug.trim() === "") {
            slug = generateRandomSlug(6);
          } else {
            slug = slug.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "-").slice(0, 100);
          }

          // Reserved API slugs
          if (["api", "admin", "health", "favicon.ico", "robots.txt"].includes(slug)) {
            return new Response(JSON.stringify({ error: `Slug '${slug}' is reserved` }), {
              status: 400,
              headers: { "Content-Type": "application/json" }
            });
          }

          // Cloudflare Workers KV enforces a strict 1024-byte limit on metadata JSON.
          // For long URLs (> 400 chars), store a preview in metadata and set truncated: true.
          // The full URL is always preserved without loss in the 25 MiB KV value.
          const isTruncated = destination.length > 400;
          const metadata = {
            title: title ? String(title).slice(0, 100) : "",
            destination: isTruncated ? destination.slice(0, 400) : destination,
            truncated: isTruncated,
            created_at: new Date().toISOString(),
            clicks: 0
          };

          // Store in Cloudflare KV (full destination preserved in value)
          await env.SHORT_LINKS.put(slug, destination, { metadata });

          const shortUrl = `${url.origin}/${slug}`;
          return new Response(JSON.stringify({
            success: true,
            slug,
            short_url: shortUrl,
            destination,
            title: metadata.title,
            created_at: metadata.created_at
          }), {
            status: 201,
            headers: { "Content-Type": "application/json" }
          });
        } catch (err) {
          return new Response(JSON.stringify({ error: "Failed to process request", details: err.message }), {
            status: 500,
            headers: { "Content-Type": "application/json" }
          });
        }
      }

      // GET /api/list -> Retrieve all shortened links
      if (request.method === "GET" && url.pathname === "/api/list") {
        try {
          const listResponse = await env.SHORT_LINKS.list();
          const items = [];

          for (const key of listResponse.keys) {
            const meta = key.metadata || {};
            let destinationUrl = meta.destination || "";
            if (meta.truncated || !destinationUrl) {
              destinationUrl = (await env.SHORT_LINKS.get(key.name)) || destinationUrl;
            }

            items.push({
              slug: key.name,
              destination: destinationUrl,
              title: meta.title || "",
              created_at: meta.created_at || "Unknown",
              clicks: meta.clicks || 0,
              short_url: `${url.origin}/${key.name}`
            });
          }

          // Sort by newest first
          items.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

          return new Response(JSON.stringify({ success: true, count: items.length, links: items }), {
            status: 200,
            headers: { "Content-Type": "application/json" }
          });
        } catch (err) {
          return new Response(JSON.stringify({ error: "Failed to list keys", details: err.message }), {
            status: 500,
            headers: { "Content-Type": "application/json" }
          });
        }
      }

      // DELETE /api/delete/:slug -> Delete a shortened link
      if (request.method === "DELETE" && url.pathname.startsWith("/api/delete/")) {
        const slugToDelete = url.pathname.replace("/api/delete/", "").trim();
        if (!slugToDelete) {
          return new Response(JSON.stringify({ error: "Missing slug to delete" }), {
            status: 400,
            headers: { "Content-Type": "application/json" }
          });
        }

        await env.SHORT_LINKS.delete(slugToDelete);
        return new Response(JSON.stringify({ success: true, message: `Slug '${slugToDelete}' deleted` }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }

      return new Response(JSON.stringify({ error: "API endpoint not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" }
      });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 2. Strict Bangladesh-Only Geo-Fence for Public Traffic
    // ─────────────────────────────────────────────────────────────────────────
    if (country !== "BD") {
      return renderGeoBlockedResponse(country);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 3. Public Redirection Engine (GET /:slug)
    // ─────────────────────────────────────────────────────────────────────────
    const slug = url.pathname.slice(1).trim();

    // Root URL redirect to main portfolio / website
    if (!slug) {
      return Response.redirect("https://snowfox.live", 302);
    }

    // Favicon & robots ignore
    if (slug === "favicon.ico" || slug === "robots.txt") {
      return new Response(null, { status: 404 });
    }

    // Lookup destination in KV
    const record = await env.SHORT_LINKS.getWithMetadata(slug);

    if (record && record.value) {
      // Return fast HTTP 302 redirect
      return Response.redirect(record.value, 302);
    }

    // 404 Not Found Page
    return renderNotFoundResponse(slug);
  }
};

/**
 * Helper to generate random alphanumeric slug
 */
function generateRandomSlug(length = 6) {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let result = "";
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Geo-fence 403 Forbidden Response
 */
function renderGeoBlockedResponse(detectedCountry) {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>403 Forbidden - Access Restricted</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card: #111827;
      --border: #1f2937;
      --text: #f9fafb;
      --muted: #9ca3af;
      --accent: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1.5rem; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 2.5rem; max-width: 500px; text-align: center; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }
    .badge { display: inline-flex; align-items: center; gap: 0.5rem; background: rgba(239, 68, 68, 0.15); color: var(--accent); padding: 0.35rem 0.85rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; margin-bottom: 1.5rem; border: 1px solid rgba(239, 68, 68, 0.3); }
    h1 { font-size: 1.75rem; margin-bottom: 0.75rem; font-weight: 700; }
    p { color: var(--muted); line-height: 1.6; font-size: 0.95rem; margin-bottom: 1.75rem; }
    .footer { font-size: 0.8rem; color: #4b5563; border-top: 1px solid var(--border); padding-top: 1.25rem; }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">
      <span>🚫</span> Geographic Restriction
    </div>
    <h1>Access Restricted to Bangladesh</h1>
    <p>
      The owner of this link service has configured strict geographic access controls.
      This resource is only accessible to visitors connecting from within <strong>Bangladesh (BD)</strong>.
    </p>
    <div class="footer">
      Detected Region: <code>${detectedCountry}</code> · Snowfox Edge Security
    </div>
  </div>
</body>
</html>`;

  return new Response(html, {
    status: 403,
    headers: { "Content-Type": "text/html; charset=utf-8" }
  });
}

/**
 * 404 Not Found Response
 */
function renderNotFoundResponse(slug) {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>404 - Short Link Not Found</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card: #111827;
      --border: #1f2937;
      --text: #f9fafb;
      --muted: #9ca3af;
      --accent: #38bdf8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1.5rem; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 2.5rem; max-width: 480px; text-align: center; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }
    h1 { font-size: 2rem; color: var(--accent); margin-bottom: 0.5rem; font-weight: 700; }
    p { color: var(--muted); line-height: 1.6; font-size: 0.95rem; margin-bottom: 1.5rem; }
    code { background: rgba(255,255,255,0.06); padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; color: #38bdf8; }
    a { display: inline-block; background: var(--accent); color: #000; text-decoration: none; padding: 0.65rem 1.25rem; border-radius: 8px; font-weight: 600; font-size: 0.9rem; transition: opacity 0.2s; }
    a:hover { opacity: 0.9; }
  </style>
</head>
<body>
  <div class="card">
    <h1>404</h1>
    <p>The short link <code>/${slug}</code> does not exist or has been removed by the owner.</p>
    <a href="https://snowfox.live">Return to Snowfox Home</a>
  </div>
</body>
</html>`;

  return new Response(html, {
    status: 404,
    headers: { "Content-Type": "text/html; charset=utf-8" }
  });
}
