import sys, os, base64, io
sys.path.insert(0, "/Users/thucom/Documents/Atari 7800/a7800-toolkit/tools")
from gfx import render_direct, render_charset, GREY
from disasm import Cart

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(PROJECT, "build")
os.makedirs(BUILD, exist_ok=True)

ROM = os.path.join(PROJECT, "Ballblazer (NTSC) (Atari-Lucasfilm) (1987) (A4C4808B).a78")
cart = Cart(ROM)

# (addr, width, category, sources)
ENTRIES = [
    # floor tiles -- confirmed diagonal-edge / solid-fill tileset
    (0x8020, 24, "floor", "title"),
    (0x8033, 24, "floor", "gameplay/spin"),
    (0x8038, 21, "floor", "title"),
    (0x804B, 21, "floor", "gameplay"),
    (0x8082, 24, "floor", "spin"),
    (0x8085, 24, "floor", "title"),
    (0x809A, 24, "floor", "spin"),
    (0x809D, 24, "floor", "title"),
    (0x80A0, 24, "floor", "gameplay"),
    (0x80B8, 24, "floor", "gameplay"),
    (0x881D, 24, "floor", "spin"),
    (0x881F, 24, "floor", "title"),
    (0x8833, 24, "floor", "gameplay/spin"),
    (0x8835, 24, "floor", "spin"),
    (0x8837, 24, "floor", "title"),
    (0x884B, 24, "floor", "gameplay"),
    (0x8875, 24, "floor", "title/gameplay/spin"),
    (0x8889, 24, "floor", "gameplay"),
    (0x888D, 27, "floor", "title/gameplay/spin"),
    (0x88A1, 27, "floor", "gameplay"),
    # narrow palette-4 objects, zones 20-22 -- unidentified (ball candidate)
    (0x989E, 1, "unident", "gameplay/spin"),
    (0x9AA2, 1, "unident", "gameplay"),
    (0x9AA3, 1, "unident", "spin"),
    (0xA2A2, 1, "unident", "gameplay"),
    (0xA2A3, 1, "unident", "spin"),
    # spin fragment sheet -- small diagonal wedges, same vocabulary as floor
    (0x9F1E, 7, "spin-frag", "spin"),
    (0x9F22, 6, "spin-frag", "spin"),
    (0xA20A, 7, "spin-frag", "spin"),
    (0xA20E, 6, "spin-frag", "spin"),
    (0xA51E, 7, "spin-frag", "spin"),
    (0xA522, 6, "spin-frag", "spin"),
    (0xA659, 6, "spin-frag", "spin"),
    (0xA65D, 5, "spin-frag", "spin"),
    (0xA80A, 2, "spin-frag", "spin"),
    (0xA80E, 6, "spin-frag", "spin"),
    (0xA811, 3, "spin-frag", "spin"),
    (0xA812, 2, "spin-frag", "spin"),
    (0xA85A, 4, "spin-frag", "spin"),
    (0xA85D, 4, "spin-frag", "spin"),
    (0xAABF, 3, "spin-frag", "spin"),
    (0xAF8F, 3, "spin-frag", "spin"),
]

def to_data_uri(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

cells = []
for addr, width, cat, src in ENTRIES:
    img = render_direct(cart, "rom", addr, width, 8, GREY, scale=8)
    cells.append({
        "addr": addr, "width": width, "cat": cat, "src": src,
        "uri": to_data_uri(img), "w": img.width, "h": img.height,
    })

charset_img = render_charset(cart, "rom", 0xA000, 8, GREY, scale=3)
charset_uri = to_data_uri(charset_img)

import json
with open(os.path.join(BUILD, "cells.json"), "w") as f:
    json.dump({"cells": cells, "charset_uri": charset_uri,
               "charset_w": charset_img.width, "charset_h": charset_img.height}, f)
print(f"rendered {len(cells)} cells + character set")
