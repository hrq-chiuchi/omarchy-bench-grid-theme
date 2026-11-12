#!/usr/bin/env python3
"""Build Bench Grid Icons: a small icon theme that inherits Yaru-sage and redraws the
folder ("places") and file-type ("mimetypes") icons in the workstation mockup's line style.

usage: python3 -I tools/icons.py <out-dir> [--preview sheet.png]

Style "D": graphite outline on a cream paper fill, drawn on the mockup's 24-unit grid with
round ends. Folders have a front-flap line, files a folded corner; both carry a small line
glyph from 24 px up (16 px stays plain). The fill keeps them readable on a mat selection
(Nautilus never recolours full-colour icons); gtk.css lifts it to white on hover/selection.
Lines stay thin: the stroke is set per rendered size, not scaled with it. No amber.

File types: GTK searches every name of a file's icon list in this theme before it falls
back to Yaru, so the generic names (text-x-generic, package-x-generic, ...) already cover
every file. MIME_ALIASES only sharpens the category for common specific types (a shell
script is "script", not the generic page). Aliases are symlinks to the category drawing.
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile

MAT, KEYCAP, GRAPHITE = "#174d3a", "#eee8dc", "#17201c"
PAPER = KEYCAP        # icon fill; Nautilus lifts it to white on hover/selection (gtk.css)

FIXED = (16, 24, 32, 48, 64, 96, 128, 256)   # PNG sizes, each also rendered @2x
SCALABLE_BASE = 96                            # line weight the scalable SVG is drawn for


def stroke_units(px):
    """Hairline weight that grows slowly with size: ~1 px at 16-24, 1.25 at 48, 2 at 128,
    3.4 at 256. Returned in 24-unit drawing terms."""
    return max(1.0, 0.75 + px / 96) * 24 / px


# ---------------------------------------------------------------- bodies
CLOSED = ('<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h5l2 2H20a1 1 0 0 1 1 1v10.5a1.5 1.5 0 0 1-1.5 1.5'
          'h-15A1.5 1.5 0 0 1 3 18.5z"/><path d="M3 9.5H21" fill="none"/>')
OPEN = ('<path d="M3 18.5V6.5A1.5 1.5 0 0 1 4.5 5h5l2 2H18a1 1 0 0 1 1 1v2.5"/>'
        '<path d="M3.2 19.1 5.6 11.4a1 1 0 0 1 .95-.7H21a.8.8 0 0 1 .77 1.02L19.6 19a1.4 1.4 0 0 1-1.35 1'
        'H4.5a1.35 1.35 0 0 1-1.3-.9z"/>')
# the mockup's file: a page with a folded top-right corner
PAGE = ('<path d="M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/>'
        '<path d="M14 3v4h4" fill="none"/>')

# ---------------------------------------------------------------- folder glyphs
# Stroke-only, on the front panel (y 9.5-20), centred near (12, 14.75).
FOLDER_GLYPHS = {
    "documents": '<path d="M9 12.25h6M9 14.75h6M9 17.25h3.5"/>',
    "download": '<path d="M12 11.5v6m-2.2-2.2 2.2 2.2 2.2-2.2"/>',
    "music": '<path d="M10.75 17V12.25l4-1v4.75"/><circle cx="9.75" cy="17" r="1"/><circle cx="13.75" cy="16" r="1"/>',
    "pictures": '<rect x="8.5" y="11.75" width="7" height="6" rx=".75"/><path d="m8.75 17 2.25-2.25 1.75 1.75 1-1 1.5 1.5"/>',
    "videos": '<path d="M10.5 11.75v6l5-3z"/>',
    "templates": '<path d="M9 18v-6.25l6.25 6.25z"/>',
    "publicshare": '<circle cx="9.5" cy="14.75" r="1"/><circle cx="14.5" cy="12.25" r="1"/><circle cx="14.5" cy="17.25" r="1"/>'
                   '<path d="m10.4 14.3 3.2-1.6m-3.2 2.5 3.2 1.6"/>',
    "remote": '<path d="M10 17.25h4.5a1.9 1.9 0 0 0 0-3.8 2.9 2.9 0 0 0-5.5.6 1.6 1.6 0 0 0 1 3.2z"/>',
    "user-home": '<path d="M8.5 15 12 12l3.5 3"/><path d="M9.75 14v3.75h4.5V14"/>',
    "user-desktop": '<rect x="8.5" y="11.75" width="7" height="4.5" rx=".75"/><path d="M12 16.25v1.5m-2 0h4"/>',
}

# folder icon name -> (glyph or None, open?)
FOLDERS = {
    "folder": (None, False),
    "inode-directory": (None, False),
    "folder-open": (None, True),
    "folder-drag-accept": (None, True),
    "folder-visiting": (None, True),
    "folder-documents": ("documents", False),
    "folder-download": ("download", False),
    "folder-music": ("music", False),
    "folder-pictures": ("pictures", False),
    "folder-videos": ("videos", False),
    "folder-templates": ("templates", False),
    "folder-publicshare": ("publicshare", False),
    "folder-remote": ("remote", False),
    "user-home": ("user-home", False),
    "user-desktop": ("user-desktop", False),
}

# ---------------------------------------------------------------- file glyphs
# Stroke-only, on the page body below the fold (x 8.5-15.5, y 10-18.5), centred near (12, 14.5).
FILE_GLYPHS = {
    "generic": "",
    "text": '<path d="M9 10.5h6M9 13h6M9 15.5h6M9 18h3.5"/>',
    "document": '<path d="M8.5 3v5l1.5-1 1.5 1V3"/><path d="M9 11.5h6M9 14h6M9 16.5h6M9 19h3.5"/>',
    "code": '<path d="M10.25 12 8.25 14.5l2 2.5M13.75 12l2 2.5-2 2.5M12.6 11.25l-1.2 6.5"/>',
    "script": '<path d="m8.75 12 2.25 2-2.25 2"/><path d="M12.25 17h3"/>',
    "image": '<rect x="8.25" y="10.75" width="7.5" height="7" rx=".75"/>'
             '<path d="m8.5 16.75 2.25-2.25 1.75 1.75 1-1 2 2"/><circle cx="13.6" cy="12.9" r=".6"/>',
    "audio": '<path d="M11 17V11.5l4-1V16"/><circle cx="10" cy="17" r="1"/><circle cx="14" cy="16" r="1"/>',
    "video": '<path d="M10.5 11.5v6l5-3z"/>',
    "archive": '<path d="M11 4h1M12 5.5h1M11 7h1M12 8.5h1M11 10h1"/><rect x="10.75" y="11.5" width="2.5" height="3.5" rx=".5"/>',
    "spreadsheet": '<rect x="8.5" y="10.75" width="7" height="7.5" rx=".5"/><path d="M8.5 13.25h7M8.5 15.75h7M11 10.75v7.5"/>',
    "presentation": '<rect x="8.25" y="10.75" width="7.5" height="5.25" rx=".5"/>'
                    '<path d="M12 16v2m-1.5.25h3M10.25 14.25v-1M12 14.25v-1.75M13.75 14.25v-1.25"/>',
    "drawing": '<circle cx="10.75" cy="12.75" r="2"/><rect x="11.5" y="13.75" width="4" height="4" rx=".4"/>',
    "font": '<path d="M9.25 18 12 10.5l2.75 7.5M10.25 15.5h3.5"/>',
    "executable": '<rect x="8.25" y="11" width="7.5" height="6.5" rx=".75"/><path d="M8.25 13h7.5M9.6 12h.01M10.85 12h.01"/>',
    "disk": '<circle cx="12" cy="14.5" r="3.5"/><circle cx="12" cy="14.5" r="1"/>',
}

# category -> names it answers to. The first is the file; the rest are symlinks to it.
# Generic freedesktop names come first so every file type is covered.
MIME = {
    "generic": "application-x-generic application-octet-stream unknown empty application-x-zerosize",
    "text": "text-x-generic text-plain text-x-plain text text-x-log text-x-readme text-x-authors "
            "text-x-copying text-x-credits text-x-install text-markdown text-x-preview text-enriched "
            "text-richtext",
    "document": "x-office-document document office-document text-document application-msword "
                "application-vnd.ms-word application-rtf application-pdf application-x-pdf "
                "application-x-bzpdf application-x-gzpdf application-postscript application-epub+zip "
                "application-x-mobipocket-ebook application-vnd.oasis.opendocument.text "
                "application-vnd.oasis.opendocument.text-template "
                "application-vnd.oasis.opendocument.master-document "
                "application-vnd.openxmlformats-officedocument.wordprocessingml.document "
                "application-x-hwp application-vnd.haansoft-hwp libreoffice-text libreoffice-oasis-text "
                "libreoffice-oasis-text-template libreoffice-master-document "
                "libreoffice-oasis-master-document text-x-tex text-vnd.typst message-rfc822",
    "code": "text-x-script text-html html text-htmlh html-template text-css text-less text-x-sass "
            "text-x-scss text-xml application-xml text-x-python text-x-python3 application-x-python-bytecode "
            "text-x-c text-x-csrc text-x-chdr text-x-c++ text-x-cpp text-x-cppsrc text-x-c++src "
            "text-x-c++hdr text-x-csharp text-x-java text-x-java-source application-java application-x-java "
            "text-x-javascript application-javascript application-x-javascript text-x-typescript "
            "application-typescript application-x-typescript application-json application-geo+json "
            "application-x-ipynb+json application-x-yaml application-yaml application-toml "
            "application-sql text-x-sql text-x-go text-rust text-x-rust text-ruby text-x-ruby "
            "application-x-ruby text-x-php application-x-php application-x-perl text-x-lua text-x-kotlin "
            "text-x-scala text-x-dart application-vnd-dart text-x-haskell text-x-r text-x-r-source "
            "text-x-vala text-x-nim text-x-v text-x-qml text-x-fortran text-x-cobol text-x-arduino "
            "text-x-makefile gnome-mime-text-x-makefile text-x-cmake text-x-meson text-dockerfile "
            "text-x-systemd-unit text-x-patch text-x-twig text-x-maven+xml text-x-gettext-translation "
            "text-x-gettext-translation-template application-x-desktop application-x-wine-extension-ini "
            "application-x-rss+xml",
    "script": "application-x-shellscript",
    "image": "image-x-generic image-x-xcf image-x-compressed-xcf image-x-cursor image-x-3ds",
    "audio": "audio-x-generic audio-mpeg audio-x-mpeg audio-flac audio-x-flac audio-x-flac+ogg "
             "audio-x-vorbis+ogg audio-x-wav audio-x-ms-wma audio-midi audio-x-adpcm audio-x-playlist "
             "audio-x-mp3-playlist audio-x-mpegurl audio-x-scpls",
    "video": "video-x-generic application-x-subrip application-x-sami text-x-microdvd",
    "archive": "package-x-generic application-x-archive application-archive application-archive-zip "
               "application-zip application-x-zip zip application-gzip application-x-gzip application-rar "
               "application-x-rar application-vnd.rar rar gnome-mime-application-x-rar "
               "application-x-7z-compressed application-x-compress gnome-mime-application-x-compress "
               "application-x-java-archive application-vnd.debian.binary-package application-vnd.flatpak "
               "application-vnd.snap application-vnd.squashfs application-apk "
               "application-vnd.android.package-archive application-x-xpinstall package gnome-package "
               "application-x-bittorrent",
    "spreadsheet": "x-office-spreadsheet spreadsheet office-spreadsheet text-spreadsheet text-csv "
                   "application-vnd.ms-excel application-vnd.oasis.opendocument.spreadsheet "
                   "application-vnd.oasis.opendocument.spreadsheet-template "
                   "application-vnd.openxmlformats-officedocument.spreadsheetml.sheet "
                   "application-vnd.sun.xml.calc libreoffice-spreadsheet libreoffice-oasis-spreadsheet "
                   "libreoffice-oasis-spreadsheet-template application-x-sqlite3 office-database "
                   "application-msaccess application-vnd.ms-access libreoffice-database "
                   "libreoffice-oasis-database libreoffice-oasis-database-template "
                   "application-vnd.oasis.opendocument.database "
                   "application-vnd.oasis.opendocument.database-template",
    "presentation": "x-office-presentation presentation office-presentation text-presentation "
                    "application-mspowerpoint application-vnd.ms-powerpoint "
                    "application-vnd.oasis.opendocument.presentation "
                    "application-vnd.oasis.opendocument.presentation-template "
                    "application-vnd.openxmlformats-officedocument.presentationml.presentation "
                    "application-vnd.openxmlformats-officedocument.presentationml.slideshow "
                    "libreoffice-presentation libreoffice-oasis-presentation "
                    "libreoffice-oasis-presentation-template",
    "drawing": "x-office-drawing application-vnd.oasis.opendocument.graphics "
               "application-vnd.oasis.opendocument.graphics-template libreoffice-drawing "
               "libreoffice-oasis-drawing libreoffice-oasis-drawing-template application-illustrator "
               "image-vnd.adobe.illustrator application-x-karbon application-eps application-x-eps "
               "image-eps image-x-eps",
    "font": "font-x-generic font font-otf font-ttf application-font",
    "executable": "application-x-executable application-x-sharedlib application-x-ms-dos-executable "
                  "application-x-msdownload application-x-msi "
                  "application-vnd.microsoft.portable-executable application-x-firmware "
                  "application-x-addon",
    "disk": "application-x-cd-image application-x-iso9660-image application-x-raw-disk-image application-x-apple-diskimage "
            "application-x-qemu-disk application-x-virtualbox-vdi application-x-virtualbox-vhd "
            "application-x-virtualbox-vmdk",
}


# ---------------------------------------------------------------- symbolic (UI) icons
# The one-colour icons GTK recolours itself: sidebar places, header buttons, emblems. Drawn
# as lines on the mockup's 24-unit grid, then outlined into filled shapes at build time
# (outline()): GTK3 only recolours fills and draws stroked symbolic SVGs blank. Primitives:
#   ("l", pts) open polyline   ("p", pts) closed polyline   ("c", cx, cy, r) circle line
#   ("d", cx, cy, r) dot       ("r", x, y, w, h, rad) rounded-rect line
#   ("a", cx, cy, r, deg0, deg1) open arc (screen angles, 0 = east, 90 = south)
#   ("f", pts) filled polygon with a rounded outline
def _folder():
    return [("p", [(3, 5.5), (9.5, 5.5), (11.5, 7.5), (21, 7.5), (21, 19.5), (3, 19.5)]),
            ("l", [(3, 10.5), (21, 10.5)])]


def _star(cy=12.5, ro=9, ri=4.1):
    pts = []
    for i in range(10):
        r = ro if i % 2 == 0 else ri
        a = math.radians(-90 + 36 * i)
        pts.append((12 + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _page():
    return [("p", [(6, 3), (14, 3), (18, 7), (18, 21), (6, 21)]), ("l", [(14, 3), (14, 7), (18, 7)])]


def _x(c=12, h=6):
    return [("l", [(c - h, c - h), (c + h, c + h)]), ("l", [(c + h, c - h), (c - h, c + h)])]


def _arrow_arc(cx=12, cy=12, r=7.5, d0=-60, d1=230, head=3.2):
    """Refresh-style: an arc running from d0 to d1 with an arrowhead on its end, along the tangent."""
    e = math.radians(d1)
    ex, ey = cx + r * math.cos(e), cy + r * math.sin(e)
    sgn = 1 if d1 > d0 else -1
    tx, ty = -math.sin(e) * sgn, math.cos(e) * sgn           # direction of travel
    nx, ny = -ty, tx
    back = (ex - tx * head, ey - ty * head)
    return [("a", cx, cy, r, d0, d1),
            ("l", [(back[0] + nx * head, back[1] + ny * head), (ex, ey),
                   (back[0] - nx * head, back[1] - ny * head)])]


SYMBOLIC = {
    # places / sidebar
    "user-home": [("p", [(3.5, 10.5), (12, 3), (20.5, 10.5), (20.5, 20.5), (3.5, 20.5)]),
                  ("l", [(9, 20.5), (9, 14), (15, 14), (15, 20.5)])],
    "folder": _folder(),
    "folder-open": [("l", [(3, 18.5), (3, 5.5), (9.5, 5.5), (11.5, 7.5), (19, 7.5), (19, 10)]),
                    ("p", [(3, 19.5), (5.5, 10.5), (21.5, 10.5), (19, 19.5)])],
    "folder-new": _folder() + [("l", [(12, 12.5), (12, 17.5)]), ("l", [(9.5, 15), (14.5, 15)])],
    "folder-documents": _page() + [("l", [(9, 12), (15, 12)]), ("l", [(9, 15), (15, 15)]),
                                   ("l", [(9, 18), (12.5, 18)])],
    "folder-download": [("l", [(12, 3), (12, 15)]), ("l", [(8, 11), (12, 15), (16, 11)]),
                        ("l", [(5, 20), (19, 20)])],
    "folder-music": [("l", [(9.5, 17.5), (9.5, 5.5), (19, 3.5), (19, 15.5)]),
                     ("c", 7, 17.5, 2.5), ("c", 16.5, 15.5, 2.5)],
    "folder-pictures": [("r", 3, 4, 18, 16, 1.5), ("c", 8, 9, 1.5),
                        ("l", [(4, 17), (9, 12), (13, 16), (15, 14), (20, 19)])],
    "folder-videos": [("r", 3, 5, 18, 14, 1.5), ("p", [(10, 9), (10, 15), (15, 12)])],
    "folder-templates": [("p", [(4, 20), (4, 4), (20, 20)]), ("p", [(8, 16), (8, 12.5), (11.5, 16)])],
    "folder-publicshare": [("c", 6, 12, 2.5), ("c", 17.5, 5.5, 2.5), ("c", 17.5, 18.5, 2.5),
                           ("l", [(8.2, 10.8), (15.3, 6.8)]), ("l", [(8.2, 13.2), (15.3, 17.2)])],
    "folder-remote": [("l", [(7, 18.5), (17, 18.5)]), ("a", 17, 14, 4.5, -90, 90),
                      ("a", 11.5, 11.5, 6, 175, 300), ("a", 7, 14.75, 3.75, 90, 195)],
    "user-desktop": [("r", 3, 4, 18, 12, 1.5), ("l", [(12, 16), (12, 20)]), ("l", [(8, 20), (16, 20)])],
    "user-trash": [("l", [(4, 6.5), (20, 6.5)]), ("l", [(9, 6.5), (9.5, 3.5), (14.5, 3.5), (15, 6.5)]),
                   ("l", [(6, 6.5), (7, 20.5), (17, 20.5), (18, 6.5)]),
                   ("l", [(10, 10.5), (10, 16.5)]), ("l", [(14, 10.5), (14, 16.5)])],
    "user-trash-full": [("l", [(4, 6.5), (20, 6.5)]), ("l", [(9, 6.5), (9.5, 3.5), (14.5, 3.5), (15, 6.5)]),
                        ("l", [(6, 6.5), (7, 20.5), (17, 20.5), (18, 6.5)]),
                        ("l", [(9.5, 11), (14.5, 11)]), ("l", [(9.5, 14), (14.5, 14)]),
                        ("l", [(9.5, 17), (14.5, 17)])],
    "document-open-recent": [("c", 12, 12, 9), ("l", [(12, 7), (12, 12), (15.5, 14)])],
    "starred": [("f", _star())],
    "non-starred": [("p", _star())],
    "drive-harddisk": [("r", 3, 7, 18, 10, 2), ("d", 16.5, 12, 1.2), ("l", [(6.5, 12), (11, 12)])],
    "drive-removable-media": [("r", 7, 9, 10, 12, 1.5), ("l", [(9.5, 9), (9.5, 3.5), (14.5, 3.5), (14.5, 9)])],
    "media-optical": [("c", 12, 12, 9), ("c", 12, 12, 2.5)],
    "media-eject": [("p", [(5, 14), (12, 6), (19, 14)]), ("l", [(5, 18.5), (19, 18.5)])],
    "computer": [("r", 3, 4, 18, 12, 1.5), ("l", [(12, 16), (12, 20)]), ("l", [(8, 20), (16, 20)])],
    "network-server": [("r", 4, 3.5, 16, 7.5, 1.5), ("r", 4, 13, 16, 7.5, 1.5),
                       ("d", 16.5, 7.25, 1.1), ("d", 16.5, 16.75, 1.1)],
    "network-workgroup": [("c", 12, 12, 9), ("l", [(3, 12), (21, 12)]), ("e", 12, 12, 4, 9)],
    # header / toolbar
    "go-previous": [("l", [(15, 5), (8, 12), (15, 19)])],
    "go-next": [("l", [(9, 5), (16, 12), (9, 19)])],
    "go-up": [("l", [(5, 15), (12, 8), (19, 15)])],
    "go-down": [("l", [(5, 9), (12, 16), (19, 9)])],
    "pan-start": [("l", [(14, 7), (9, 12), (14, 17)])],
    "pan-end": [("l", [(10, 7), (15, 12), (10, 17)])],
    "pan-up": [("l", [(7, 14), (12, 9), (17, 14)])],
    "pan-down": [("l", [(7, 10), (12, 15), (17, 10)])],
    "edit-find": [("c", 10.5, 10.5, 6.5), ("l", [(15.3, 15.3), (20, 20)])],
    "zoom-in": [("c", 10.5, 10.5, 6.5), ("l", [(15.3, 15.3), (20, 20)]),
                ("l", [(10.5, 7.5), (10.5, 13.5)]), ("l", [(7.5, 10.5), (13.5, 10.5)])],
    "zoom-out": [("c", 10.5, 10.5, 6.5), ("l", [(15.3, 15.3), (20, 20)]), ("l", [(7.5, 10.5), (13.5, 10.5)])],
    "view-grid": [("r", 4, 4, 6, 6, 1), ("r", 14, 4, 6, 6, 1), ("r", 4, 14, 6, 6, 1), ("r", 14, 14, 6, 6, 1)],
    "view-list": [("l", [(9, 6), (20, 6)]), ("l", [(9, 12), (20, 12)]), ("l", [(9, 18), (20, 18)]),
                  ("d", 5, 6, 1.2), ("d", 5, 12, 1.2), ("d", 5, 18, 1.2)],
    "open-menu": [("l", [(4, 7), (20, 7)]), ("l", [(4, 12), (20, 12)]), ("l", [(4, 17), (20, 17)])],
    "view-more": [("d", 5.5, 12, 1.6), ("d", 12, 12, 1.6), ("d", 18.5, 12, 1.6)],
    "view-more-vertical": [("d", 12, 5.5, 1.6), ("d", 12, 12, 1.6), ("d", 12, 18.5, 1.6)],
    "sidebar-show": [("r", 3, 4, 18, 16, 2), ("l", [(9, 4), (9, 20)])],
    "sidebar-show-right": [("r", 3, 4, 18, 16, 2), ("l", [(15, 4), (15, 20)])],
    "nautilus-search-filters": [("l", [(4, 7), (20, 7)]), ("l", [(7, 12), (17, 12)]), ("l", [(10, 17), (14, 17)])],
    "view-refresh": _arrow_arc(),
    "emblem-synchronizing": _arrow_arc(),
    "edit-undo": [("l", [(8, 4.5), (4, 8.5), (8, 12.5)]), ("l", [(4, 8.5), (14.5, 8.5)]),
                  ("a", 14.5, 14, 5.5, -90, 90), ("l", [(14.5, 19.5), (8, 19.5)])],
    "edit-redo": [("l", [(16, 4.5), (20, 8.5), (16, 12.5)]), ("l", [(20, 8.5), (9.5, 8.5)]),
                  ("a", 9.5, 14, 5.5, 90, 270), ("l", [(9.5, 19.5), (16, 19.5)])],
    "edit-copy": [("r", 8, 8, 12, 12, 1.5), ("l", [(16, 5), (16, 4.5), (15.5, 4), (5.5, 4), (4, 5.5),
                                                  (4, 15.5), (4.5, 16), (5, 16)])],
    "edit-paste": [("r", 5, 5, 14, 16, 1.5), ("r", 9, 3, 6, 4, 1), ("l", [(9, 12), (15, 12)]),
                   ("l", [(9, 16), (13, 16)])],
    "edit-cut": [("c", 7, 17.5, 2.75), ("c", 17, 17.5, 2.75), ("l", [(8.8, 15.4), (17, 4)]),
                 ("l", [(15.2, 15.4), (7, 4)])],
    "edit-delete": [],          # filled from user-trash below
    "edit-clear": [("p", [(8.5, 5), (20, 5), (20, 19), (8.5, 19), (3, 12)]),
                   ("l", [(11.5, 9), (16.5, 15)]), ("l", [(16.5, 9), (11.5, 15)])],
    "edit-clear-rtl": [("p", [(15.5, 5), (4, 5), (4, 19), (15.5, 19), (21, 12)]),
                       ("l", [(7.5, 9), (12.5, 15)]), ("l", [(12.5, 9), (7.5, 15)])],
    "list-add": [("l", [(12, 5), (12, 19)]), ("l", [(5, 12), (19, 12)])],
    "list-remove": [("l", [(5, 12), (19, 12)])],
    "document-new": _page() + [("l", [(12, 11), (12, 17)]), ("l", [(9, 14), (15, 14)])],
    "bookmark-new": [("p", [(6, 3.5), (18, 3.5), (18, 20.5), (12, 16), (6, 20.5)])],
    "window-close": _x(12, 5.5),
    "process-stop": _x(12, 6),
    "window-minimize": [("l", [(6, 17), (18, 17)])],
    "window-maximize": [("r", 6, 6, 12, 12, 1.5)],
    "window-restore": [("r", 5, 9, 10, 10, 1.5), ("l", [(9, 6), (19, 6), (19, 15)])],
    "cancel-operation": [("c", 12, 12, 9)] + _x(12, 3.5),
    "object-select": [("l", [(5, 12.5), (10, 17.5), (19, 7)])],
    # emblems / status
    "info-outline": [("c", 12, 12, 9), ("l", [(12, 11), (12, 16.5)]), ("d", 12, 7.75, 1.2)],
    "dialog-warning": [("p", [(12, 3.5), (21, 19.5), (3, 19.5)]), ("l", [(12, 9.5), (12, 13.5)]),
                       ("d", 12, 16.5, 1.1)],
    "dialog-error": [("c", 12, 12, 9), ("l", [(12, 7), (12, 13)]), ("d", 12, 16.5, 1.2)],
    "symbolic-link": [("l", [(6, 19), (6, 14), (9.5, 10.5), (18, 10.5)]), ("l", [(14, 6.5), (18, 10.5), (14, 14.5)])],
    "readonly": [("r", 5, 10.5, 14, 10, 2), ("l", [(8, 10.5), (8, 8)]), ("a", 12, 8, 4, 180, 360),
                 ("l", [(16, 8), (16, 10.5)])],
    "not-accessible": [("c", 12, 12, 9), ("l", [(5.6, 18.4), (18.4, 5.6)])],
    "list-drag-handle": [("d", 9, 6, 1.4), ("d", 15, 6, 1.4), ("d", 9, 12, 1.4), ("d", 15, 12, 1.4),
                         ("d", 9, 18, 1.4), ("d", 15, 18, 1.4)],
}
SYMBOLIC["edit-delete"] = SYMBOLIC["user-trash"]

# alias -> drawn name (symlinked; "-symbolic" is appended to both)
SYMBOLIC_ALIASES = {
    "go-home": "user-home", "user-home-open": "user-home", "folder-projects": "folder",
    "folder-saved-search": "folder", "inode-directory": "folder", "folder-visiting": "folder-open",
    "folder-drag-accept": "folder-open",
    "drive-harddisk-system": "drive-harddisk", "drive-harddisk-usb": "drive-removable-media",
    "drive-harddisk-solidstate": "drive-harddisk", "media-removable": "drive-removable-media",
    "drive-optical": "media-optical", "network-computer": "computer", "video-display": "computer",
    "folder-network": "network-workgroup",
    "emblem-shared": "folder-publicshare", "system-search": "edit-find",
    "nautilus-folder-search": "edit-find", "view-more-horizontal": "view-more",
    "open-menu-horizontal": "view-more", "view-app-grid": "view-grid", "view-list-bullet": "view-list",
    "file-operation-cancelled": "cancel-operation", "file-operation-finished": "object-select",
    "emblem-ok": "object-select", "checkbox-checked": "object-select", "dialog-information": "info-outline",
    "help-about": "info-outline", "emblem-important": "dialog-warning", "emblem-symbolic-link": "symbolic-link",
    "emblem-readonly": "readonly", "changes-prevent": "readonly", "emblem-unreadable": "not-accessible",
    "edit-clear-all": "user-trash", "list-remove-all": "user-trash", "document-revert": "edit-undo",
}
# symbolic dirs: (dir, index.theme spec, line weight drawn for). GTK prefers the largest scalable
# dir for anything over its nominal size, so the common sizes are Fixed dirs holding SVGs.
SYMBOLIC_DIRS = tuple((f"symbolic/{n}", {"Size": n, "Context": "Actions", "Type": "Fixed"}, n)
                      for n in (16, 24, 32, 48)) + (
    ("symbolic/scalable", {"Size": 96, "MinSize": 49, "MaxSize": 512, "Context": "Actions",
                           "Type": "Scalable"}, 96),)


def _f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _circle(cx, cy, r, ccw=True):
    s = 0 if ccw else 1   # screen counter-clockwise = sweep 0, the orientation every shape uses
    return (f"M{_f(cx + r)} {_f(cy)}A{_f(r)} {_f(r)} 0 1 {s} {_f(cx - r)} {_f(cy)}"
            f"A{_f(r)} {_f(r)} 0 1 {s} {_f(cx + r)} {_f(cy)}Z")


def _capsule(p, q, r):
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = math.hypot(dx, dy)
    if n < 1e-6:
        return _circle(p[0], p[1], r)
    nx, ny = -dy / n * r, dx / n * r
    a, b = (p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny)
    c, e = (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)
    return (f"M{_f(a[0])} {_f(a[1])}L{_f(b[0])} {_f(b[1])}A{_f(r)} {_f(r)} 0 0 0 {_f(c[0])} {_f(c[1])}"
            f"L{_f(e[0])} {_f(e[1])}A{_f(r)} {_f(r)} 0 0 0 {_f(a[0])} {_f(a[1])}Z")


def _area(pts):
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))


def _poly(pts, hole=False):
    # every filled shape winds like the capsules (negative shoelace in y-down); holes the other way
    if (_area(pts) > 0) != hole:
        pts = pts[::-1]
    return "M" + "L".join(f"{_f(x)} {_f(y)}" for x, y in pts) + "Z"


def _rrect_pts(x, y, w, h, rad, step=10):
    rad = max(0.0, min(rad, w / 2, h / 2))
    pts = []
    for cx, cy, a0 in ((x + w - rad, y + rad, -90), (x + w - rad, y + h - rad, 0),
                       (x + rad, y + h - rad, 90), (x + rad, y + rad, 180)):
        for i in range(0, 91, step):
            a = math.radians(a0 + i)
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return pts


def _arc_pts(cx, cy, rx, ry, d0, d1, step=8):
    n = max(2, int(abs(d1 - d0) / step) + 1)
    return [(cx + rx * math.cos(math.radians(d0 + (d1 - d0) * i / (n - 1))),
             cy + ry * math.sin(math.radians(d0 + (d1 - d0) * i / (n - 1)))) for i in range(n)]


def outline(spec, w):
    """Line drawing -> one filled path (nonzero): every stroke segment becomes a capsule with
    round ends, so overlaps union cleanly and joins come out round."""
    r, parts = w / 2, []

    def polyline(pts, closed=False):
        seq = pts + pts[:1] if closed else pts
        parts.extend(_capsule(p, q, r) for p, q in zip(seq, seq[1:]))

    for item in spec:
        kind, args = item[0], item[1:]
        if kind == "l":
            polyline(list(args[0]))
        elif kind == "p":
            polyline(list(args[0]), closed=True)
        elif kind == "f":
            parts.append(_poly(list(args[0])))
            polyline(list(args[0]), closed=True)
        elif kind == "c":
            cx, cy, rad = args
            parts.append(_circle(cx, cy, rad + r) + _circle(cx, cy, max(rad - r, 0.01), ccw=False))
        elif kind == "d":           # dots shrink with the line weight at large sizes
            cx, cy, rad = args
            parts.append(_circle(cx, cy, rad * min(1.0, w / 1.7)))
        elif kind == "r":
            x, y, ww, hh, rad = args
            parts.append(_poly(_rrect_pts(x - r, y - r, ww + w, hh + w, rad + r)))
            if ww > w and hh > w:
                parts.append(_poly(_rrect_pts(x + r, y + r, ww - w, hh - w, max(rad - r, 0)), hole=True))
        elif kind == "a":
            cx, cy, rad, d0, d1 = args
            polyline(_arc_pts(cx, cy, rad, rad, d0, d1))
        elif kind == "e":          # closed ellipse line: cx, cy, rx, ry
            cx, cy, rx, ry = args
            polyline(_arc_pts(cx, cy, rx, ry, 0, 360)[:-1], closed=True)
    return "".join(parts)


def symbolic_svg(name, px):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24">'
            f'<path fill="#000" d="{outline(SYMBOLIC[name], stroke_units(px) * 1.15)}"/></svg>\n')


# ---------------------------------------------------------------- drawing
def _svg(body, glyph, px):
    stroke = (f'stroke="{GRAPHITE}" stroke-width="{stroke_units(px):.3f}" stroke-linecap="round" '
              f'stroke-linejoin="round"')
    out = [f'<g fill="{PAPER}" {stroke}>{body}</g>']
    if glyph and px > 16:
        out.append(f'<g fill="none" {stroke}>{glyph}</g>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
            + "".join(out) + "</svg>\n")


def folder_svg(name, px):
    glyph, open_ = FOLDERS[name]
    return _svg(OPEN if open_ else CLOSED, FOLDER_GLYPHS.get(glyph, ""), px)


def file_svg(category, px):
    return _svg(PAGE, FILE_GLYPHS[category], px)


# context dir -> (Context=, {file name: svg function}, {alias: file name})
def sets():
    files = {MIME[c].split()[0]: (lambda px, c=c: file_svg(c, px)) for c in MIME}
    aliases = {}
    for c, names in MIME.items():
        first, *rest = names.split()
        for n in rest:
            aliases[n] = first
    return {
        "places": ("Places", {n: (lambda px, n=n: folder_svg(n, px)) for n in FOLDERS}, {}),
        "mimetypes": ("MimeTypes", files, aliases),
    }


def render(src, px, dst):
    subprocess.run(["rsvg-convert", "-w", str(px), "-h", str(px), "-o", dst, src], check=True)


def index_theme(dirs):
    lines = ["# bench-grid: generated by tools/icons.py", "[Icon Theme]", "Name=Bench Grid Icons",
             "Comment=Line-drawn folders and files over Yaru-sage", "Inherits=Yaru-sage,Yaru,hicolor",
             "Example=folder", "Directories=" + ",".join(d for d, _ in dirs), ""]
    for d, spec in dirs:
        lines += [f"[{d}]"] + [f"{k}={v}" for k, v in spec.items()] + [""]
    return "\n".join(lines)


def link_aliases(dirpath, aliases, ext):
    for alias, target in aliases.items():
        os.symlink(target + ext, os.path.join(dirpath, alias + ext))


def build(out):
    if os.path.isdir(out):
        shutil.rmtree(out)
    dirs = []
    with tempfile.TemporaryDirectory() as tmp:
        src = {}
        for sub, (_, draw, _) in sets().items():
            for name, fn in draw.items():
                for px in (*FIXED, SCALABLE_BASE):
                    p = os.path.join(tmp, f"{sub}-{name}-{px}.svg")
                    with open(p, "w") as f:
                        f.write(fn(px))
                    src[sub, name, px] = p
        for size in FIXED:
            for scale in (1, 2):
                for sub, (context, draw, aliases) in sets().items():
                    d = f"{size}x{size}{'@2x' if scale == 2 else ''}/{sub}"
                    os.makedirs(os.path.join(out, d))
                    spec = {"Size": size, "Context": context, "Type": "Fixed"}
                    if scale == 2:
                        spec = {"Size": size, "Scale": 2, "Context": context, "Type": "Fixed"}
                    dirs.append((d, spec))
                    for name in draw:
                        render(src[sub, name, size], size * scale, os.path.join(out, d, name + ".png"))
                    link_aliases(os.path.join(out, d), aliases, ".png")
        for sub, (context, draw, aliases) in sets().items():
            d = f"scalable/{sub}"
            os.makedirs(os.path.join(out, d))
            dirs.append((d, {"Size": 256, "MinSize": 33, "MaxSize": 512, "Context": context,
                             "Type": "Scalable"}))
            for name in draw:
                shutil.copy(src[sub, name, SCALABLE_BASE], os.path.join(out, d, name + ".svg"))
            link_aliases(os.path.join(out, d), aliases, ".svg")
        for d, spec, base in SYMBOLIC_DIRS:
            os.makedirs(os.path.join(out, d))
            dirs.append((d, spec))
            for name in SYMBOLIC:
                with open(os.path.join(out, d, f"{name}-symbolic.svg"), "w") as f:
                    f.write(symbolic_svg(name, base))
            link_aliases(os.path.join(out, d),
                         {f"{a}-symbolic": f"{t}-symbolic" for a, t in SYMBOLIC_ALIASES.items()}, ".svg")
    with open(os.path.join(out, "index.theme"), "w") as f:
        f.write(index_theme(dirs))


def preview(out, sheet):
    """Folders, files, then UI icons; each size twice: on the keycap page, then on a mat selection."""
    groups = [("places", ["folder", "folder-open", "folder-documents", "folder-download", "folder-music",
                          "folder-pictures", "folder-videos", "folder-templates", "folder-publicshare",
                          "folder-remote", "user-home", "user-desktop"]),
              ("mimetypes", [MIME[c].split()[0] for c in MIME])]
    with tempfile.TemporaryDirectory() as tmp:
        rows = []
        for sub, names in groups:
            for size in (16, 24, 32, 48, 128):
                row = []
                for n in names:
                    p = os.path.join(tmp, f"{sub}-{n}-{size}.png")
                    shutil.copy(os.path.join(out, f"{size}x{size}/{sub}/{n}.png"), p)
                    row.append(p)
                for bg in (KEYCAP, MAT):
                    r = os.path.join(tmp, f"row-{sub}-{size}{bg[1:]}.png")
                    subprocess.run(["magick", "montage", *row, "-background", bg, "-geometry",
                                    f"{size}x{size}+{max(6, size // 5)}+8", "-tile", f"{len(row)}x1", r],
                                   check=True)
                    rows.append(r)
        names = list(SYMBOLIC)
        for size, d in ((16, "symbolic/16"), (24, "symbolic/24"), (48, "symbolic/48")):
            for bg, fg in ((KEYCAP, GRAPHITE), (MAT, KEYCAP)):
                row = []
                for n in names:
                    src = os.path.join(tmp, f"sym-{n}-{size}{fg[1:]}.svg")
                    with open(os.path.join(out, d, f"{n}-symbolic.svg")) as f:
                        svg_text = f.read().replace('fill="#000"', f'fill="{fg}"')
                    with open(src, "w") as f:
                        f.write(svg_text)
                    png = src[:-4] + ".png"
                    render(src, size, png)
                    row.append(png)
                r = os.path.join(tmp, f"row-sym-{size}{bg[1:]}.png")
                subprocess.run(["magick", "montage", *row, "-background", bg, "-geometry",
                                f"{size}x{size}+{max(5, size // 4)}+6", "-tile", f"{min(len(row), 32)}x", r],
                               check=True)
                rows.append(r)
        subprocess.run(["magick", *rows, "-background", KEYCAP, "-gravity", "west", "-append",
                        "-bordercolor", KEYCAP, "-border", "16", sheet], check=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    sheet = None
    if "--preview" in args:
        i = args.index("--preview")
        sheet = args[i + 1]
        del args[i:i + 2]
    build(args[0])
    if sheet:
        preview(args[0], sheet)
