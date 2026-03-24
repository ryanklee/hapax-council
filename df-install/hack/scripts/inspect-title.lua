local t = dfhack.gui.getViewscreenByType(df.viewscreen_titlest, 0)
if not t then
    print("NOT ON TITLE SCREEN")
    return
end
print("=== Title viewscreen fields ===")
for k, v in pairs(t) do
    local vstr = tostring(v)
    if #vstr > 80 then vstr = vstr:sub(1,80) .. "..." end
    print(("  %-30s %s = %s"):format(k, type(v), vstr))
end
