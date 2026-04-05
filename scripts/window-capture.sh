#!/bin/bash
# Capture a Hyprland window to v4l2 loopback for compositor input
# Usage: window-capture.sh [window-class-or-title]
# Default: captures the focused window

DEVICE="/dev/video10"
FPS=24
RES="1920x1080"

# Get window geometry
if [ -n "$1" ]; then
    # Find window by class/title
    GEOM=$(hyprctl clients -j | jq -r ".[] | select(.class == \"$1\" or .title == \"$1\") | \"\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])\"" | head -1)
else
    # Use active window
    GEOM=$(hyprctl activewindow -j | jq -r '"\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])"')
fi

if [ -z "$GEOM" ]; then
    echo "No window found"
    exit 1
fi

echo "Capturing: $GEOM → $DEVICE at ${FPS}fps"

# Use wf-recorder to capture the window region → v4l2 loopback
exec wf-recorder \
    --geometry "$GEOM" \
    --framerate "$FPS" \
    --codec rawvideo \
    --pixel-format yuv420p \
    --file "$DEVICE" \
    --no-dmabuf \
    -x yuv420p
