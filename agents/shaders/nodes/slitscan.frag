#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform sampler2D tex_accum;
uniform float u_direction;
uniform float u_speed;
uniform float u_time;
void main() {
    vec2 uv = v_texcoord;
    float offset = u_speed * u_time * 0.01;
    if (u_direction < 0.5) {
        uv.x = fract(uv.x + uv.y * offset);
    } else {
        uv.y = fract(uv.y + uv.x * offset);
    }
    gl_FragColor = texture2D(tex, uv);
}
