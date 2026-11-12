#!/bin/bash
# Bench Grid: flip starship to the bench_grid palette while the theme is active.
# Needs [palettes.default] and [palettes.bench_grid] plus a `palette = ...` line
# in ~/.config/starship.toml (see extras/starship.toml). Theme slug arrives in $1.
config="${STARSHIP_CONFIG:-$HOME/.config/starship.toml}"
[[ -f $config ]] && grep -q '^\[palettes\.bench_grid\]' "$config" || exit 0

if [[ $1 == bench-grid ]]; then palette=bench_grid; else palette=default; fi
sed -i --follow-symlinks -E "s/^palette = \".*\"/palette = \"$palette\"/" "$config"
