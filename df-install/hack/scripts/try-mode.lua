local t = dfhack.gui.getViewscreenByType(df.viewscreen_titlest, 0)
if not t then print("NOT ON TITLE") return end

-- mode 0 = main menu. Let's try setting mode to trigger transition.
-- First, let's see what happens with game_start_proceed
print("game_start_proceed: " .. t.game_start_proceed)
print("mode: " .. t.mode)

-- Method: set mode directly and see what values trigger transitions
-- mode=1 might be "start playing" submenu
-- mode=2 might be world gen
-- Let's try mode=2 (might go to world gen)
t.mode = 2
print("Set mode to 2")

dfhack.timeout(10, "frames", function()
    local focus = dfhack.gui.getCurFocus()
    print("After mode=2, focus: " .. (focus[1] or "nil"))
    local scr = dfhack.gui.getCurViewscreen()
    print("Viewscreen: " .. tostring(scr._type))
end)
