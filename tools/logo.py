#!/usr/bin/env python3
"""Render unlock.png: the 800x188 transparent logo Omarchy puts on the Plymouth boot
splash and the SDDM login screen (over colors.toml background, graphite).

usage: python3 -I tools/logo.py <unlock.png> [--source logo.png]

It stays Omarchy's own wordmark (this is a theme, not a new OS), recoloured to
keycap cream and set on a sage ruler. The source defaults to Omarchy's stock
Plymouth logo.
"""
import base64
import os
import subprocess
import sys

KEYCAP, SAGE = "#eee8dc", "#a8c7b7"
W, H = 800, 188
SOURCE = os.path.join(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy"), "default/plymouth/logo.png")

# wordmark box (70% of the stock 800x188) and the ruler under it
LX, LY, LW, LH = 120, 6, 560, 132
RY, STEP = 156, 8


def wordmark(source):
    png = subprocess.run(["magick", source, "-resize", f"{LW}x{LH}!", "-fill", KEYCAP,
                          "-colorize", "100", "png:-"], check=True, capture_output=True).stdout
    return base64.b64encode(png).decode()


def svg(source):
    ticks = []
    for i, x in enumerate(range(LX, LX + LW + 1, STEP)):
        h = 14 if i % 10 == 0 else (9 if i % 5 == 0 else 5)
        ticks.append(f"M{x} {RY}V{RY + h}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<image x="{LX}" y="{LY}" width="{LW}" height="{LH}" '
            f'xlink:href="data:image/png;base64,{wordmark(source)}"/>'
            f'<path d="M{LX} {RY}H{LX + LW}{"".join(ticks)}" stroke="{SAGE}" stroke-width="2.5" '
            f'stroke-linecap="square" fill="none"/></svg>\n')


if __name__ == "__main__":
    args = sys.argv[1:]
    source = SOURCE
    if "--source" in args:
        i = args.index("--source")
        source = args[i + 1]
        del args[i:i + 2]
    subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-o", args[0]],
                   input=svg(source).encode(), check=True)
