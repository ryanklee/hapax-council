local gui = require("gui")
local t = dfhack.gui.getViewscreenByType(df.viewscreen_titlest, 0)
if not t then print("NOT ON TITLE") return end

-- Method 1: try direct key for "New World"
print("Trying CURSOR_DOWN to NewWorld then SELECT...")
-- NewWorld is index 0 in menu_line_id (value=2)
-- selected is already 0, so just press SELECT
t.selected = 0
print("selected set to 0, menu_line_id[0] = " .. t.menu_line_id[0])
gui.simulateInput(t, "SELECT")
print("SELECT pressed")

-- Check if screen changed
dfhack.timeout(5, "frames", function()
    local focus = dfhack.gui.getCurFocus()
    print("After SELECT, focus: " .. (focus[1] or "nil"))
end)
