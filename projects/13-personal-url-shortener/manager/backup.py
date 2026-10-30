#!/usr/bin/env python3
"""
Snowfox Short Links Automated Local Backup Engine
Location: Proxmox LXC 225 (/opt/short-manager/backup.py)

Features:
1. Queries Cloudflare Edge REST API (/api/list) using master Bearer token.
2. Writes timestamped immutable JSON snapshots to /var/backups/short-links/snapshots/.
3. Atomically updates /var/backups/short-links/latest.json.
4. Synchronizes and tracks lifecycle in SQLite (/var/backups/short-links/short_links.sqlite)
   with soft-deletion tracking (is_active=0 for tombstoned slugs).
5. Rotates and prunes JSON snapshots older than retention days (default: 30 days).
6. CLI support for manual execution, status inspection, and list formatting.
7. Importable module for app.py to trigger backups or serve backup downloads.
"""

import os
import sys
import json
import sqlite3
import datetime
import argparse
import urllib.request
import urllib.error

ENV_FILE = os.environ.get("ENV_FILE", "/opt/short-manager/.env")
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/var/backups/short-links")
SNAPSHOT_DIR = os.path.join(BACKUP_DIR, "snapshots")
SQLITE_DB = os.path.join(BACKUP_DIR, "short_links.sqlite")
LATEST_JSON = os.path.join(BACKUP_DIR, "latest.json")
RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", 30))
USER_AGENT = "SnowfoxShortManager-vmbr1"


def load_env(env_path=ENV_FILE):
    """Load environment variables from .env file or fallback to os.environ."""
    env = {}
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip().strip('"').strip("'")
        except Exception as e:
            sys.stderr.write(f"Warning: could not read {env_path}: {e}\n")

    # Environment variables take precedence
    for k in ["CLOUDFLARE_WORKER_URL", "SHORTENER_SECRET_TOKEN"]:
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def init_db(db_path=SQLITE_DB):
    """Initialize local SQLite backup database schema."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS short_links (
            slug TEXT PRIMARY KEY,
            destination TEXT NOT NULL,
            title TEXT,
            clicks INTEGER DEFAULT 0,
            created_at TEXT,
            first_backed_up_at TEXT NOT NULL,
            last_synced_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backup_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            links_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            snapshot_path TEXT,
            error_message TEXT
        )
    """)
    conn.commit()
    return conn


def fetch_links_from_edge(worker_url, secret_token):
    """Retrieve all short links from the Cloudflare Worker edge API."""
    url = f"{worker_url.rstrip('/')}/api/list"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {secret_token}")
    req.add_header("User-Agent", USER_AGENT)

    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Edge API returned HTTP {resp.status}")
        raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        return data.get("links", [])


def prune_old_snapshots(snapshot_dir=SNAPSHOT_DIR, days=RETENTION_DAYS):
    """Remove snapshots older than the specified retention period."""
    if not os.path.exists(snapshot_dir):
        return 0
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    pruned = 0
    for fname in os.listdir(snapshot_dir):
        if fname.startswith("short_links_") and fname.endswith(".json"):
            fpath = os.path.join(snapshot_dir, fname)
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fpath), datetime.timezone.utc)
                if mtime < cutoff:
                    os.remove(fpath)
                    pruned += 1
            except Exception as e:
                sys.stderr.write(f"Warning: could not prune {fpath}: {e}\n")
    return pruned


def run_backup():
    """Execute a complete backup cycle: Edge fetch -> JSON snapshot -> SQLite upsert -> Retention prune."""
    env = load_env()
    worker_url = env.get("CLOUDFLARE_WORKER_URL", "https://short.snowfox.live")
    secret_token = env.get("SHORTENER_SECRET_TOKEN", "")

    if not secret_token:
        raise ValueError(f"SHORTENER_SECRET_TOKEN missing or empty in {ENV_FILE}")

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    conn = init_db()
    cur = conn.cursor()

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snapshot_filename = f"short_links_{timestamp_str}.json"
    snapshot_path = os.path.join(SNAPSHOT_DIR, snapshot_filename)

    try:
        links = fetch_links_from_edge(worker_url, secret_token)

        # 1. Write timestamped immutable JSON snapshot
        snapshot_payload = {
            "backup_version": 1,
            "created_at": now_iso,
            "total_links": len(links),
            "source": worker_url,
            "links": links
        }
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_payload, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # 2. Update latest.json atomically via temporary file
        tmp_latest = LATEST_JSON + ".tmp"
        with open(tmp_latest, "w", encoding="utf-8") as f:
            json.dump(snapshot_payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_latest, LATEST_JSON)

        # 3. Synchronize state into SQLite
        live_slugs = set()
        for link in links:
            slug = link.get("slug")
            if not slug:
                continue
            live_slugs.add(slug)
            dest = link.get("destination", "")
            title = link.get("title", "")
            clicks = link.get("clicks", 0)
            created_at = link.get("created_at", now_iso)

            cur.execute("""
                INSERT INTO short_links (slug, destination, title, clicks, created_at, first_backed_up_at, last_synced_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(slug) DO UPDATE SET
                    destination = excluded.destination,
                    title = excluded.title,
                    clicks = excluded.clicks,
                    last_synced_at = excluded.last_synced_at,
                    is_active = 1
            """, (slug, dest, title, clicks, created_at, now_iso, now_iso))

        # Mark soft-deleted links that exist in SQLite but no longer exist in KV
        if live_slugs:
            placeholders = ",".join("?" for _ in live_slugs)
            cur.execute(
                f"UPDATE short_links SET is_active = 0, last_synced_at = ? WHERE slug NOT IN ({placeholders}) AND is_active = 1",
                [now_iso] + list(live_slugs)
            )
        else:
            cur.execute("UPDATE short_links SET is_active = 0, last_synced_at = ? WHERE is_active = 1", (now_iso,))

        # Record successful backup audit entry
        cur.execute("""
            INSERT INTO backup_runs (run_at, links_count, status, snapshot_path, error_message)
            VALUES (?, ?, 'SUCCESS', ?, NULL)
        """, (now_iso, len(links), snapshot_path))
        conn.commit()

        # 4. Prune older snapshots
        pruned_count = prune_old_snapshots()

        print(f"[{now_iso}] Backup completed successfully:")
        print(f"  • Total active links: {len(links)}")
        print(f"  • Snapshot saved:     {snapshot_path}")
        print(f"  • Latest state:       {LATEST_JSON}")
        print(f"  • SQLite DB:          {SQLITE_DB}")
        if pruned_count > 0:
            print(f"  • Pruned {pruned_count} snapshots older than {RETENTION_DAYS} days.")

        return {
            "success": True,
            "created_at": now_iso,
            "total_links": len(links),
            "snapshot_path": snapshot_path,
            "latest_json": LATEST_JSON,
            "sqlite_db": SQLITE_DB,
            "pruned_snapshots": pruned_count
        }

    except Exception as e:
        now_err = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur.execute("""
            INSERT INTO backup_runs (run_at, links_count, status, snapshot_path, error_message)
            VALUES (?, 0, 'FAILURE', NULL, ?)
        """, (now_err, str(e)))
        conn.commit()
        sys.stderr.write(f"[{now_err}] Backup FAILED: {e}\n")
        raise
    finally:
        conn.close()


def get_backup_status():
    """Retrieve summary metadata about local backups for UI or CLI inspection."""
    status = {
        "configured": os.path.exists(ENV_FILE),
        "db_exists": os.path.exists(SQLITE_DB),
        "latest_json_exists": os.path.exists(LATEST_JSON),
        "last_run": None,
        "total_active_links": 0,
        "total_archived_links": 0,
        "total_snapshots": 0
    }

    if os.path.exists(SNAPSHOT_DIR):
        status["total_snapshots"] = len([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])

    if os.path.exists(SQLITE_DB):
        try:
            conn = sqlite3.connect(SQLITE_DB)
            cur = conn.cursor()
            cur.execute("SELECT run_at, links_count, status, error_message FROM backup_runs ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                status["last_run"] = {
                    "run_at": row[0],
                    "links_count": row[1],
                    "status": row[2],
                    "error_message": row[3]
                }
            cur.execute("SELECT SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END), COUNT(*) FROM short_links")
            counts = cur.fetchone()
            if counts:
                status["total_active_links"] = counts[0] or 0
                status["total_archived_links"] = counts[1] or 0
            conn.close()
        except Exception as e:
            status["db_error"] = str(e)

    return status


def print_list():
    """CLI helper to display tabular list of backed-up links with active/deleted status."""
    if not os.path.exists(SQLITE_DB):
        print(f"No SQLite database found at {SQLITE_DB}. Run a backup first.")
        return

    conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT slug, destination, title, clicks, is_active, last_synced_at
        FROM short_links
        ORDER BY is_active DESC, slug ASC
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No links found in local database.")
        return

    print(f"\n{'STATUS':<10} {'SLUG':<16} {'CLICKS':<8} {'TITLE':<25} {'DESTINATION'}")
    print("=" * 90)
    for slug, dest, title, clicks, is_active, last_synced in rows:
        status_str = "🟢 ACTIVE" if is_active else "🔴 DELETED"
        title_str = (title or "-")[:24]
        dest_str = dest if len(dest) <= 45 else dest[:42] + "..."
        print(f"{status_str:<10} {slug:<16} {clicks:<8} {title_str:<25} {dest_str}")
    print("=" * 90)
    active_count = sum(1 for r in rows if r[4])
    deleted_count = sum(1 for r in rows if not r[4])
    print(f"Total: {len(rows)} links (Active in KV: {active_count}, Historical Deleted Tombstones: {deleted_count})\n")


def print_status():
    """CLI helper to display health and run status."""
    st = get_backup_status()
    print("\n📦 Snowfox Short Links Backup Status:")
    print("=" * 50)
    print(f"Backup Directory:     {BACKUP_DIR}")
    print(f"SQLite DB Exists:     {st['db_exists']}")
    print(f"Latest JSON Exists:   {st['latest_json_exists']}")
    print(f"Stored Snapshots:     {st['total_snapshots']}")
    print(f"Active Links:         {st['total_active_links']}")
    print(f"Total Recorded Links: {st['total_archived_links']}")
    if st["last_run"]:
        lr = st["last_run"]
        print(f"Last Backup Run:      {lr['run_at']} ({lr['status']}, {lr['links_count']} links)")
        if lr["error_message"]:
            print(f"Last Error:           {lr['error_message']}")
    else:
        print("Last Backup Run:      None yet")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Snowfox Short Links Automated Backup Engine")
    parser.add_argument("--list", action="store_true", help="List all backed up links and their status")
    parser.add_argument("--status", action="store_true", help="Show backup system status and history")
    args = parser.parse_args()

    if args.list:
        print_list()
    elif args.status:
        print_status()
    else:
        try:
            res = run_backup()
            sys.exit(0)
        except Exception:
            sys.exit(1)
