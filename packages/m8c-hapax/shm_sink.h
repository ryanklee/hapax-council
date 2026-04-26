/* shm_sink.h — opaque interface for the SHM RGBA bridge.
 *
 * Three calls drive the bridge:
 *   shm_sink_init()      — open the SHM file, ensure the directory.
 *                          Call once after main_texture exists.
 *   shm_sink_publish()   — read main_texture into a buffer + write to
 *                          the SHM file + atomically update sidecar.
 *                          Call after every successful SDL_RenderPresent.
 *   shm_sink_shutdown()  — close the file.
 *
 * If USE_SHM_SINK is not defined at build time, all three calls are
 * silent no-ops (compiled into the stock m8c binary harmlessly).
 *
 * Output format matches the studio compositor's external_rgba source
 * pattern (same shape as Reverie):
 *   /dev/shm/hapax-sources/m8-display.rgba       — raw 320x240 BGRA bytes
 *   /dev/shm/hapax-sources/m8-display.rgba.json  — sidecar metadata
 */

#ifndef HAPAX_M8C_SHM_SINK_H
#define HAPAX_M8C_SHM_SINK_H

int shm_sink_init(void);
void shm_sink_publish(void *renderer, void *texture);
void shm_sink_shutdown(void);

#endif /* HAPAX_M8C_SHM_SINK_H */
