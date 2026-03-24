local t = dfhack.gui.getViewscreenByType(df.viewscreen_titlest, 0)
if not t then print("NOT ON TITLE") return end
print("menu_line_id count: " .. #t.menu_line_id)
for i = 0, #t.menu_line_id - 1 do
    print(("  [%d] = %d"):format(i, t.menu_line_id[i]))
end
print("selected = " .. t.selected)
print("mode = " .. t.mode)
