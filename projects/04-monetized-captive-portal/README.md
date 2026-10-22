# 📡 Project 04: Monetized OpenWrt Captive Portal & Wi-Fi Billing Architecture

> **Project ID:** `04-monetized-captive-portal`  
> **Target Devices:** TP-Link Archer C6 v3 (OpenWrt 25.12.6) / OpenWrt VM 100  
> **Status:** Architecture & Requirements Specification Phase  
> **Business Model:** Paid Subscription Wi-Fi with bKash/Nagad MFS Billing & Multi-Device Bandwidth Pool

---

## 🎯 1. Core Vision & Concept

- **Free, Open Access at Layer 2:** 
  The guest Wi-Fi network is passwordless (or utilizes OWE Enhanced Open). Anyone can connect immediately without needing a pre-shared Wi-Fi key.
- **Strict Quarantine by Default (Zero Trust):** 
  Upon association, the device receives a local DHCP lease in an isolated guest zone. It has:
  - ❌ **No Internet access.**
  - ❌ **No access to LAN / local homelab devices** (client isolation enabled; layer-2 communication between connected phones/PCs blocked).
  - ✅ **Access ONLY to the router's local Captive Portal splash page & DNS.**
- **Automatic Splash Interception:**
  Connecting triggers the native Android / iOS / Windows captive portal detection (`connectivitycheck.gstatic.com`, `captive.apple.com`), immediately popping open the subscription portal.

---

## 📱 2. User Journey & Self-Management Flow

```
[ User Connects to Free Wi-Fi ]
               │
               ▼ (Automatic Captive Detection)
[ Captive Portal Splash Page ]
               │
       ┌───────┴───────┐
       ▼               ▼
[ New User Sign-Up ]   [ Returning User Login ]
   │ (Phone Number)        │ (Phone Number + SMS OTP)
   ▼                       ▼
[ SMS OTP Verification ]   [ Self-Management Dashboard ]
   │
   ▼
[ Plan Selection & Payment ]
   ├─ Choose Bandwidth Package (e.g. 5 Mbps, 10 Mbps, 20 Mbps)
   ├─ Standard Validity: 31 Days (Monthly Subscription)
   ├─ Payment Instructions: Send money to specified bKash / Nagad Number
   └─ Input Transaction ID (TrxID)
               │
               ▼ (Verification & Activation)
[ User Self-Service Dashboard (Active Plan) ]
   ├─ Active Plan & Speed
   ├─ Expiration Date countdown (31-day timer)
   └─ 🖧 Connected Devices Hub (Up to 5 MAC addresses)
```

---

## 🖧 3. Multi-Device MAC Pooling & Bandwidth Splitting

A single customer subscription covers a household/personal pool of up to **5 devices**:
- **Automatic Current Device Detection:** The portal detects the current connecting device's MAC address automatically.
- **Self-Service MAC Registry:** 
  Inside the user dashboard, the customer can add, label, edit, and remove up to 5 device MAC addresses (e.g., *My Phone, Sister's Phone, Laptop, Android TV*).
- **Dynamic Bandwidth Distribution:**
  The total bandwidth package purchased by the user (e.g. 10 Mbps) is dynamically shared/shaped across their registered active MAC addresses using OpenWrt traffic control / SQM / nftables.
- **Hardware-Level Firewall Whitelisting:**
  When a MAC is active under an unexpired plan, the router firewall whitelists the MAC, granting full outbound WAN routing. When the 31-day plan expires, the MACs automatically fall back into quarantine.

---

## 🏗️ 4. Technical Architecture Components

```
+───────────────────────────────────────────────────────────────+
|                  OpenWrt Router (Archer C6)                   |
|                                                               |
|  [ Guest Wi-Fi Interface ] (Isolated Subnet: 192.168.10.0/24) |
|               │                                               |
|               ▼                                               |
|     openNDS / FAS Engine (Forward Authentication Service)      |
|               │                                               |
|               ▼ (Captive redirect to API/Portal)              |
+───────────────┼───────────────────────────────────────────────+
                │
                ▼ (Internal LAN / Tailscale / Safe Zone)
+───────────────────────────────────────────────────────────────+
|         Portal Backend & Management Engine (Proxmox LXC)       |
|                                                               |
|  - Web Portal: Fast, mobile-optimized responsive web UI      |
|  - SMS Gateway: Bangladesh SMS API for OTP verification       |
|  - MFS Ingest: bKash / Nagad TrxID verification engine        |
|  - Database: User accounts, plan timers, registered MACs      |
|              (Supabase / Neon / Local Postgres)               |
|  - Controller: Calls OpenWrt ubus / ndsctl API to allow/      |
|               revoke MACs and configure SQM bandwidth limits  |
+───────────────────────────────────────────────────────────────+
```

---

## 📋 5. Architectural Building Blocks & Work Items

### 5.1 OpenWrt Router Engine
- **Captive Portal Daemon:** `openNDS` using its FAS (Forwarding Authentication Service) mode. This offloads the heavy portal logic, database, and SMS handling to our Proxmox server while keeping the router lean.
- **Firewall Isolation:** Isolated guest zone (`guest`) with client-to-client isolation (`isolate 1`) and drop rules targeting `lan` and `safe`.

### 5.2 Portal Backend & Database
- **Auth:** Phone number + SMS OTP verification.
- **Database Schema:**
  - `users`: Phone number, account status, created_at.
  - `subscriptions`: User ID, bandwidth tier (Mbps), start_date, expires_at (31-day calculation), trx_id, payment_status.
  - `devices`: User ID, MAC address, device_name, is_active (limit 5 per user).
- **Payment Verification:** Manual TrxID approval via Admin Telegram Alert or automated bKash Merchant webhook.

### 5.3 Bandwidth Limiting & Shaping
- Application of dynamic per-user rate limiting (e.g., cake / fq_codel SQM or nftables meter) so the user's combined active devices share their allocated quota.
