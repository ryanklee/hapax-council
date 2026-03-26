#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform sampler2D tex_accum;
uniform float u_frame_count;
uniform float u_decay_curve;
uniform float u_blend_mode;
void main() {
    vec4 cur = texture2D(tex, v_texcoord);
    vec4 acc = texture2D(tex_accum, v_texcoord);
    float w = 1.0 / u_frame_count;
    float decay = pow(1.0 - w, u_decay_curve);
    vec3 r;
    if (u_blend_mode < 0.5) {
        r = acc.rgb * decay + cur.rgb * w;
    } else if (u_blend_mode < 1.5) {
        r = max(acc.rgb * decay, cur.rgb * w);
    } else {
        r = 1.0 - (1.0 - acc.rgb * decay) * (1.0 - cur.rgb * w);
    }
    gl_FragColor = vec4(clamp(r, 0.0, 1.0), 1.0);
}
