#!/usr/bin/env bash
# Installs a macOS launchd agent that runs backup_db.sh every 6 hours,
# regardless of whether a terminal/IDE is open. Safe to re-run (overwrites
# the existing agent definition). See uninstall_backup_schedule.sh to remove.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.integra.dbbackup"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$PROJECT_DIR/backups"
mkdir -p "$LOG_DIR"

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${PROJECT_DIR}/scripts/backup_db.sh</string>
  </array>
  <key>StartInterval</key>
  <integer>21600</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/backup_schedule.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/backup_schedule.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "Installed. ${LABEL} will run backup_db.sh every 6h (and once now) while you're logged in."
echo "Logs: ${LOG_DIR}/backup_schedule.log"
echo "To remove: ./scripts/uninstall_backup_schedule.sh"
