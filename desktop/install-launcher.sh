#!/usr/bin/env bash
# Install "MuniMonitor Start" / "MuniMonitor Stop" launchers for this checkout:
# the application menu, plus the desktop if ~/Desktop exists. Re-run after moving the folder.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
chmod +x "$HERE/munimonitor-ctl"
mk() { # mk <file> <name> <comment> <action> <icon>
    cat > "$1" <<DESK
[Desktop Entry]
Type=Application
Name=$2
Comment=$3
Exec=$HERE/munimonitor-ctl $4
Terminal=false
Icon=$5
Categories=Development;
DESK
    chmod +x "$1"
}
dirs=("${XDG_DATA_HOME:-$HOME/.local/share}/applications")
[[ -d "$HOME/Desktop" ]] && dirs+=("$HOME/Desktop")
for d in "${dirs[@]}"; do
    mkdir -p "$d"
    mk "$d/MuniMonitor-Start.desktop" "MuniMonitor Start" \
       "Model server + synthetic web UI on http://127.0.0.1:8600 (unofficial test system)" start "$HERE/munimonitor.png"
    mk "$d/MuniMonitor-Stop.desktop" "MuniMonitor Stop" "Stop the MuniMonitor model and web UI" stop media-playback-stop
    if [[ "$d" == "$HOME/Desktop" ]] && command -v gio >/dev/null; then   # GNOME: allow double-click
        gio set "$d/MuniMonitor-Start.desktop" metadata::trusted true 2>/dev/null || true
        gio set "$d/MuniMonitor-Start.desktop" metadata::custom-icon "file://$HERE/munimonitor.png" 2>/dev/null || true
        gio set "$d/MuniMonitor-Stop.desktop" metadata::trusted true 2>/dev/null || true
    fi
    echo "installed launchers in $d"
done
