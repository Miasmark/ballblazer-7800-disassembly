# Ballblazer (Atari 7800) disassembly

A byte-identical disassembly and gameplay-mechanics investigation of
*Ballblazer* (NTSC, Atari/Lucasfilm, 1987), built with
[a7800-toolkit](https://github.com/) and MAME as a live-verification
instrument, not just a static reader.

**This repo does not contain the ROM.** Supply your own legally-owned dump
(`Ballblazer (NTSC) (Atari-Lucasfilm) (1987) (A4C4808B).a78`, alongside a
7800 BIOS) to reproduce anything here. The disassembly listing itself
(`src/rom.asm`) isn't committed either -- it's fully generated from
[`annotations.json`](annotations.json) plus the ROM, and regenerating it is
one command (below).

## Start here

[`docs/FINDINGS.md`](docs/FINDINGS.md) is the real deliverable: a
chronological narrative of every mechanism investigated, what was
confirmed live in MAME (with the exact recording and frame cited), what
was retracted and why, and what's still open. [`annotations.json`](annotations.json)
is the machine-readable form of the same knowledge -- 45 data blocks, 56
header comments, 65 labels -- that actually drives the disassembler.

Working discipline, if you're picking this up: every claim about what a
byte range or mechanism does is checked live (a MAME Lua write/read tap,
PC-tagged to find the real writer, cross-checked against a screenshot or a
direct framebuffer read -- see the `video:snapshot()` pitfall in the
toolkit's `docs/pitfalls.md`) rather than asserted from static reading
alone. Every `annotations.json` change is followed by JSON validation,
`disasm.py` regeneration, and a `verify.py` byte-identical round-trip
check. Mistakes are retracted in place in the documentation, not silently
fixed -- `docs/FINDINGS.md` has several, and they're left visible on
purpose.

## Reproducing it

```
# from this directory, with the toolkit checked out as a sibling (adjust
# the path below to wherever you have it) and your own ROM copy dropped in:

python3 ../a7800-toolkit/tools/disasm.py "Ballblazer (NTSC) (Atari-Lucasfilm) (1987) (A4C4808B).a78" -c annotations.json -o src
python3 ../a7800-toolkit/tools/verify.py "Ballblazer (NTSC) (Atari-Lucasfilm) (1987) (A4C4808B).a78" -d src
# -> ROUND-TRIP PASSED
```

`src/rom.asm` is then a full listing, byte-identical when reassembled.

## Reproducing the live findings

`run-01.inp` / `run-02.inp` / `run-03.inp` are MAME input recordings --
deterministic button-press logs, not video, and not copyrighted content --
that reproduce the exact game states `docs/FINDINGS.md` cites by frame
number. Replay one with:

```
./"Play Recording.command" run-03
```

or drive it headless with a Lua probe the way the findings do:

```
mame a7800 -rompath /path/to/bios -input_directory . \
  -cart "Ballblazer (NTSC) (Atari-Lucasfilm) (1987) (A4C4808B).a78" \
  -playback run-03.inp -autoboot_script your-probe.lua \
  -video none -sound none -nothrottle -str 320
```

`tools/` holds this project's own probe/build scripts (`live-slots.lua`,
`ball-raster.lua`, `build_coverage.py`, `build_gallery.py`, `build_html.py`) --
generic instrument code lives in the toolkit itself, these are specific to
questions this particular game raised.

## Layout

| | |
|---|---|
| `annotations.json` | The recipe. Feed it to `disasm.py` to get the listing. |
| `docs/FINDINGS.md` | The narrative -- read this first. |
| `docs/sprites.html` | Graphics gallery (built with `tools/build_gallery.py` / `build_html.py`). |
| `docs/color-cycle-table.txt`, `docs/dlwalk-output.txt` | Decoded reference data cited from `FINDINGS.md`. |
| `docs/img/` | Screenshots cited as evidence for specific live findings. |
| `run-*.inp` | MAME input recordings the live findings were checked against. |
| `tools/` | This project's own probe and build scripts. |
| `Play Recording.command`, `Record Session.command` | Double-click launchers for replaying/recording a session (macOS + MAME on `PATH`). |

Not committed (see `.gitignore`): the ROM, the generated `src/rom.asm` and
`build/`, audio/video renders, raw memory dumps, and a few regeneratable
analysis manifests -- all reproducible from the ROM and the recordings
above.
