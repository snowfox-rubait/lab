#!/bin/bash
# Fallback to Mode 1 (Physical Router Main) to ensure home WAN stays active
revert_wan_mode() {
    echo "Reverting router to Mode 1 (Physical Router Main)..."
    curl -s -m 8 -X POST "http://192.168.1.130/api/set" -H "Content-Type: application/json" -d '{"mode":"1"}' >/dev/null 2>&1 || true
}

# Homelab Power Management & Auto-Wake daemon script

# 1. Low Battery Protection (< 40% and Discharging)
BAT_CAP_FILE=/sys/class/power_supply/BAT0/capacity
BAT_STAT_FILE=/sys/class/power_supply/BAT0/status

if [ -f $BAT_CAP_FILE ] && [ -f $BAT_STAT_FILE ]; then
    CAP=$(cat $BAT_CAP_FILE)
    STAT=$(cat $BAT_STAT_FILE)
    if [ $STAT = Discharging ] && [ $CAP -le 40 ]; then
        wall CRITICAL POWER WARNING: Battery is at ${CAP}% discharging. Server will shut down in 2 minutes.
        revert_wan_mode
        /usr/sbin/shutdown -h +2 Server shutting down due to low battery
        exit 0
    fi
fi

# 2. Nightly Schedule (Shutdown at 00:00 / 12:00 AM, wake at 07:00 AM)
CURRENT_HOUR=$(date +%H)
CURRENT_MIN=$(date +%M)

if [ $CURRENT_HOUR -eq 0 ] && [ $CURRENT_MIN -le 15 ]; then
    WAKE_TIME=$(date -d 07:00:00 +%s)
    NOW=$(date +%s)
    if [ $WAKE_TIME -le $NOW ]; then
        WAKE_TIME=$(date -d tomorrow 07:00:00 +%s)
    fi

    ACTIVE_SSH=$(who | grep -E pts/[0-9]+ || true)

    if [ -n "$ACTIVE_SSH" ]; then
        wall NIGHTLY SHUTDOWN NOTICE: It is 12:00 AM. Server shutdown scheduled with RTC wake at 7:00 AM in 10 minutes. Run shutdown -c to cancel.
        /usr/sbin/rtcwake -m no -t $WAKE_TIME
        revert_wan_mode
        /usr/sbin/shutdown -h +10 Scheduled nightly shutdown
    else
        wall Scheduled nightly shutdown executing. Waking up at 7:00 AM.
        /usr/sbin/rtcwake -m no -t $WAKE_TIME
        revert_wan_mode
        /usr/sbin/shutdown -h +2 Scheduled nightly shutdown
    fi
fi
