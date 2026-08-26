import os, re, json
from PIL import Image

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(PROJECT, "build")
os.makedirs(BUILD, exist_ok=True)

ROM_START, ROM_END = 0x8000, 0x10000  # exclusive end
SIZE = ROM_END - ROM_START

status = bytearray(SIZE)  # 0=unknown, 1=code, 2=known graphics/data, 3=live-referenced gfx

# 1. code coverage: parse every instruction/byte line's address from the listing
asm_path = os.path.join(PROJECT, "src", "rom.asm")
addr_re = re.compile(r";\s*([0-9A-F]{4}):")
byte_re = re.compile(r"^\s*\.byte\s")
with open(asm_path) as f:
    for line in f:
        m = addr_re.search(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        if not (ROM_START <= addr < ROM_END):
            continue
        # crude instruction length: count how many "XX " hex byte groups appear
        # after the address in the comment (disasm prints raw bytes there)
        tail = line[m.end():]
        hexbytes = re.findall(r"\b[0-9A-F]{2}\b", tail)
        n = max(1, min(len(hexbytes), 3))
        for i in range(n):
            if addr + i < ROM_END:
                status[addr + i - ROM_START] = 1

# 2. known graphics footprints (line-planar: width bytes at base+n*256, n=0..7)
with open(os.path.join(BUILD, "cells.json")) as f:
    data = json.load(f)
for c in data["cells"]:
    base, width = c["addr"], c["width"]
    for n in range(8):
        for col in range(width):
            a = base + n * 256 + col
            if ROM_START <= a < ROM_END:
                status[a - ROM_START] = 2

# character set: $A000-$A7FF, full 2048 bytes (256 chars x 8 lines)
for a in range(0xA000, 0xA800):
    status[a - ROM_START] = 2

# every data block declared in annotations.json (each one carries reader
# evidence in its note); code traced by the disassembler keeps priority
import json
with open(os.path.join(PROJECT, "annotations.json")) as f:
    annot = json.load(f)
for b in annot.get("blocks", []):
    def parse(s):
        return int(s.split(":")[1], 16)
    lo, hi = parse(b["loc"]), parse(b["end"])
    for a in range(lo, hi):
        if ROM_START <= a < ROM_START + SIZE and status[a - ROM_START] == 0:
            status[a - ROM_START] = 2

# 4. live-referenced graphics: bytes the display lists actually point at during
# the run-01/02/03 replays (tools/live-slots.lua), spread line-planar
# (width bytes at base+n*256, n=0..7). Evidence, not annotation: these stay
# a separate colour until a block with a reader is written for them.
ls = os.path.join(PROJECT, "live-slots.json")
if os.path.exists(ls):
    with open(ls) as f:
        for e in json.load(f)["refs"]:
            for n in range(8):
                for c in range(e["width"]):
                    a = e["addr"] + n * 256 + c
                    if ROM_START <= a < ROM_START + SIZE and status[a - ROM_START] == 0:
                        status[a - ROM_START] = 3

unknown_ranges = []
start = None
for i, s in enumerate(status):
    if s == 0:
        if start is None:
            start = i
    else:
        if start is not None:
            unknown_ranges.append((start + ROM_START, i + ROM_START))
            start = None
if start is not None:
    unknown_ranges.append((start + ROM_START, SIZE + ROM_START))

# only report gaps of real size (skip 1-3 byte noise between instructions)
big_gaps = [(lo, hi) for lo, hi in unknown_ranges if hi - lo >= 16]

code_n = status.count(1)
gfx_n = status.count(2)
live_n = status.count(3)
unk_n = status.count(0)
print(f"code: {code_n} ({code_n/SIZE:.1%})  known graphics/data: {gfx_n} ({gfx_n/SIZE:.1%})  live-ref'd: {live_n} ({live_n/SIZE:.1%})  unknown: {unk_n} ({unk_n/SIZE:.1%})")
print(f"{len(big_gaps)} unknown gaps of 16+ bytes:")
for lo, hi in big_gaps:
    print(f"  ${lo:04X}-${hi-1:04X}  ({hi-lo} bytes)")

# build a compact heatmap image: 128 rows x 256 cols, one pixel per byte
img = Image.new("RGB", (256, 128))
px = img.load()
COLORS = {0: (200, 60, 60), 1: (70, 130, 90), 2: (70, 100, 200), 3: (180, 140, 60)}
for i in range(SIZE):
    x, y = i % 256, i // 256
    px[x, y] = COLORS[status[i]]
img = img.resize((256*3, 128*3), Image.NEAREST)
img.save(os.path.join(BUILD, "coverage.png"))

with open(os.path.join(BUILD, "gaps.json"), "w") as f:
    json.dump({"big_gaps": big_gaps, "code_n": code_n, "gfx_n": gfx_n, "live_n": live_n, "unk_n": unk_n, "size": SIZE}, f)
