#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform sampler2D tex_b;
uniform float u_key_r;
uniform float u_key_g;
uniform float u_key_b;
uniform float u_tolerance;
uniform float u_softness;
void main() {
    vec4 a = texture2D(tex, v_texcoord);
    vec4 b = texture2D(tex_b, v_texcoord);
    vec3 key_color = vec3(u_key_r, u_key_g, u_key_b);
    float dist = distance(b.rgb, key_color);
    float mask = smoothstep(u_tolerance - u_softness, u_tolerance + u_softness, dist);
    gl_FragColor = vec4(mix(a.rgb, b.rgb, mask), 1.0);
}
