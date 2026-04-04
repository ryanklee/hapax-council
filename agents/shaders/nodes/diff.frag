#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform sampler2D tex_accum;
uniform float u_threshold;
uniform float u_color_mode;
void main() {
    vec4 cur = texture2D(tex, v_texcoord);
    vec4 prev = texture2D(tex_accum, v_texcoord);
    vec3 d = abs(cur.rgb - prev.rgb);
    float luma = dot(d, vec3(0.299, 0.587, 0.114));
    vec3 r;
    if (u_color_mode < 0.5) {
        float g = step(u_threshold, luma) * luma;
        r = vec3(g);
    } else if (u_color_mode < 1.5) {
        float b = step(u_threshold, luma);
        r = vec3(b);
    } else {
        r = cur.rgb * step(u_threshold, luma);
    }
    gl_FragColor = vec4(r, 1.0);
}
