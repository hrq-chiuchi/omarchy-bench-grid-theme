#!/bin/bash
# Regenerate Bench Grid assets. Usage: tools/build.sh [WIDTH HEIGHT]
# Defaults to the primary monitor's native resolution.
set -euo pipefail
cd "$(dirname "$0")/.."

W=${1:-$(hyprctl monitors -j 2>/dev/null | jq '.[0].width' || echo 1920)}
H=${2:-$(hyprctl monitors -j 2>/dev/null | jq '.[0].height' || echo 1080)}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

python3 -I tools/contrast.py colors.toml >/dev/null || { python3 -I tools/contrast.py colors.toml; exit 1; }

i=1
for v in mat night graphite; do
  python3 -I tools/wallpaper.py "$v" "$W" "$H" >"$tmp/$v.svg"
  rsvg-convert "$tmp/$v.svg" -o "backgrounds/$i-$v.png"
  i=$((i + 1))
done

python3 -I tools/cursor.py extras/cursors/BenchGrid
python3 -I tools/icons.py extras/icons/Bench-Grid-Icons
python3 -I tools/logo.py unlock.png && omarchy plymouth preview "#17201c" "#eee8dc" unlock.png preview-unlock.png

# VS Code: regenerate the base from Omarchy's template with the current palette,
# then apply the Bench Grid tuning. Needs the theme linked as "bench-grid".
state="$HOME/.local/state/omarchy/current/theme/vscode-theme.json"
if command -v omarchy >/dev/null && [[ -e $HOME/.config/omarchy/themes/bench-grid ]]; then
  mv vscode-theme.json "$tmp/previous.json"
  if omarchy theme set bench-grid >/dev/null 2>&1 && [[ -f $state ]]; then
    jq -f tools/vscode-tune.jq "$state" >vscode-theme.json
  else
    mv "$tmp/previous.json" vscode-theme.json
    echo "vscode: regeneration failed, kept previous file" >&2
  fi
  omarchy theme set bench-grid >/dev/null 2>&1
fi
echo "built ${W}x${H}"
