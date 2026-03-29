#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform float u_vignette_strength;
uniform float u_sediment_strength;
void main() {
    vec4 c = texture2D(tex, v_texcoord);
    // Vignette
    vec2 uv = v_texcoord * 2.0 - 1.0;
    float d = length(uv);
    float vig = smoothstep(0.8, 1.8, d) * u_vignette_strength;
    c.rgb *= 1.0 - vig;
    // Sediment strip (subtle dark bar at bottom)
    float sed = smoothstep(0.95, 1.0, v_texcoord.y) * u_sediment_strength;
    c.rgb *= 1.0 - sed;
    gl_FragColor = c;
}
