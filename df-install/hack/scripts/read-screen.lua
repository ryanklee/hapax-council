local gps = df.global.gps
print(("Screen dims: %dx%d"):format(gps.dimx, gps.dimy))
print(("Mouse: %d, %d"):format(gps.mouse_x, gps.mouse_y))

-- Scan for non-empty text on screen to find menu items
for y = 0, math.min(gps.dimy - 1, 119) do
    local line = ""
    local has_text = false
    for x = 0, math.min(gps.dimx - 1, 319) do
        local ch = gps.screen[x * gps.dimy * 4 + y * 4]
        if ch and ch > 32 and ch < 127 then
            line = line .. string.char(ch)
            has_text = true
        else
            if has_text and #line > 0 then
                line = line .. " "
            end
        end
    end
    if has_text and #line:gsub("%s+", "") > 2 then
        print(("Row %3d: %s"):format(y, line:gsub("%s+$", "")))
    end
end
