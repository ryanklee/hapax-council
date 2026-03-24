local gui = require("gui")
local t = dfhack.gui.getViewscreenByType(df.viewscreen_titlest, 0)
if not t then print("NOT ON TITLE") return end

-- In DF 53.x premium, the title menu might use mouse/keyboard differently.
-- Let's try: option_key_pressed field, or direct key constants.

-- Check if there are widgets
print("widgets: " .. tostring(t.widgets))
local children = dfhack.gui.getWidgetChildren(t.widgets)
if children then
    print("Widget children: " .. #children)
    for i, c in ipairs(children) do
        print(("  [%d] %s"):format(i, tostring(c)))
    end
end

-- Try STRING_A048 which might be 'N' for New World
-- Or try the mode field — maybe setting mode triggers the transition
print("Current mode: " .. t.mode)

-- Try: maybe we need to use CUSTOM_N or similar
print("Trying various keys...")
gui.simulateInput(t, df.interface_key._MOUSE_L)
