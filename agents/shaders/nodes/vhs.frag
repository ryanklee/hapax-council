#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform float u_time;
uniform float u_chroma_shift;
uniform float u_head_switch_y;
uniform float u_noise_band_y;
uniform float u_width;
uniform float u_height;

// Integer-style hash — avoids sin() precision issues entirely
float hash(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 19.19);
    return fract((p3.x + p3.y) * p3.z);
}

void main() {
    vec2 uv = v_texcoord;
    if (u_chroma_shift < 0.01) { gl_FragColor = texture2D(tex, uv); return; }

    float t = mod(u_time, 60.0);
    float px = 1.0 / max(u_width, 1.0);
    float line = floor(uv.y * max(u_height, 1.0));

    // Characteristic 3: Head-switching noise (bottom 5-8%)
    if (uv.y > u_head_switch_y) {
        float ln = hash(vec2(line, t * 7.0));
        uv.x += (ln - 0.5) * 30.0 * px;
    }

    // Characteristic 2: Chroma bleed — R/B offset, green anchored
    float shift = u_chroma_shift * px;
    float r = texture2D(tex, vec2(uv.x + shift, uv.y)).r;
    float g = texture2D(tex, uv).g;
    float b = texture2D(tex, vec2(uv.x - shift, uv.y)).b;
    vec4 color = vec4(r, g, b, 1.0);

    // Characteristic 1: Scan-line banding with luminance variation
    float lineHash = hash(vec2(line * 3.7, t * 0.5 + 42.0));
    color.rgb *= 1.0 + (lineHash - 0.5) * 0.06;
    color.rgb *= mix(0.92, 1.0, mod(line, 2.0));

    // Characteristic 4: Tracking artifact — rolling static band
    float bandY = fract(t * 0.15 + 0.3);
    float bandDist = abs(uv.y - bandY);
    if (bandDist < 0.03) {
        float bandInt = 1.0 - bandDist / 0.03;
        float noise = hash(vec2(uv.x * 173.0, t * 13.0 + line * 0.7));
        color.rgb = mix(color.rgb, vec3(noise * 0.4), bandInt * 0.6);
    }


    // Tape noise
    color.rgb += (hash(vec2(uv.x * 200.0 + 11.0, uv.y * 200.0 + t * 50.0)) - 0.5) * 0.04;

    // Cool blue VHS cast
    float lum = dot(color.rgb, vec3(0.299, 0.587, 0.114));
    color.rgb = mix(color.rgb, vec3(lum * 0.9, lum * 0.95, lum * 1.1), 0.2);

    gl_FragColor = clamp(color, 0.0, 1.0);
}
