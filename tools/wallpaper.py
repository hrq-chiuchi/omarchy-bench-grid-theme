#!/usr/bin/env python3
"""Render Bench Grid cutting-mat wallpapers as SVG.

Usage: python3 -I tools/wallpaper.py <variant> <width> <height> > out.svg
Variants: mat, night, graphite. Render with: rsvg-convert out.svg -o out.png
"""
import sys

variant, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

PALETTE = {
    #            field      line                minor  major  ruler  stamp
    "mat":      ("#174d3a", "#eee8dc",          0.075, 0.15,  0.34,  0.28),
    "night":    ("#0d2f25", "#a8c7b7",          0.055, 0.11,  0.26,  0.22),
    "graphite": ("#17201c", "#a8c7b7",          0.040, 0.075, 0.20,  0.18),
}
field, line, a_minor, a_major, a_ruler, a_stamp = PALETTE[variant]

cell = round(H / 30)            # ~1 cm square at 1080p
margin = cell * 2               # ruler band, like the unprinted edge of a real mat
font = "IBM Plex Mono, BlexMono Nerd Font, monospace"
fs = max(9, round(cell * 0.30))

out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="{field}"/>']

def stroke(alpha, width):
    return f'stroke="{line}" stroke-opacity="{alpha}" stroke-width="{width}"'

# Grid: minor every cell, major every 5th, starting at the ruler origin.
x0, y0 = margin, H - margin      # origin bottom-left, as on the desk
minor, major = [], []
i = 0
x = x0
while x <= W:
    (major if i % 5 == 0 else minor).append(f"M{x} 0V{H}")
    x += cell; i += 1
i = 0
y = y0
while y >= 0:
    (major if i % 5 == 0 else minor).append(f"M0 {y}H{W}")
    y -= cell; i += 1
out.append(f'<path d="{" ".join(minor)}" fill="none" {stroke(a_minor, 1)}/>')
out.append(f'<path d="{" ".join(major)}" fill="none" {stroke(a_major, 1.5)}/>')

# One faint 45° guide from the origin, the way real mats carry angle lines.
out.append(f'<path d="M{x0} {y0}L{x0 + y0} 0" fill="none" {stroke(a_minor * 0.9, 1)}/>')

# Rulers: ticks and numbers along the bottom and left edges.
stamp = f"HRQ · OMARCHY · {W}×{H} · 1 SQ = 1 CM"
stamp_w = len(stamp) * fs * (0.6 + 0.18)      # mono advance + letter-spacing
stamp_x0 = W - margin - stamp_w - cell
ticks, labels = [], []
n = 0
x = x0
while x <= W - cell:
    length = cell * (0.5 if n % 5 == 0 else 0.28)
    ticks.append(f"M{x} {H}V{H - length}")
    if n and x < stamp_x0:
        labels.append(f'<text x="{x}" y="{H - cell * 0.75}" text-anchor="middle">{n}</text>')
    x += cell; n += 1
n = 0
y = y0
while y >= cell:
    length = cell * (0.5 if n % 5 == 0 else 0.28)
    ticks.append(f"M0 {y}H{length}")
    if n and y > margin:                     # keep clear of the top bar
        labels.append(f'<text x="{cell * 0.75}" y="{y + fs * 0.35}" text-anchor="middle">{n}</text>')
    y -= cell; n += 1
out.append(f'<path d="{" ".join(ticks)}" fill="none" {stroke(a_ruler, 1)}/>')
out.append(f'<g fill="{line}" fill-opacity="{a_ruler}" font-family="{font}" font-size="{fs}">{"".join(labels)}</g>')

# Maker's stamp, where a mat prints its brand.
out.append(
    f'<text x="{W - margin}" y="{H - cell * 0.75}" text-anchor="end" fill="{line}" fill-opacity="{a_stamp}" '
    f'font-family="{font}" font-size="{fs}" font-weight="500" letter-spacing="{fs * 0.18:.1f}">'
    f'{stamp}</text>')

out.append("</svg>")
print("\n".join(out))
