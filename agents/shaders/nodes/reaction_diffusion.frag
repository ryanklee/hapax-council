#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform sampler2D tex_accum;
uniform float u_feed_rate;
uniform float u_kill_rate;
uniform float u_diffusion_a;
uniform float u_diffusion_b;
uniform float u_speed;
uniform float u_width;
uniform float u_height;

void main() {
    vec2 texel = vec2(1.0 / u_width, 1.0 / u_height);
    vec4 c = texture2D(tex_accum, v_texcoord);
    float A = c.r;
    float B = c.g;
    
    // 5-point Laplacian stencil
    vec4 l = texture2D(tex_accum, v_texcoord - vec2(texel.x, 0.0));
    vec4 r = texture2D(tex_accum, v_texcoord + vec2(texel.x, 0.0));
    vec4 t = texture2D(tex_accum, v_texcoord - vec2(0.0, texel.y));
    vec4 b = texture2D(tex_accum, v_texcoord + vec2(0.0, texel.y));
    float lap_A = (l.r + r.r + t.r + b.r - 4.0 * A);
    float lap_B = (l.g + r.g + t.g + b.g - 4.0 * B);
    
    // Gray-Scott equations
    float reaction = A * B * B;
    float dA = u_diffusion_a * lap_A - reaction + u_feed_rate * (1.0 - A);
    float dB = u_diffusion_b * lap_B + reaction - (u_kill_rate + u_feed_rate) * B;
    
    A += dA * u_speed * 0.1;
    B += dB * u_speed * 0.1;
    
    // Seed from camera input luminance
    float seed = dot(texture2D(tex, v_texcoord).rgb, vec3(0.299, 0.587, 0.114));
    if (A < 0.01 && seed > 0.8) {
        B = 0.25;
    }
    
    gl_FragColor = vec4(clamp(A, 0.0, 1.0), clamp(B, 0.0, 1.0), 0.0, 1.0);
}
