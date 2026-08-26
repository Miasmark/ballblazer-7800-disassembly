-- ball-raster.lua -- FINDINGS item 14: find the writer that renders the ball.
-- v2: this MAME build's Lua exposes no hpos()/vpos() on the screen device, so
-- beam position is derived from machine.time() instead:
--   * WSYNC write times calibrate ticks-per-scanline L (DLI loops hit WSYNC
--     exactly once per line, so the minimum positive delta between WSYNC
--     writes IS L), and give the phase anchor for "just after line start";
--   * every colour-register write is stamped with phase = t mod L, grouped
--     by writing PC. Static clusters = ordinary DLI code. A cluster whose
--     phase drifts smoothly frame to frame is a beam-racer tracking a
--     moving object -- the expected fingerprint of the ball.
-- Also logs every narrow (<=4-byte) display-list entry per frame with hpos,
-- since the earlier "not a DL object" conclusion only checked zones 0-6.
--
--   mame a7800 -rompath ../bios -cart <rom> -video none -sound none
--       -nothrottle -playback run-01.inp -autoboot_script ball-raster.lua
--       -str 320
-- Writes ball-raster-colour.txt, ball-raster-narrow.txt in the cwd.

local MACHINE = (type(manager.machine) == "function")
                and manager:machine() or manager.machine
local cpu = MACHINE.devices[":maincpu"]
local mem = cpu.spaces["program"]

local CPU_CLOCK = 1789772            -- NTSC 6502, close enough for phase work
local F = 0
local t0 = nil
local function ticks()               -- machine time in CPU ticks since boot
  -- NB: machine.time is a property (attotime), NOT a method -- calling it
  -- errors, and an error inside a tap callback is silently swallowed, which
  -- makes the tap look dead.
  if not t0 then t0 = MACHINE.time:as_ticks(CPU_CLOCK) end
  return MACHINE.time:as_ticks(CPU_CLOCK) - t0
end

-- ---- one tap for WSYNC calibration + colour writes (overlapping taps
-- silently stop each other firing in this MAME build, so keep it single) --
local ws_times = {}                  -- first 400 WSYNC write times
local ws_n = 0
local col = io.open("ball-raster-colour.txt", "w")
local DETAIL_FROM, DETAIL_TO = 2890, 2990
local L = nil                        -- ticks per scanline, calibrated later

COLTAP = mem:install_write_tap(0x20, 0x27, "maria colours", function(offset, data)
  local t = ticks()
  if offset == 0x24 then
    if ws_n < 400 then
      ws_n = ws_n + 1
      ws_times[ws_n] = t
    end
    return data
  end
  local pc = cpu.state["PC"].value
  if L then
    local phase = t % L
    col:write(string.format("%d %04X %02X %02X %d %d\n",
      F, pc, offset, data, t, phase))
  else
    col:write(string.format("%d %04X %02X %02X %d -1\n", F, pc, offset, data, t))
  end
  return data
end)

-- ---- narrow display-list entries --------------------------------------
local dpph, dppl = nil, nil
DLLTAP = mem:install_write_tap(0x2C, 0x31, "dll", function(offset, data)
  if offset == 0x2C then dpph = data end
  if offset == 0x30 then dppl = data end
  return data
end)

local narrow = io.open("ball-raster-narrow.txt", "w")
local function byte(a) return mem:read_u8(a) end

local function walk_dl(addr)
  for _ = 1, 48 do
    local b0, b1 = byte(addr), byte(addr + 1)
    if b1 == 0 then return end
    local gfx, width, len, hpos, pal
    if (b1 & 0x1F) == 0 then
      local b2, b3, b4 = byte(addr + 2), byte(addr + 3), byte(addr + 4)
      gfx = b0 | (b2 << 8); width = (~b3 & 0x1F) + 1
      hpos = b4; pal = (b3 >> 5) & 7; len = 5
    else
      local b2, b3 = byte(addr + 2), byte(addr + 3)
      gfx = b0 | (b2 << 8); width = (~b1 & 0x1F) + 1
      hpos = b3; pal = (b1 >> 5) & 7; len = 4
    end
    if gfx >= 0x8000 and width <= 4 then
      narrow:write(string.format("%d %04X %d %d %d\n",
        F, gfx, width, hpos, pal))
    end
    addr = addr + len
  end
end

local function walk_dll(base)
  for z = 0, 31 do
    local a = base + 3 * z
    local b0, b1, b2 = byte(a), byte(a + 1), byte(a + 2)
    local dl = (b1 << 8) | b2
    if dl == 0 or (b1 == 0 and b2 == 0) then break end
    walk_dl(dl)
    if b1 >= 0x80 then break end
  end
end

-- ---- calibration and frame loop ---------------------------------------
local calibrated = false
local function calibrate()
  table.sort(ws_times)
  local best = nil
  for i = 2, #ws_times do
    local d = ws_times[i] - ws_times[i - 1]
    if d > 24 and (not best or d < best) then best = d end
  end
  if best then
    L = best
    calibrated = true
    print(string.format("calibrated L=%d ticks/scanline (%d samples)", L, #ws_times))
  end
end

emu.register_frame_done(function()
  F = F + 1
  if not calibrated and ws_n >= 400 then calibrate() end
  if dpph and dppl then walk_dll((dpph << 8) | dppl) end
  if F % 600 == 0 then print(string.format("frame %d, L=%s", F, tostring(L))) end
  if F % 2000 == 0 then
    col:flush(); narrow:flush()
  end
end)
