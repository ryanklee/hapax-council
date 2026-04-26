/* v4l2_sink.c — write SDL_RenderReadPixels output to a v4l2-loopback device.
 *
 * Carry-fork patch for laamaa/m8c. Hooks into render.c so every frame
 * the M8 LCD draws (320x240 ARGB) is also published as a V4L2 output
 * device frame, ready for the studio compositor's pyudev camera FSM
 * to consume as another camera Source.
 *
 * Build with -DUSE_V4L2_SINK; otherwise this file no-ops via the
 * function-stubs guard below.
 *
 * Constitutional binders:
 *   - feedback_l12_equals_livestream_invariant (vacuous; no L-12 contact)
 *   - never drop operator speech (no audio path)
 *   - anti-anthropomorphization (instrument LCD, not personified)
 *
 * Why a separate file (not inline in render.c): keeps the patch surface
 * small enough to rebase trivially when upstream m8c moves.
 */

#include "v4l2_sink.h"

#ifdef USE_V4L2_SINK

#include <SDL3/SDL.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

/* M8 LCD native resolution (pre-window-scaling). main_texture in
 * render.c is created at this exact size. */
#define V4L2_SINK_WIDTH 320
#define V4L2_SINK_HEIGHT 240
#define V4L2_SINK_BYTES_PER_PIXEL 4 /* RGBA32 */
#define V4L2_SINK_FRAME_BYTES (V4L2_SINK_WIDTH * V4L2_SINK_HEIGHT * V4L2_SINK_BYTES_PER_PIXEL)
#define V4L2_SINK_DEFAULT_DEVICE "/dev/video15"

static int sink_fd = -1;
static uint8_t sink_buffer[V4L2_SINK_FRAME_BYTES];

static const char *resolve_device_path(void) {
  const char *override = getenv("M8C_V4L2_SINK_PATH");
  return (override && override[0] != '\0') ? override : V4L2_SINK_DEFAULT_DEVICE;
}

int v4l2_sink_init(void) {
  if (sink_fd >= 0) {
    return 1; /* already open */
  }

  const char *path = resolve_device_path();
  sink_fd = open(path, O_WRONLY | O_NONBLOCK);
  if (sink_fd < 0) {
    SDL_LogWarn(SDL_LOG_CATEGORY_APPLICATION,
                "v4l2_sink: open(%s) failed; v4l2-loopback module loaded?",
                path);
    return 0;
  }

  struct v4l2_format fmt;
  memset(&fmt, 0, sizeof(fmt));
  fmt.type = V4L2_BUF_TYPE_VIDEO_OUTPUT;
  fmt.fmt.pix.width = V4L2_SINK_WIDTH;
  fmt.fmt.pix.height = V4L2_SINK_HEIGHT;
  fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_ABGR32; /* matches SDL_PIXELFORMAT_ARGB8888 byte order on LE */
  fmt.fmt.pix.field = V4L2_FIELD_NONE;
  fmt.fmt.pix.bytesperline = V4L2_SINK_WIDTH * V4L2_SINK_BYTES_PER_PIXEL;
  fmt.fmt.pix.sizeimage = V4L2_SINK_FRAME_BYTES;
  fmt.fmt.pix.colorspace = V4L2_COLORSPACE_SRGB;

  if (ioctl(sink_fd, VIDIOC_S_FMT, &fmt) < 0) {
    SDL_LogWarn(SDL_LOG_CATEGORY_APPLICATION,
                "v4l2_sink: VIDIOC_S_FMT failed; falling back to publishless");
    close(sink_fd);
    sink_fd = -1;
    return 0;
  }

  SDL_Log("v4l2_sink: publishing 320x240 ARGB8888 frames to %s", path);
  return 1;
}

void v4l2_sink_publish(void *renderer, void *texture) {
  if (sink_fd < 0) {
    return; /* not initialised, or init failed; render hot path is no-op */
  }

  SDL_Renderer *rend = (SDL_Renderer *)renderer;
  SDL_Texture *tex = (SDL_Texture *)texture;

  SDL_Texture *previous_target = SDL_GetRenderTarget(rend);
  if (!SDL_SetRenderTarget(rend, tex)) {
    return; /* couldn't bind target; skip this frame */
  }

  SDL_Rect rect = {.x = 0, .y = 0, .w = V4L2_SINK_WIDTH, .h = V4L2_SINK_HEIGHT};
  SDL_Surface *surface = SDL_RenderReadPixels(rend, &rect);
  /* restore caller's render target before any early return */
  SDL_SetRenderTarget(rend, previous_target);
  if (!surface) {
    return;
  }

  if (surface->pitch == V4L2_SINK_WIDTH * V4L2_SINK_BYTES_PER_PIXEL) {
    memcpy(sink_buffer, surface->pixels, V4L2_SINK_FRAME_BYTES);
  } else {
    /* Pitch-mismatch path: copy row-by-row. */
    const uint8_t *src = (const uint8_t *)surface->pixels;
    for (int y = 0; y < V4L2_SINK_HEIGHT; y++) {
      memcpy(&sink_buffer[y * V4L2_SINK_WIDTH * V4L2_SINK_BYTES_PER_PIXEL],
             &src[y * surface->pitch],
             V4L2_SINK_WIDTH * V4L2_SINK_BYTES_PER_PIXEL);
    }
  }
  SDL_DestroySurface(surface);

  ssize_t written = write(sink_fd, sink_buffer, V4L2_SINK_FRAME_BYTES);
  if (written < 0 && errno != EAGAIN) {
    SDL_LogWarn(SDL_LOG_CATEGORY_APPLICATION,
                "v4l2_sink: write failed (errno=%d); leaving sink open for retry",
                errno);
  }
}

void v4l2_sink_shutdown(void) {
  if (sink_fd >= 0) {
    close(sink_fd);
    sink_fd = -1;
  }
}

#else /* !USE_V4L2_SINK */

int v4l2_sink_init(void) { return 0; }
void v4l2_sink_publish(void *renderer, void *texture) {
  (void)renderer;
  (void)texture;
}
void v4l2_sink_shutdown(void) {}

#endif /* USE_V4L2_SINK */
