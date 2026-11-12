#!/usr/bin/env python3
"""Build the Bench Grid XCursor theme.

Usage: python3 -I tools/cursor.py <out-dir>      (normally extras/cursors/BenchGrid)
Needs rsvg-convert and ImageMagick's magick. Shapes are drawn on a 32-unit canvas:
cream keycap fill, graphite edge, soft shadow. Amber appears only on the busy spinner,
because busy is the one cursor state that means "active". Shapes that are not drawn
here fall back to Adwaita through index.theme.
"""
import os
import struct
import subprocess
import sys

CREAM, GRAPHITE, MAT, AMBER, BRICK = "#eee8dc", "#17201c", "#174d3a", "#f3a712", "#e07a5f"
SIZES = (24, 30, 32, 36, 48, 64, 72)
EDGE = 4  # outline layer stroke width: 2 units of edge outside the fill (1.5 px at size 24)

SHADOW = ('<filter id="s" x="-30%" y="-30%" width="160%" height="160%">'
          '<feGaussianBlur in="SourceAlpha" stdDeviation="0.7"/><feOffset dx="0.4" dy="0.9"/>'
          '<feComponentTransfer><feFuncA type="linear" slope="0.32"/></feComponentTransfer>'
          '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def svg(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            f'<defs>{SHADOW}</defs><g filter="url(#s)">{body}</g></svg>')


def solid(shapes, fill=CREAM, edge=GRAPHITE, width=EDGE, transform=""):
    """Filled shapes with one outline around their union (no seams where they overlap)."""
    t = f' transform="{transform}"' if transform else ""
    return (f'<g{t}><g fill="{edge}" stroke="{edge}" stroke-width="{width}" stroke-linejoin="round">{shapes}</g>'
            f'<g fill="{fill}">{shapes}</g></g>')


def lines(d, ink, edge, w, ew, cap="round", transform=""):
    """Stroked paths with an outline: an edge-coloured wide stroke under the ink stroke."""
    t = f' transform="{transform}"' if transform else ""
    return (f'<g{t} fill="none" stroke-linecap="{cap}" stroke-linejoin="round">'
            f'<path d="{d}" stroke="{edge}" stroke-width="{ew}"/><path d="{d}" stroke="{ink}" stroke-width="{w}"/></g>')


ARROW = '<path d="M5 4V25.6L10.4 20.6L14 28.6L17.6 27L14.1 19.2H21Z"/>'
ARROW_HOT = (4.6, 3.4)


def arrow():
    return solid(ARROW)


def badge(glyph):
    """A small mat-green tag at the arrow's heel, like a label on the mat."""
    return (f'<circle cx="24.6" cy="24.6" r="6.6" fill="{GRAPHITE}"/>'
            f'<circle cx="24.6" cy="24.6" r="5.6" fill="{CREAM}"/>'
            f'<circle cx="24.6" cy="24.6" r="4.6" fill="{MAT}"/>{glyph}')


def g_stroke(d, w=1.5, color=CREAM):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


def spinner(cx, cy, r, track, arc, frame, frames):
    c = 2 * 3.14159265 * r
    rot = 360 * frame / frames
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{GRAPHITE}" stroke-width="{track + 2.6}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{CREAM}" stroke-width="{track}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{AMBER}" stroke-width="{arc}" '
            f'stroke-linecap="round" stroke-dasharray="{c * 0.3:.2f} {c:.2f}" '
            f'transform="rotate({rot - 90} {cx} {cy})"/>')


DOUBLE_V = ('<rect x="14.8" y="8" width="2.4" height="16"/>'
            '<path d="M16 3.5L21.6 10H10.4Z"/><path d="M16 28.5L21.6 22H10.4Z"/>')
SPLIT_H = ('<rect x="14.9" y="5" width="2.2" height="22" rx="0.6"/>'
           '<rect x="7" y="14.8" width="5.6" height="2.4"/><path d="M2.6 16L8.6 10.8V21.2Z"/>'
           '<rect x="19.4" y="14.8" width="5.6" height="2.4"/><path d="M29.4 16L23.4 10.8V21.2Z"/>')
MOVE = ('<rect x="14.8" y="7" width="2.4" height="18"/><rect x="7" y="14.8" width="18" height="2.4"/>'
        '<path d="M16 2.5L20.8 8H11.2Z"/><path d="M16 29.5L20.8 24H11.2Z"/>'
        '<path d="M2.5 16L8 11.2V20.8Z"/><path d="M29.5 16L24 11.2V20.8Z"/>')


def hand(kind):
    """One silhouette per hand: fingers as a run of rounded tops, a palm, and a thumb that
    grows out of the palm (no separate pieces), with short seams between fingers."""
    # (left x, right x, top y) per finger, left to right; widths ~3.5 units.
    fingers = {
        "pointer": [(10.4, 14.6, 2.4), (14.6, 18.1, 11.2), (18.1, 21.6, 12.0), (21.6, 25.0, 13.4)],
        "grab": [(10.4, 14.0, 6.2), (14.0, 17.6, 4.2), (17.6, 21.2, 5.2), (21.2, 24.6, 7.6)],
        "grabbing": [(10.4, 14.0, 11.4), (14.0, 17.6, 10.6), (17.6, 21.2, 11.2), (21.2, 24.6, 12.6)],
    }[kind]
    x0, x1, y = fingers[0]
    r = (x1 - x0) / 2
    d = f"M{x0} {y + r:.2f}A{r:.2f} {r:.2f} 0 0 1 {x1} {y + r:.2f}"
    for x0, x1, y in fingers[1:]:
        r = (x1 - x0) / 2
        d += f"L{x0} {y + r:.2f}A{r:.2f} {r:.2f} 0 0 1 {x1} {y + r:.2f}"
    right = fingers[-1][1]
    d += (f"V22C{right} 26.5 {right - 2.5} 29 {right - 6} 29H15.5C12.5 29 11 27.5 9.6 25.5"
          "L6.6 21.2C5.6 19.8 6.4 18 8 18.2C9 18.3 9.8 19 10.4 20Z")
    seam_end = 16.6
    seams = ""
    for (_, _, ya), (xb, xb1, yb) in zip(fingers, fingers[1:]):
        top = max(ya, yb) + (xb1 - xb) / 2 + 0.4
        if kind == "pointer" and ya < yb:  # the raised index finger meets the knuckles
            continue
        if seam_end - top > 1:
            seams += f"M{xb} {top:.2f}V{seam_end}"
    if kind == "pointer":
        seams = "".join(f"M{xb} {yb + (xb1 - xb) / 2 + 0.4:.2f}V16.6" for xb, xb1, yb in fingers[2:])
    return solid(f'<path d="{d}"/>') + g_stroke(seams, 1.1, GRAPHITE)


def lens(sign):
    d = "M9.4 13H16.6" + ("M13 9.4V16.6" if sign == "+" else "")
    return (lines("M19.2 19.2L27 27", GRAPHITE, CREAM, 4.4, 7.4)
            + f'<circle cx="13" cy="13" r="8.2" fill="{CREAM}" stroke="{GRAPHITE}" stroke-width="2.6"/>'
            + g_stroke(d, 2, GRAPHITE))


def crosshair():
    # A drafting cross with ruler ticks on every arm: the mat's grid under the pointer.
    arms = "M16 3V12.6M16 19.4V29M3 16H12.6M19.4 16H29"
    ticks = "M14.6 7H17.4M14.6 25H17.4M7 14.6V17.4M25 14.6V17.4"
    return (lines(arms + ticks, GRAPHITE, CREAM, 1.5, 4, cap="square")
            + f'<circle cx="16" cy="16" r="2.2" fill="{CREAM}"/><circle cx="16" cy="16" r="1.1" fill="{GRAPHITE}"/>')


def forbidden(cx=16, cy=16, r=9, w=3.2):
    o = r * 0.7071
    slash = f"M{cx - o:.2f} {cy - o:.2f}L{cx + o:.2f} {cy + o:.2f}"
    ring = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{{c}}" stroke-width="{{w}}"/>'
    return (ring.format(c=GRAPHITE, w=w + 2.8) + lines(slash, GRAPHITE, GRAPHITE, w + 2.8, w + 2.8)
            + ring.format(c=BRICK, w=w) + lines(slash, BRICK, BRICK, w, w))


IBEAM = ('<rect x="11.8" y="4.6" width="8.4" height="2.2" rx="1.1"/>'
         '<rect x="14.9" y="5" width="2.2" height="22"/>'
         '<rect x="11.8" y="25.2" width="8.4" height="2.2" rx="1.1"/>')

# name -> (frames: list of svg bodies, hotspot in canvas units, frame delay ms)
SHAPES = {
    "default": ([arrow()], ARROW_HOT, 0),
    "pointer": ([hand("pointer")], (12.5, 2.6), 0),
    "grab": ([hand("grab")], (17, 15), 0),
    "grabbing": ([hand("grabbing")], (17, 16), 0),
    # Text cursors invert the keycap: graphite beam with a cream edge, readable on both surfaces.
    "text": ([solid(IBEAM, GRAPHITE, CREAM, 2.8)], (16, 16), 0),
    "vertical-text": ([solid(IBEAM, GRAPHITE, CREAM, 2.8, "rotate(90 16 16)")], (16, 16), 0),
    "crosshair": ([crosshair()], (16, 16), 0),
    "cell": ([solid('<rect x="13.4" y="5" width="5.2" height="22" rx="1"/>'
                    '<rect x="5" y="13.4" width="22" height="5.2" rx="1"/>')], (16, 16), 0),
    "move": ([solid(MOVE)], (16, 16), 0),
    "ns-resize": ([solid(DOUBLE_V)], (16, 16), 0),
    "ew-resize": ([solid(DOUBLE_V, transform="rotate(90 16 16)")], (16, 16), 0),
    "nesw-resize": ([solid(DOUBLE_V, transform="rotate(45 16 16)")], (16, 16), 0),
    "nwse-resize": ([solid(DOUBLE_V, transform="rotate(-45 16 16)")], (16, 16), 0),
    "col-resize": ([solid(SPLIT_H)], (16, 16), 0),
    "row-resize": ([solid(SPLIT_H, transform="rotate(90 16 16)")], (16, 16), 0),
    "not-allowed": ([forbidden()], (16, 16), 0),
    "no-drop": ([arrow() + f'<circle cx="24.6" cy="24.6" r="6.4" fill="{CREAM}"/>'
                 + forbidden(24.6, 24.6, 4.2, 1.8)], ARROW_HOT, 0),
    "help": ([arrow() + badge(g_stroke("M22.7 23.2Q22.7 21.4 24.6 21.4Q26.5 21.4 26.5 23Q26.5 24.2 24.6 24.9V25.6")
                              + f'<circle cx="24.6" cy="27.6" r="0.85" fill="{CREAM}"/>')], ARROW_HOT, 0),
    "context-menu": ([arrow() + badge(g_stroke("M22.4 22.6H26.8M22.4 24.6H26.8M22.4 26.6H26.8", 1.2))], ARROW_HOT, 0),
    "copy": ([arrow() + badge(g_stroke("M24.6 22.2V27M22.2 24.6H27", 1.6))], ARROW_HOT, 0),
    "alias": ([arrow() + badge(g_stroke("M22.4 26.8L26.6 22.6M23.6 22.4H26.8V25.6", 1.4))], ARROW_HOT, 0),
    "zoom-in": ([lens("+")], (13, 13), 0),
    "zoom-out": ([lens("-")], (13, 13), 0),
    "wait": ([spinner(16, 16, 8.4, 4.4, 4.4, f, 12) for f in range(12)], (16, 16), 60),
    "progress": ([arrow() + spinner(24.2, 24.2, 4.4, 2.6, 2.6, f, 12) for f in range(12)], ARROW_HOT, 60),
}

ALIASES = {
    "default": "arrow left_ptr top_left_arrow",
    "pointer": "hand hand1 hand2 pointing_hand",
    "grab": "openhand",
    "grabbing": "closedhand dnd-none",
    "text": "xterm ibeam",
    "crosshair": "cross tcross cross_reverse diamond_cross",
    "cell": "plus",
    "move": "fleur all-scroll all-resize size_all dnd-move",
    "ns-resize": "n-resize s-resize top_side bottom_side sb_v_double_arrow v_double_arrow size_ver",
    "ew-resize": "e-resize w-resize left_side right_side sb_h_double_arrow h_double_arrow size_hor",
    "nwse-resize": "nw-resize se-resize top_left_corner bottom_right_corner bd_double_arrow size_fdiag",
    "nesw-resize": "ne-resize sw-resize top_right_corner bottom_left_corner fd_double_arrow size_bdiag",
    "col-resize": "split_h",
    "row-resize": "split_v",
    "not-allowed": "X_cursor forbidden crossed_circle circle",
    "no-drop": "dnd-no-drop",
    "help": "question_arrow whats_this left_ptr_help dnd-ask",
    "copy": "dnd-copy",
    "alias": "dnd-link link",
    "wait": "watch",
    "progress": "left_ptr_watch half-busy",
}


def rasterize(body, size):
    png = subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size)],
                         input=svg(body).encode(), capture_output=True, check=True).stdout
    rgba = subprocess.run(["magick", "png:-", "-depth", "8", "rgba:-"],
                          input=png, capture_output=True, check=True).stdout
    assert len(rgba) == size * size * 4, (len(rgba), size)
    pixels = []
    for i in range(0, len(rgba), 4):
        r, g, b, a = rgba[i:i + 4]
        # XCursor wants premultiplied ARGB.
        pixels.append((a << 24) | ((r * a // 255) << 16) | ((g * a // 255) << 8) | (b * a // 255))
    return struct.pack(f"<{len(pixels)}I", *pixels)


def xcursor(frames, hot, delay):
    images = []
    for size in SIZES:
        hx = min(size - 1, round(hot[0] * size / 32))
        hy = min(size - 1, round(hot[1] * size / 32))
        for body in frames:
            images.append((size, struct.pack("<9I", 36, 0xFFFD0002, size, 1, size, size, hx, hy, delay)
                           + rasterize(body, size)))
    pos = 16 + 12 * len(images)
    toc, chunks = b"", b""
    for size, chunk in images:
        toc += struct.pack("<3I", 0xFFFD0002, size, pos + len(chunks))
        chunks += chunk
    return struct.pack("<4sIII", b"Xcur", 16, 0x10000, len(images)) + toc + chunks


def main():
    out = sys.argv[1]
    cursors = os.path.join(out, "cursors")
    os.makedirs(cursors, exist_ok=True)
    for f in os.listdir(cursors):
        os.remove(os.path.join(cursors, f))
    for name, (frames, hot, delay) in SHAPES.items():
        with open(os.path.join(cursors, name), "wb") as fh:
            fh.write(xcursor(frames, hot, delay))
    for target, names in ALIASES.items():
        for alias in names.split():
            os.symlink(target, os.path.join(cursors, alias))
    with open(os.path.join(out, "index.theme"), "w") as fh:
        fh.write("[Icon Theme]\nName=Bench Grid\n"
                 "Comment=Cream keycap cursors with a graphite edge, from the Bench Grid Omarchy theme\n"
                 "Inherits=Adwaita\n")
    if "--preview" in sys.argv:
        # A contact sheet on the three Bench Grid surfaces, for checking the shapes by eye.
        names = list(SHAPES)
        cell, cols = 64, 9
        rows = -(-len(names) // cols)
        parts = []
        for band, bg in enumerate((CREAM, MAT, GRAPHITE)):
            y0 = band * rows * cell
            parts.append(f'<rect y="{y0}" width="{cols * cell}" height="{rows * cell}" fill="{bg}"/>')
            for i, n in enumerate(names):
                x, y = (i % cols) * cell + 8, y0 + (i // cols) * cell + 8
                body = SHAPES[n][0][3 % len(SHAPES[n][0])]
                parts.append(f'<svg x="{x}" y="{y}" width="48" height="48" viewBox="0 0 32 32">'
                             f'<defs>{SHADOW}</defs><g filter="url(#s)">{body}</g></svg>')
        sheet = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{cols * cell}" height="{3 * rows * cell}">'
                 + "".join(parts) + "</svg>")
        with open(sys.argv[sys.argv.index("--preview") + 1], "w") as fh:
            fh.write(sheet)


if __name__ == "__main__":
    main()
