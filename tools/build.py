#!/usr/bin/env python3
"""
One-command rebuild of everything generated in this project.

Runs, in order (any failure stops the build):
  1. disasm   -- regenerate src/rom.asm from the ROM + annotations.json
  2. verify   -- reassemble the listing, byte-for-byte identity check
  3. build    -- rebuild build/rebuilt.a78 from the listing
  4. gallery  -- render known graphics cells to build/cells.json
  5. coverage -- ROM coverage map + gap list (build/coverage.png, gaps.json)
  6. html     -- docs/sprites.html tying it all together

Usage: python3 tools/build.py [rom.a78]   (default: the ROM in this folder)
"""
import glob
import os
import subprocess
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLKIT = "/Users/thucom/Documents/Atari 7800/a7800-toolkit/tools"
sys.path.insert(0, TOOLKIT)

ROM = sys.argv[1] if len(sys.argv) > 1 else None
if ROM is None:
    matches = sorted(glob.glob(os.path.join(PROJECT, "*.a78")))
    if len(matches) != 1:
        sys.exit(f"expected exactly one .a78 in {PROJECT}, found {len(matches)}")
    ROM = matches[0]

ANNOT = os.path.join(PROJECT, "annotations.json")


def run(label, args):
    print(f"\n=== {label} ===", flush=True)
    r = subprocess.run([sys.executable] + args, cwd=PROJECT)
    if r.returncode != 0:
        sys.exit(f"{label} failed (exit {r.returncode})")


run("disasm", [os.path.join(TOOLKIT, "disasm.py"), ROM,
               "-c", ANNOT, "-o", "src"])
run("verify", [os.path.join(TOOLKIT, "verify.py"), ROM, "-d", "src"])
run("rebuild", [os.path.join(TOOLKIT, "build.py"), ROM, "-d", "src",
                "-o", "build/rebuilt.a78"])
run("gallery", [os.path.join(PROJECT, "tools", "build_gallery.py")])
run("coverage", [os.path.join(PROJECT, "tools", "build_coverage.py")])
run("html", [os.path.join(PROJECT, "tools", "build_html.py")])

print("\nbuild complete: src/rom.asm, build/, docs/sprites.html all regenerated")
