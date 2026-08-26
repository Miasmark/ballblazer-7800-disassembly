-- live-slots.lua -- replay a recording and record, for the whole run:
--   1. every ROM address the live display lists reference (direct-mode gfx
--      data and indirect charsets), with the max width seen, so unconfirmed
--      sheet slots can be confirmed or left red on evidence;
--   2. whether the unreached-code window $B15E-$B1F3 ever executes
--      (opcode fetches are reads, so a read tap catches them).
--
--   mame a7800 -rompath ../bios -cart <rom> -skip_gameinfo -video none \
--       -sound none -nothrottle -playback run-01.inp \
--       -autoboot_script tools/live-slots.lua -str 600
--
-- Writes live-slots-<recording>.json next to this file at the end.

local MACHINE = (type(manager.machine) == "function")
                and manager:machine() or manager.machine
local mem = MACHINE.devices[":maincpu"].spaces["program"]

local F, dpph, dppl = 0, nil, nil
local refs = {}          -- addr -> max width seen
local b15e_reads = 0
local first_b15e_frame = nil

-- keep every tap in a global (the GC trap; see watch.lua)
TAP_MARIA = mem:install_write_tap(0x20, 0x3F, "maria regs", function(offset, data)
  if offset == 0x2C then dpph = data end
  if offset == 0x30 then dppl = data end
  return data
end)

TAP_CODE = mem:install_read_tap(0xB15E, 0xB1F3, "unreached code window",
  function(offset, data)
    b15e_reads = b15e_reads + 1
    if not first_b15e_frame then first_b15e_frame = F end
    return data
  end)

local function byte(a) return mem:read_u8(a) end

local function walk_dl(addr)
  -- mirrors: DLs built through $0040-$01FF live one page up in the dump,
  -- but the CPU space already resolves those reads correctly.
  for _ = 1, 48 do
    local b0, b1 = byte(addr), byte(addr + 1)
    if b1 == 0 then return end                    -- terminator
    local gfx, width, len
    if (b1 & 0x1F) == 0 then                     -- 5-byte extended entry
      local b2, b3 = byte(addr + 2), byte(addr + 3)
      gfx, width, len = b0 | (b2 << 8), (~b3 & 0x1F) + 1, 5
    else                                          -- 4-byte direct entry
      local b2 = byte(addr + 2)
      gfx, width, len = b0 | (b2 << 8), (~b1 & 0x1F) + 1, 4
    end
    if gfx >= 0x8000 and gfx < 0x10000 then
      if not refs[gfx] or width > refs[gfx] then refs[gfx] = width end
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
    if b1 >= 0x80 then break end                 -- high bit = last entry
  end
end

emu.register_frame_done(function()
  F = F + 1
  if dpph and dppl then walk_dll((dpph << 8) | dppl) end
  if F % 300 == 0 then dump() end   -- checkpoint; no exit hook on this MAME
end)

function dump()   -- global: the frame hook is registered above
  local parts = {}
  for a, w in pairs(refs) do
    parts[#parts + 1] = string.format('{"addr":%d,"width":%d}', a, w)
  end
  local out = string.format(
    '{"frames":%d,"refs":[%s],"b15e_reads":%d,"first_b15e_frame":%s}\n',
    F, table.concat(parts, ","),
    b15e_reads, first_b15e_frame and tostring(first_b15e_frame) or "null")
  local name = "live-slots-out.json"
  local h = io.open(name, "w")
  if h then h:write(out) h:close() print("wrote " .. name) end
  print(string.format("frames=%d rom refs=%d b15e_reads=%d first=%s",
    F, #parts, b15e_reads, first_b15e_frame or "never"))
end
