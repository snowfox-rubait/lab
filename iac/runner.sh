#!/bin/sh
# Zero-dependency POSIX fleet verification & pyinfra runner helper
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VAULT_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 [check|status|pyinfra|help]"
    echo ""
    echo "Commands:"
    echo "  check    - Ping and verify SSH connectivity across all live fleet hosts"
    echo "  status   - Check running status of core homelab daemons (Fail2ban, WAN controller, Pi-hole)"
    echo "  pyinfra  - Run pyinfra fleet playbook (requires pyinfra installed in python env)"
    echo "  help     - Show this usage overview"
    exit 1
}

CMD="${1:-check}"

case "$CMD" in
    check)
        echo "=== [1/4] Checking Physical Router (192.168.1.1) ==="
        if ping -c 1 -W 1 192.168.1.1 >/dev/null 2>&1; then
            echo "  [OK] Router reachable. Testing SSH Dropbear..."
            ssh -q -o BatchMode=yes -o ConnectTimeout=3 router "echo '  [OK] Router SSH authenticated. OS: '\$(cat /etc/openwrt_release | grep DISTRIB_DESCRIPTION | cut -d= -f2)" || echo "  [FAIL] Router SSH failed"
        else
            echo "  [FAIL] Router 192.168.1.1 unreachable"
        fi

        echo ""
        echo "=== [2/4] Checking Proxmox Host (192.168.1.2) ==="
        if ping -c 1 -W 1 192.168.1.2 >/dev/null 2>&1; then
            echo "  [OK] Proxmox reachable. Testing SSH..."
            ssh -q -o BatchMode=yes -o ConnectTimeout=3 proxmox "echo '  [OK] Proxmox SSH authenticated. Kernel: '\$(uname -r)" || echo "  [FAIL] Proxmox SSH failed"
        else
            echo "  [FAIL] Proxmox 192.168.1.2 unreachable"
        fi

        echo ""
        echo "=== [3/4] Checking WAN Controller (192.168.1.130) ==="
        if curl -s -m 2 http://192.168.1.130/api/status >/dev/null 2>&1; then
            echo "  [OK] WAN Controller HTTP API responding on :80"
        else
            echo "  [WARN] WAN Controller HTTP API not responding (Container sleeping or stopping?)"
        fi

        echo ""
        echo "=== [4/4] Checking Pi-hole Sinkhole (192.168.1.135) ==="
        if ping -c 1 -W 1 192.168.1.135 >/dev/null 2>&1; then
            echo "  [OK] Pi-hole container reachable on 192.168.1.135"
        else
            echo "  [WARN] Pi-hole unreachable (Server sleep schedule active?)"
        fi
        ;;

    status)
        echo "=== Proxmox Fail2ban Status ==="
        ssh proxmox "fail2ban-client status" 2>/dev/null || echo "Unable to query Fail2ban"
        echo ""
        echo "=== WAN Controller Status ==="
        curl -s http://192.168.1.130/api/status | grep -A 5 "output" || echo "Unable to query WAN Controller"
        ;;

    pyinfra)
        if command -v pyinfra >/dev/null 2>&1; then
            echo "Executing pyinfra fleet orchestration..."
            pyinfra "$SCRIPT_DIR/inventory.py" "$SCRIPT_DIR/playbook.py"
        else
            echo "Error: pyinfra is not installed in the current environment."
            echo "Install via: pip install pyinfra"
            exit 1
        fi
        ;;

    *)
        usage
        ;;
esac
