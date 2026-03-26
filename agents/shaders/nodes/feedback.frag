#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform sampler2D tex_accum;
uniform float u_decay;
uniform float u_zoom;
uniform float u_rotate;
uniform float u_blend_mode;
uniform float u_hue_shift;
void main() {
    vec2 center = vec2(0.5);
    vec2 uv = v_texcoord - center;
    float cs = cos(u_rotate);
    float sn = sin(u_rotate);
    uv = mat2(cs, -sn, sn, cs) * uv;
    uv /= u_zoom;
    uv += center;
    vec4 acc = texture2D(tex_accum, uv);
    acc.rgb *= (1.0 - u_decay);
    if (u_hue_shift > 0.0) {
        float a = u_hue_shift * 3.14159 / 180.0;
        float c = cos(a);
        float s = sin(a);
        mat3 hue = mat3(
            0.213 + 0.787*c - 0.213*s, 0.213 - 0.213*c + 0.143*s, 0.213 - 0.213*c - 0.787*s,
            0.715 - 0.715*c - 0.715*s, 0.715 + 0.285*c + 0.140*s, 0.715 - 0.715*c + 0.715*s,
            0.072 - 0.072*c + 0.928*s, 0.072 - 0.072*c - 0.283*s, 0.072 + 0.928*c + 0.072*s
        );
        acc.rgb = hue * acc.rgb;
    }
    vec4 cur = texture2D(tex, v_texcoord);
    vec3 r;
    if (u_blend_mode < 0.5) r = max(acc.rgb, cur.rgb);
    else if (u_blend_mode < 1.5) r = 1.0 - (1.0 - acc.rgb) * (1.0 - cur.rgb);
    else r = acc.rgb + cur.rgb;
    gl_FragColor = vec4(clamp(r, 0.0, 1.0), 1.0);
}
