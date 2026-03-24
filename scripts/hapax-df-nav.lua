-- hapax-df-nav.lua — Screen reader + button clicker for DF navigation
--
-- Usage:
--   hapax-df-nav dump              -- dump entire screen as text
--   hapax-df-nav find <text>       -- find text on screen, report coords
--   hapax-df-nav click <text>      -- find and click a named button
--   hapax-df-nav focus             -- show current focus string
--   hapax-df-nav tree              -- dump screen text + focus for tree mapping

local gui = require("gui")

-- Read a single tile character
local function read_char(x, y)
    local pen = dfhack.screen.readTile(x, y)
    if not pen then return " " end
    local ch = pen.ch
    if type(ch) == "number" then
        if ch >= 32 and ch < 127 then return string.char(ch) end
        return "."
    end
    return ch or " "
end

-- Build full screen text map
local function build_screen_text()
    local w, h = dfhack.screen.getWindowSize()
    local lines = {}
    for y = 0, h - 1 do
        local row = {}
        for x = 0, w - 1 do
            row[#row + 1] = read_char(x, y)
        end
        lines[y] = table.concat(row)
    end
    return lines, w, h
end

-- Find all occurrences of text on screen
local function find_text(target)
    local lines, w, h = build_screen_text()
    local results = {}
    for y = 0, h - 1 do
        local line = lines[y]
        local pos = 1
        while true do
            local s, e = line:find(target, pos, true)
            if not s then break end
            table.insert(results, {
                x = s - 1,  -- 0-based tile coord
                y = y,
                click_x = s - 1 + math.floor((e - s) / 2),
                click_y = y,
            })
            pos = e + 1
        end
    end
    return results
end

-- Click at a tile position
local function click_at(x, y)
    local scr = dfhack.gui.getCurViewscreen()
    df.global.gps.mouse_x = x
    df.global.gps.mouse_y = y
    df.global.enabler.tracking_on = 1
    gui.simulateInput(scr, "_MOUSE_L")
end

-- Commands
local args = {...}
local cmd = args[1] or "focus"

if cmd == "dump" then
    local lines, w, h = build_screen_text()
    print(("[screen] %dx%d"):format(w, h))
    for y = 0, h - 1 do
        local trimmed = lines[y]:match("^(.-)%s*$")
        if #trimmed:gsub("%s+", "") > 0 then
            print(("%3d|%s"):format(y, trimmed))
        end
    end

elseif cmd == "find" then
    local target = table.concat(args, " ", 2)
    if #target == 0 then qerror("Usage: hapax-df-nav find <text>") end
    local results = find_text(target)
    if #results == 0 then
        print(("[find] '%s' not found"):format(target))
    else
        for _, r in ipairs(results) do
            print(("[find] '%s' at tile (%d, %d), click (%d, %d)"):format(
                target, r.x, r.y, r.click_x, r.click_y))
        end
    end

elseif cmd == "click" then
    local target = table.concat(args, " ", 2)
    if #target == 0 then qerror("Usage: hapax-df-nav click <text>") end
    local results = find_text(target)
    if #results == 0 then
        print(("[click] '%s' not found on screen"):format(target))
    else
        local r = results[1]
        click_at(r.click_x, r.click_y)
        print(("[click] Clicked '%s' at (%d, %d)"):format(target, r.click_x, r.click_y))
        dfhack.timeout(3, "frames", function()
            local focus = dfhack.gui.getCurFocus()
            print(("[click] Focus after: %s"):format(table.concat(focus, ", ")))
        end)
    end

elseif cmd == "focus" then
    local focus = dfhack.gui.getCurFocus()
    local scr = dfhack.gui.getCurViewscreen()
    print(("[focus] %s"):format(table.concat(focus, ", ")))
    print(("[focus] viewscreen: %s"):format(tostring(scr._type)))

elseif cmd == "tree" then
    -- Dump focus + all visible text (for tree mapping)
    local focus = dfhack.gui.getCurFocus()
    print(("=== Screen: %s ==="):format(table.concat(focus, ", ")))
    local lines, w, h = build_screen_text()
    local visible = {}
    for y = 0, h - 1 do
        local trimmed = lines[y]:match("^(.-)%s*$")
        local content = trimmed:gsub("%s+", "")
        if #content > 2 then
            table.insert(visible, ("%3d|%s"):format(y, trimmed))
        end
    end
    print(("[tree] %d non-empty rows out of %d"):format(#visible, h))
    for _, line in ipairs(visible) do
        print(line)
    end

else
    print("Usage: hapax-df-nav [dump|find|click|focus|tree] [args]")
end
