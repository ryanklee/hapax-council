#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform sampler2D tex_b;
uniform float u_threshold;
uniform float u_softness;
uniform float u_invert;
void main() {
    vec4 a = texture2D(tex, v_texcoord);
    vec4 b = texture2D(tex_b, v_texcoord);
    float luma = dot(b.rgb, vec3(0.299, 0.587, 0.114));
    float key = smoothstep(u_threshold - u_softness, u_threshold + u_softness, luma);
    if (u_invert > 0.5) key = 1.0 - key;
    gl_FragColor = vec4(mix(a.rgb, b.rgb, key), 1.0);
}
