local focus = dfhack.gui.getCurFocus()
for i, f in ipairs(focus) do
    print(("Focus[%d]: %s"):format(i, f))
end
local scr = dfhack.gui.getCurViewscreen()
print("Viewscreen type: " .. tostring(scr._type))
