/* Ambient fBM flow field — generative background for visual communication layer.
 *
 * Perlin noise fractional Brownian motion. Parameters driven by system state:
 *   u_speed      — animation rate (0.0-1.0)
 *   u_turbulence — noise octave complexity (0.0-1.0)
 *   u_warmth     — color temperature (0.0=cool teal, 1.0=warm red)
 *   u_brightness — overall output brightness (0.0-1.0)
 */

#version 300 es
precision mediump float;

uniform float u_time;
uniform float u_speed;
uniform float u_turbulence;
uniform float u_warmth;
uniform float u_brightness;
uniform vec2 u_resolution;

out vec4 fragColor;

// Hash function for pseudo-random gradient
vec2 hash(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)),
             dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

// 2D Perlin noise
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);  // smoothstep

    return mix(mix(dot(hash(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0)),
                   dot(hash(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
               mix(dot(hash(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
                   dot(hash(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x), u.y);
}

// Fractional Brownian motion
float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    int octaves = 3 + int(u_turbulence * 4.0);  // 3-7 octaves based on turbulence

    for (int i = 0; i < 7; i++) {
        if (i >= octaves) break;
        value += amplitude * noise(p * frequency);
        p += vec2(5.2, 1.3);  // domain warp
        frequency *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float t = u_time * u_speed * 0.1;

    // Flow field: distort UV with fbm
    vec2 q = vec2(fbm(uv * 3.0 + t), fbm(uv * 3.0 + vec2(1.7, 9.2) + t));
    vec2 r = vec2(fbm(uv * 3.0 + 4.0 * q + vec2(1.7, 9.2) + t * 0.5),
                  fbm(uv * 3.0 + 4.0 * q + vec2(8.3, 2.8) + t * 0.3));

    float f = fbm(uv * 3.0 + 4.0 * r);

    // Color mapping: cool teal → warm red via u_warmth
    vec3 cool = vec3(0.15, 0.35, 0.45);   // deep teal
    vec3 warm = vec3(0.45, 0.15, 0.12);   // muted red

    vec3 base = mix(cool, warm, u_warmth);
    vec3 highlight = mix(vec3(0.2, 0.5, 0.6), vec3(0.6, 0.3, 0.15), u_warmth);

    vec3 color = mix(base, highlight, clamp(f * 0.5 + 0.5, 0.0, 1.0));
    color *= u_brightness;

    // Subtle vignette
    float vignette = 1.0 - 0.3 * length(uv - 0.5);
    color *= vignette;

    fragColor = vec4(color, 1.0);
}
