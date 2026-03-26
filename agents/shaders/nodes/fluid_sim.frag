#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform sampler2D tex_accum;
uniform float u_viscosity;
uniform float u_vorticity;
uniform float u_dissipation;
uniform float u_speed;
uniform float u_time;
uniform float u_width;
uniform float u_height;

void main() {
    vec2 texel = vec2(1.0 / u_width, 1.0 / u_height);
    vec4 prev = texture2D(tex_accum, v_texcoord);
    vec2 vel = prev.rg * 2.0 - 1.0;
    
    // Advect: sample from where fluid came from
    vec2 advected_uv = v_texcoord - vel * texel * u_speed;
    vec4 advected = texture2D(tex_accum, advected_uv);
    
    // Diffusion: average with neighbors
    vec4 l = texture2D(tex_accum, v_texcoord - vec2(texel.x, 0.0));
    vec4 r = texture2D(tex_accum, v_texcoord + vec2(texel.x, 0.0));
    vec4 t = texture2D(tex_accum, v_texcoord - vec2(0.0, texel.y));
    vec4 b = texture2D(tex_accum, v_texcoord + vec2(0.0, texel.y));
    vec4 diffused = mix(advected, (l + r + t + b) * 0.25, u_viscosity * 10.0);
    
    // Vorticity confinement
    float curl = (r.g - l.g) - (t.r - b.r);
    vec2 vort = vec2(abs(texture2D(tex_accum, v_texcoord + vec2(0.0, texel.y)).r) -
                     abs(texture2D(tex_accum, v_texcoord - vec2(0.0, texel.y)).r),
                     abs(texture2D(tex_accum, v_texcoord + vec2(texel.x, 0.0)).g) -
                     abs(texture2D(tex_accum, v_texcoord - vec2(texel.x, 0.0)).g));
    float vort_len = length(vort) + 0.0001;
    vort = normalize(vort) * curl * u_vorticity * texel.x;
    
    // Inject from input
    float inject = dot(texture2D(tex, v_texcoord).rgb, vec3(0.299, 0.587, 0.114));
    
    // Combine
    vec2 new_vel = (diffused.rg * 2.0 - 1.0 + vort) * u_dissipation;
    float density = diffused.b * u_dissipation + inject * 0.1;
    
    gl_FragColor = vec4(new_vel * 0.5 + 0.5, density, 1.0);
}
