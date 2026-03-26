#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform float u_zoom_speed;
uniform float u_spiral;
uniform float u_center_x;
uniform float u_center_y;
uniform float u_branches;
uniform float u_time;
void main() {
    vec2 center = vec2(u_center_x, u_center_y);
    vec2 uv = v_texcoord - center;
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    float logr = log(max(r, 0.0001));
    float n = u_branches;
    float p = u_spiral;
    float t = u_time * u_zoom_speed;
    float angle = theta + p * logr - t;
    float scale = exp(mod(logr - t * 0.5, log(2.0)) - log(2.0));
    angle = mod(angle, 6.28318 / n);
    vec2 nuv = vec2(cos(angle), sin(angle)) * scale + center;
    nuv = fract(nuv);
    gl_FragColor = texture2D(tex, nuv);
}
