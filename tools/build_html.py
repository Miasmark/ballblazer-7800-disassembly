import json, html, base64, os

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(PROJECT, "build")

with open(os.path.join(BUILD, "cells.json")) as f:
    data = json.load(f)
with open(os.path.join(BUILD, "gaps.json")) as f:
    gaps = json.load(f)
with open(os.path.join(BUILD, "coverage.png"), "rb") as f:
    coverage_uri = "data:image/png;base64," + base64.b64encode(f.read()).decode()

CAT_INFO = {
    "floor": ("Floor / corridor tiles", "Confirmed: chequerboard diagonal-edge tiles and solid wall/sky fills. Same subsystem as DrawGridScanlines/AdvanceRowColorPhase. Not sprites."),
    "unident": ("Long-range opponent marker (zones 20-22)", "CONFIRMED: the opponent ship's long-range representation. 4px wide, palette 4. A live capture shows the opponent renders as exactly one of these dots while far away, then switches to the fragment-assembled silhouette below once close -- a distance-based level of detail (LOD) transition, not two unrelated objects."),
    "spin-frag": ("Ship fragment sheet ($9800-$AFxx)", "CONFIRMED: this is the ship's general close-range renderer, not spin-exclusive. RotationPhaseToFragment/PickSpinFragment assemble a triangular Rotofoil silhouette from these diagonal wedges every frame once the opponent is near, scaled/placed via a second math-table reader (sub_BD80, see docs/FINDINGS.md item 7). The match-end spin is the same mechanism forced to cycle at maximum speed. See docs/img/ship-lod-*.png for the live progression."),
}

by_cat = {}
for c in data["cells"]:
    by_cat.setdefault(c["cat"], []).append(c)

def cell_html(c):
    return f'''<div class="cell">
      <img src="{c['uri']}" width="{c['w']}" height="{c['h']}" alt="${c['addr']:04X}">
      <div class="label">${c['addr']:04X} &middot; {c['width']}B wide</div>
      <div class="src">{html.escape(c['src'])}</div>
    </div>'''

sections = []
for cat, (title, desc) in CAT_INFO.items():
    cells = by_cat.get(cat, [])
    cells_html = "\n".join(cell_html(c) for c in sorted(cells, key=lambda c: c["addr"]))
    sections.append(f'''
    <section>
      <h2>{html.escape(title)} <span class="count">({len(cells)})</span></h2>
      <p class="desc">{html.escape(desc)}</p>
      <div class="grid">{cells_html}</div>
    </section>''')

gaps_rows = "\n".join(
    f'<tr><td>${lo:04X}-${hi-1:04X}</td><td>{hi-lo}</td><td>{"confirmed math table, not graphics -- 1792 bytes, one continuous monotonic curve $E7-$00 across all 7 pages" if lo <= 0x9000 < hi or lo <= 0x9700 <= hi else ""}</td></tr>'
    for lo, hi in gaps["big_gaps"]
)

total = gaps["size"]
live_n = gaps.get("live_n", 0)
html_out = f'''<title>Ballblazer graphics dump</title>
<style>
  :root {{
    --bg: #ffffff; --fg: #1b1b1f; --muted: #6b6b76; --border: #dcdce2;
    --card: #f7f7fa; --accent: #3d5aa8;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #16161a; --fg: #e8e8ee; --muted: #9a9aa6;
      --card: #1f1f26; --border: #2e2e38; --accent: #7f9be0;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #16161a; --fg: #e8e8ee; --muted: #9a9aa6;
    --card: #1f1f26; --border: #2e2e38; --accent: #7f9be0;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg); color: var(--fg); margin: 0; padding: 32px;
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: var(--muted); margin: 0 0 28px; font-size: 14px; }}
  h2 {{ font-size: 16px; margin: 36px 0 4px; border-top: 1px solid var(--border); padding-top: 20px; }}
  .count {{ color: var(--muted); font-weight: normal; font-size: 13px; }}
  .desc {{ color: var(--muted); font-size: 13px; margin: 4px 0 16px; max-width: 720px; }}
  .grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .cell {{
    background: var(--card); border: 1px solid var(--border); border-radius: 6px;
    padding: 8px; text-align: center; overflow-x: auto; max-width: 260px;
  }}
  .cell img {{ image-rendering: pixelated; display: block; margin: 0 auto 6px; max-width: 100%; }}
  .label {{ font-family: ui-monospace, monospace; font-size: 12px; }}
  .src {{ font-size: 11px; color: var(--muted); }}
  .charset-wrap {{ overflow-x: auto; background: var(--card); border: 1px solid var(--border);
    border-radius: 6px; padding: 12px; }}
  .charset-wrap img {{ image-rendering: pixelated; }}
  .coverage-wrap {{ display: flex; gap: 24px; align-items: flex-start; flex-wrap: wrap; }}
  .coverage-wrap img {{ image-rendering: pixelated; border: 1px solid var(--border); border-radius: 6px; max-width: 100%; }}
  .stats {{ font-size: 13px; }}
  .stats div {{ margin: 4px 0; }}
  .swatch {{ display: inline-block; width: 12px; height: 12px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }}
  table {{ border-collapse: collapse; font-size: 12px; width: 100%; max-width: 720px; }}
  th, td {{ text-align: left; padding: 4px 10px 4px 0; border-bottom: 1px solid var(--border); font-family: ui-monospace, monospace; }}
  th {{ color: var(--muted); font-weight: normal; }}
  .note {{ font-size: 13px; color: var(--muted); max-width: 720px; }}
</style>

<h1>Ballblazer &mdash; known graphics dump</h1>
<p class="sub">Every graphics address found across three live display-list captures (title screen, ordinary gameplay, match-end spin), rendered with the correct per-object width/height (<code>gfx.py --direct</code>), plus a full ROM coverage map so gaps are visible at a glance. Generated for visual review -- if the ship is here, it should be findable by eye even where static tracing hasn't named it.</p>

<h2>Character set <span class="count">(256 characters, $A000-$A7FF, indirect mode -- confirmed)</span></h2>
<p class="desc">Terrain tiles and the digit/letter font used for the title logo, HUD, and menus. Rendered with the toolkit's ordinary indirect-mode grid, which is the correct tool for this address.</p>
<div class="charset-wrap"><img src="{data['charset_uri']}" width="{data['charset_w']}" height="{data['charset_h']}"></div>

{"".join(sections)}

<h2>ROM coverage map</h2>
<p class="desc">One pixel per ROM byte ($8000-$FFFF), 256 bytes per row. Green = reached as code by the disassembler. Blue = known graphics/data with reader evidence. Gold = live-referenced by display lists during run-01/02/03 replays (line-planar spread, not yet annotated). Red = unaccounted for.</p>
<div class="coverage-wrap">
  <img src="{coverage_uri}" width="768" height="384">
  <div class="stats">
    <div><span class="swatch" style="background:#468f5a"></span>Code: {gaps['code_n']} bytes ({gaps['code_n']/total:.1%})</div>
    <div><span class="swatch" style="background:#4664c8"></span>Known graphics/data: {gaps['gfx_n']} bytes ({gaps['gfx_n']/total:.1%})</div>
    <div><span class="swatch" style="background:#b48c3c"></span>Live-referenced (unannotated): {live_n} bytes ({live_n/total:.1%})</div>
    <div><span class="swatch" style="background:#c83c3c"></span>Unaccounted for: {gaps['unk_n']} bytes ({gaps['unk_n']/total:.1%})</div>
  </div>
</div>

<h2>Unaccounted-for regions (16+ contiguous bytes)</h2>
<p class="note">Gold regions on the map above are floor-tile and ship-fragment sheet slots confirmed referenced by live display lists across all three replays but not yet promoted to annotation blocks (they share the same per-page slot layout as the already-annotated tiles, so they are the same type of data -- animation phases not hit by the original three captures). The remaining red gaps are either alignment padding, untraced code paths, or sub-byte tables that need further reader tracing. $9000-$96FF is confirmed NOT graphics -- a monotonic perspective-divide curve (see docs/FINDINGS.md).</p>
<table>
<tr><th>range</th><th>bytes</th><th>note</th></tr>
{gaps_rows}
</table>
'''

out_path = os.path.join(PROJECT, "docs", "sprites.html")
with open(out_path, "w") as f:
    f.write(html_out)
print(f"wrote {out_path}, {len(html_out)} bytes")
