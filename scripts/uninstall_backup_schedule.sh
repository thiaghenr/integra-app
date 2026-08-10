#!/usr/bin/env bash
# Removes the launchd agent installed by install_backup_schedule.sh.
set -euo pipefail

LABEL="com.integra.dbbackup"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"

echo "Removed ${LABEL} scheduled backup."
