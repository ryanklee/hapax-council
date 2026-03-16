#!/bin/bash
# studio-fx-output.sh — Feed GPU-effected snapshots to /dev/video50
# Runs as a separate process to avoid preroll deadlocks in the compositor.

SNAPSHOT="/dev/shm/hapax-compositor/fx-snapshot.jpg"
DEVICE="/dev/video50"

[ -e "$DEVICE" ] || { echo "Device $DEVICE not found"; exit 1; }

# Wait for first snapshot
while [ ! -f "$SNAPSHOT" ]; do sleep 1; done

echo "Starting FX output to $DEVICE"

# Use ffmpeg to continuously read the snapshot and write to v4l2loopback
# -re: read at native rate
# -loop 1: loop the single image
# -f image2: treat input as image
# -stream_loop -1: infinite loop
exec ffmpeg -y -re \
  -f image2 -loop 1 -framerate 15 -i "$SNAPSHOT" \
  -f v4l2 -pix_fmt yuyv422 -video_size 1920x1080 \
  "$DEVICE"
