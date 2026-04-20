#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform float u_palette_id;
uniform float u_cycle_rate;
uniform float u_n_bands;
uniform float u_blend;
uniform float u_time;

vec3 synthwavePalette(float t) {
    if (t < 1.0)  return vec3(0.784, 0.196, 1.000);
    if (t < 2.0)  return vec3(1.000, 0.392, 1.000);
    if (t < 3.0)  return vec3(1.000, 0.196, 0.784);
    if (t < 4.0)  return vec3(0.392, 0.196, 1.000);
    if (t < 5.0)  return vec3(0.196, 0.784, 1.000);
    if (t < 6.0)  return vec3(0.196, 1.000, 0.784);
    if (t < 7.0)  return vec3(0.392, 1.000, 0.392);
    if (t < 8.0)  return vec3(0.784, 1.000, 0.196);
    if (t < 9.0)  return vec3(1.000, 0.784, 0.196);
    if (t < 10.0) return vec3(1.000, 0.392, 0.314);
    if (t < 11.0) return vec3(1.000, 0.196, 0.196);
    return             vec3(1.000, 0.196, 0.588);
}

void main() {
    vec4 color = texture2D(tex, v_texcoord);
    float intensity = max(max(color.r, color.g), color.b);

    float n = u_n_bands;
    float time_offset = floor(u_time * u_cycle_rate);

    float col = floor(v_texcoord.x * n);
    float idx = mod(col + time_offset, n);

    vec3 palette_color = synthwavePalette(idx);
    vec3 mapped = palette_color * intensity;
    vec3 final_rgb = mix(color.rgb, mapped, u_blend);

    gl_FragColor = vec4(final_rgb, color.a);
}
