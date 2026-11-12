#!/usr/bin/env python3
"""Check WCAG contrast for Bench Grid pairs. Usage: python3 -I tools/contrast.py colors.toml"""
import sys, tomllib

def lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

c = tomllib.load(open(sys.argv[1], "rb"))
CREAM, SIDEBAR, MAT = "#eee8dc", "#e2ddcf", "#174d3a"
ansi = ["red", "yellow", "orange", "green", "cyan", "blue", "magenta", "brown",
        "bright_red", "bright_yellow", "bright_green", "bright_cyan", "bright_blue", "bright_magenta",
        "foreground", "dark_foreground", "light_foreground", "accent", "muted"]
pairs = [(k, c[k], c["background"]) for k in ansi]
pairs += [(f"{k} on lighter_bg", c[k], c["lighter_background"]) for k in ("foreground", "dark_foreground", "accent")]
pairs += [
    ("cream on selection(mat)", c["selection_foreground"], c["selection"]),
    ("graphite on cream", c["background"], CREAM),
    ("graphite on sidebar", c["background"], SIDEBAR),
    ("muted text #4b5750 on cream", "#4b5750", CREAM),
    ("mat on cream (accent in GTK)", MAT, CREAM),
    ("graphite on amber", c["background"], c["accent"]),
    ("cream on mat-shadow", CREAM, c["darker_background"]),
]
fail = 0
for name, fg, bg in pairs:
    r = ratio(fg, bg)
    # muted is a non-text role (inactive chrome, comments): 3:1 is the bar
    need = 3.0 if name == "muted" else 4.5
    ok = r >= need
    fail += not ok
    print(f"{'ok ' if ok else 'LOW'} {r:5.2f}  {name:32} {fg} on {bg}")
sys.exit(1 if fail else 0)
