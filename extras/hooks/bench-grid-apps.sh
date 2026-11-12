#!/bin/bash
# Bench Grid: theme lazygit, fastfetch, Oh My Pi, Typora, eza, fzf, tmux, mpv, Firefox, the cursor and folder icons while bench-grid is active,
# and put them back when another theme is set. Theme slug arrives in $1.
# Each app is only touched through a block or file this hook marks as its own.
extras="$HOME/.config/omarchy/themes/bench-grid/extras"
active=0; [[ $1 == bench-grid && -d $extras ]] && active=1

# lazygit: a marked block in config.yml (skipped if you keep your own gui: section).
lg="${XDG_CONFIG_HOME:-$HOME/.config}/lazygit/config.yml"
if command -v lazygit >/dev/null; then
  mkdir -p "$(dirname "$lg")"; touch "$lg"
  sed -i --follow-symlinks '/^# >>> bench-grid/,/^# <<< bench-grid/d' "$lg"
  if (( active )); then
    if grep -q '^gui:' "$lg"; then
      echo "bench-grid: $lg already has a gui: section, lazygit left unthemed" >&2
    else
      { echo "# >>> bench-grid (managed by theme-set hook)"; cat "$extras/lazygit.yml"; echo "# <<< bench-grid"; } >>"$lg"
    fi
  fi
fi

# fastfetch: a user config derived from the system one, marked so it is never mistaken for yours.
ff="$HOME/.config/fastfetch/config.jsonc"
if command -v fastfetch >/dev/null && [[ -f /etc/fastfetch/config.jsonc ]]; then
  if (( active )); then
    if [[ ! -f $ff ]] || grep -q 'bench-grid/extras/fastfetch-logo' "$ff"; then
      mkdir -p "$(dirname "$ff")"
      jq --arg logo "$extras/fastfetch-logo.txt" '
        .logo.source = $logo
        | .logo.color = {"1": "#a8c7b7", "2": "#f3a712", "3": "#eee8dc"}
        | .logo.padding = {"top": 2, "right": 4, "left": 2}' \
        /etc/fastfetch/config.jsonc >"$ff.tmp" && mv "$ff.tmp" "$ff"
    fi
  elif [[ -f $ff ]] && grep -q 'bench-grid/extras/fastfetch-logo' "$ff"; then
    rm -f "$ff"
  fi
fi

# Oh My Pi: install the theme and select it, remembering the theme it replaced.
if command -v omp >/dev/null && [[ -d $HOME/.omp/agent ]]; then
  saved="${XDG_STATE_HOME:-$HOME/.local/state}/bench-grid/omp-previous-theme"
  current=$(omp config get theme.dark 2>/dev/null)
  if (( active )); then
    mkdir -p "$HOME/.omp/agent/themes" "$(dirname "$saved")"
    cp "$extras/omp/bench-grid.json" "$HOME/.omp/agent/themes/bench-grid.json"
    [[ $current != bench-grid ]] && printf '%s\n' "${current:-titanium}" >"$saved"
    omp config set theme.dark bench-grid >/dev/null 2>&1
  elif [[ $current == bench-grid ]]; then
    omp config set theme.dark "$(cat "$saved" 2>/dev/null || echo titanium)" >/dev/null 2>&1
  fi
fi

# Cursor: install the Bench Grid cursors and make them the "default" cursor theme, which every
# app without its own cursor setting (Hyprland, the shell, GTK, Electron) falls back to.
# The default/index.theme is only written or removed when it carries this hook's marker.
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons"
def="$icons/default/index.theme"
size="${XCURSOR_SIZE:-24}"
if (( active )) && [[ -d $extras/cursors/BenchGrid ]]; then
  mkdir -p "$icons"
  rm -rf "$icons/BenchGrid" && cp -a "$extras/cursors/BenchGrid" "$icons/BenchGrid"
  if [[ ! -f $def ]] || grep -q '^# bench-grid' "$def"; then
    mkdir -p "$icons/default"
    printf '%s\n' '# bench-grid: managed by theme-set hook' '[Icon Theme]' 'Inherits=BenchGrid' >"$def"
  else
    echo "bench-grid: $def is your own, cursor applied for this session only" >&2
  fi
  command -v hyprctl >/dev/null && hyprctl setcursor BenchGrid "$size" >/dev/null 2>&1
elif [[ -f $def ]] && grep -q '^# bench-grid' "$def"; then
  rm -f "$def"; rmdir "$icons/default" 2>/dev/null
  command -v hyprctl >/dev/null && hyprctl setcursor default "$size" >/dev/null 2>&1
fi

# Folder icons: Bench-Grid-Icons inherits Yaru-sage and only redraws the folders. icons.theme
# stays Yaru-sage (so the theme works without this hook); the hook switches gsettings after
# Omarchy's own icon step. On other themes Omarchy resets icon-theme; we just remove our copy.
bgi="$icons/Bench-Grid-Icons"
if (( active )) && [[ -f $extras/icons/Bench-Grid-Icons/index.theme ]]; then
  if [[ -e $bgi ]] && ! grep -q '^# bench-grid' "$bgi/index.theme" 2>/dev/null; then
    echo "bench-grid: $bgi is not ours, folder icons left alone" >&2
  else
    mkdir -p "$icons"; rm -rf "$bgi"
    cp -a "$extras/icons/Bench-Grid-Icons" "$bgi"
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -f -t "$bgi"
    gsettings set org.gnome.desktop.interface icon-theme Bench-Grid-Icons 2>/dev/null
  fi
elif [[ -f $bgi/index.theme ]] && grep -q '^# bench-grid' "$bgi/index.theme"; then
  rm -rf "$bgi"
fi

# eza: a marked ~/.config/eza/theme.yml (left alone if you keep your own).
ez="${XDG_CONFIG_HOME:-$HOME/.config}/eza/theme.yml"
if (( active )) && [[ -f $extras/eza/theme.yml ]]; then
  if [[ ! -f $ez ]] || grep -q '^# bench-grid' "$ez"; then
    mkdir -p "$(dirname "$ez")"; cp "$extras/eza/theme.yml" "$ez"
  else
    echo "bench-grid: $ez is your own, eza left unthemed" >&2
  fi
elif [[ -f $ez ]] && grep -q '^# bench-grid' "$ez"; then
  rm -f "$ez"
fi

# fzf: options live in a file only this hook writes. Point FZF_DEFAULT_OPTS_FILE at it from
# ~/.bashrc (see README). On other themes it is emptied, not deleted: fzf errors on a missing file.
fz="${XDG_STATE_HOME:-$HOME/.local/state}/bench-grid/fzfrc"
if (( active )) && [[ -f $extras/fzf/fzfrc ]]; then
  mkdir -p "$(dirname "$fz")"; cp "$extras/fzf/fzfrc" "$fz"
elif [[ -f $fz ]]; then
  : >"$fz"
fi

# tmux: a marked block at the end of tmux.conf sources the status-line colours. Running servers
# are updated live; on other themes tmux.conf is re-sourced, which restores Omarchy's colours.
tc="${XDG_CONFIG_HOME:-$HOME/.config}/tmux/tmux.conf"
if command -v tmux >/dev/null && [[ -f $tc ]]; then
  had=0; grep -q '^# >>> bench-grid' "$tc" && had=1
  sed -i --follow-symlinks '/^# >>> bench-grid/,/^# <<< bench-grid/d' "$tc"
  if (( active )) && [[ -f $extras/tmux/bench-grid.conf ]]; then
    printf '%s\n' "# >>> bench-grid (managed by theme-set hook)" \
      "source-file -q \"$extras/tmux/bench-grid.conf\"" "# <<< bench-grid" >>"$tc"
    tmux list-sessions >/dev/null 2>&1 && tmux source-file "$extras/tmux/bench-grid.conf" 2>/dev/null
  elif (( had )); then
    tmux list-sessions >/dev/null 2>&1 && tmux source-file "$tc" 2>/dev/null
  fi
fi

# mpv: marked mpv.conf (OSD) and script-opts/osc.conf (controller); each left alone if it is your own.
# Running players keep their colours until reopened.
mpvd="${XDG_CONFIG_HOME:-$HOME/.config}/mpv"
for f in mpv.conf script-opts/osc.conf; do
  dst="$mpvd/$f"
  if (( active )) && [[ -f $extras/mpv/$f ]]; then
    if [[ ! -f $dst ]] || grep -q '^# bench-grid' "$dst"; then
      mkdir -p "$(dirname "$dst")"; cp "$extras/mpv/$f" "$dst"
    else
      echo "bench-grid: $dst is your own, left alone" >&2
    fi
  elif [[ -f $dst ]] && grep -q '^# bench-grid' "$dst"; then
    rm -f "$dst"; rmdir "$mpvd/script-opts" 2>/dev/null
  fi
done

# Firefox: a marked chrome/userChrome.css in each default profile (from installs.ini), plus a marked
# user.js block enabling userChrome. A userChrome.css of your own is left alone. Firefox must be
# restarted to pick it up. Removing the user.js block does not reset the pref; it is harmless on its own.
ffcss="$extras/firefox/userChrome.css"
for ffroot in "${XDG_CONFIG_HOME:-$HOME/.config}/mozilla/firefox" "$HOME/.mozilla/firefox"; do
  [[ -f $ffroot/installs.ini ]] || continue
  while IFS= read -r prof; do
    [[ $prof == /* ]] && pdir=$prof || pdir="$ffroot/$prof"
    [[ -d $pdir ]] || continue
    uc="$pdir/chrome/userChrome.css"; uj="$pdir/user.js"
    [[ -f $uj ]] && sed -i --follow-symlinks '/^\/\/ >>> bench-grid/,/^\/\/ <<< bench-grid/d' "$uj"
    if (( active )) && [[ -f $ffcss ]]; then
      if [[ ! -f $uc ]] || grep -q '^/\* bench-grid' "$uc"; then
        mkdir -p "$pdir/chrome"; cp "$ffcss" "$uc"
        printf '%s\n' "// >>> bench-grid (managed by theme-set hook)" \
          'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);' "// <<< bench-grid" >>"$uj"
      else
        echo "bench-grid: $uc is your own, Firefox left alone" >&2
      fi
    else
      if [[ -f $uc ]] && grep -q '^/\* bench-grid' "$uc"; then
        rm -f "$uc"; rmdir "$pdir/chrome" 2>/dev/null
      fi
      [[ -f $uj && ! -s $uj ]] && rm -f "$uj"
    fi
  done < <(sed -n 's/^Default=//p' "$ffroot/installs.ini" | sort -u)
done

# Typora: install the theme file; pick "Bench Grid" once from Typora's Themes menu.
ty="$HOME/.config/Typora/themes"
if [[ -d $ty && -f $extras/typora/bench-grid.css ]]; then
  cp "$extras/typora/bench-grid.css" "$ty/bench-grid.css"
fi
exit 0
