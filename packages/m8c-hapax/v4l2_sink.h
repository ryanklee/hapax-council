/* v4l2_sink.h — opaque interface for the V4L2 output-loopback bridge.
 *
 * Three calls drive the bridge:
 *   v4l2_sink_init()      — open the loopback device, set the format.
 *                           Call once after main_texture exists.
 *   v4l2_sink_publish()   — read main_texture into a buffer + write to
 *                           the loopback. Call after every successful
 *                           SDL_RenderPresent.
 *   v4l2_sink_shutdown()  — close the device.
 *
 * If USE_V4L2_SINK is not defined at build time, all three calls are
 * silent no-ops (compiled into the stock m8c binary harmlessly).
 */

#ifndef HAPAX_M8C_V4L2_SINK_H
#define HAPAX_M8C_V4L2_SINK_H

int v4l2_sink_init(void);
void v4l2_sink_publish(void *renderer, void *texture);
void v4l2_sink_shutdown(void);

#endif /* HAPAX_M8C_V4L2_SINK_H */
