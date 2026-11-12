#!/bin/bash
# Bench Grid bar: a floating graphite card with keycap workspace buttons.
# Clones Omarchy's own bar and workspaces plugins into ~/.config/omarchy/plugins/<user>.*,
# patches the bar to draw an inset card and peek the tray drawer on hover (only when the theme sets [bar] inset in shell.toml,
# so other themes keep the stock strip), and drops in the keycap Workspaces.qml.
# Safe to re-run. After an Omarchy bar update, delete <user>.bar and run this again to re-clone.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
plugins="$HOME/.config/omarchy/plugins"
user="${USER:-$(id -un)}"

[[ -d $plugins/$user.bar ]] || omarchy plugin clone omarchy.bar
if patch -s -f --dry-run -R -p1 -d "$plugins/$user.bar" <"$here/bar-floating.patch" >/dev/null 2>&1; then
  echo "bar: already patched"
else
  patch -s -p1 -d "$plugins/$user.bar" <"$here/bar-floating.patch"
  echo "bar: patched $plugins/$user.bar"
fi

# Tray peek: no chevron; the drawer opens while the pointer is over the bar's right section
# (only when the theme sets [bar] tray-peek = true, so other themes keep the stock tray).
[[ -d $plugins/$user.tray ]] || omarchy plugin clone omarchy.tray
if patch -s -f --dry-run -R -p1 -d "$plugins/$user.tray" <"$here/tray-peek.patch" >/dev/null 2>&1; then
  echo "tray: already patched"
else
  patch -s -p1 -d "$plugins/$user.tray" <"$here/tray-peek.patch"
  echo "tray: patched $plugins/$user.tray"
fi

[[ -d $plugins/$user.workspaces ]] || omarchy plugin clone omarchy.workspaces
cp "$here/Workspaces.qml" "$plugins/$user.workspaces/Workspaces.qml"
echo "workspaces: installed $plugins/$user.workspaces"
# Clock clone: with [bar] icon-idle set, the bar mutes every first-party icon; a clock clone gets its
# own bar API colour and stays the full text colour. The clone does not move bar.centerAnchor, so do it here.
if [[ ! -d $plugins/$user.clock ]]; then
  omarchy plugin clone omarchy.clock
  f="$HOME/.config/omarchy/shell.json"
  if [[ -f $f ]] && jq -e '.bar.centerAnchor == "omarchy.clock"' "$f" >/dev/null; then
    jq --arg id "$user.clock" '.bar.centerAnchor = $id' "$f" >"$f.tmp" && mv "$f.tmp" "$f"
  fi
fi

# Focused-window title: a clone of omarchy.active-window showing the program name; clicks only focus (stock closes the
# window on middle- and right-click). Put <user>.active-window alone in bar.layout.center.
[[ -d $plugins/$user.active-window ]] || omarchy plugin clone omarchy.active-window
if patch -s -f --dry-run -R -p1 -d "$plugins/$user.active-window" <"$here/active-window.patch" >/dev/null 2>&1; then
  echo "active-window: already patched"
else
  patch -s -p1 -d "$plugins/$user.active-window" <"$here/active-window.patch"
  echo "active-window: patched $plugins/$user.active-window"
fi

# Stay-awake dot: a small widget (not a clone; cloned indicators lose the first-party idle service).
# Add it to bar.layout.center before omarchy.indicators, and give that entry
# "items": ["PasswordlessSudo","ScreenRecording","RemoteSession","Reminder","NightLight","Dnd"].
mkdir -p "$plugins/$user.stay-awake/i18n"
cp "$here/stay-awake/StayAwake.qml" "$plugins/$user.stay-awake/"
cp "$here/stay-awake/i18n/en.json" "$plugins/$user.stay-awake/i18n/"
sed "s/USER\.stay-awake/$user.stay-awake/" "$here/stay-awake/manifest.json" >"$plugins/$user.stay-awake/manifest.json"
echo "stay-awake: installed $plugins/$user.stay-awake"

echo "Restart the shell to load the new bar: omarchy restart shell"
