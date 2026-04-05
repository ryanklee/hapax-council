#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;
uniform float u_vignette_strength;
uniform float u_sediment_strength;
uniform float u_master_opacity;
uniform float u_anonymize;  // 0=off, 1=full posterize+noise face obscuring

float hash(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 19.19);
    return fract((p3.x + p3.y) * p3.z);
}

void main() {
    vec4 c = texture2D(tex, v_texcoord);

    // Anonymize: destroy facial features while preserving effect character
    if (u_anonymize > 0.5) {
        // Sample from reduced resolution (160p) — eliminates fine facial detail
        vec2 loRes = floor(v_texcoord * 160.0) / 160.0;
        vec4 loC = texture2D(tex, loRes);
        // Blend 70% low-res — face becomes blocky mosaic
        c.rgb = mix(c.rgb, loC.rgb, 0.7);
        // Posterize to 4 levels
        c.rgb = floor(c.rgb * 4.0 + 0.5) / 4.0;
        // Noise grain
        float n = hash(v_texcoord * 200.0 + c.rg * 5.0);
        c.rgb += (n - 0.5) * 0.15;
    }

    // Vignette
    vec2 uv = v_texcoord * 2.0 - 1.0;
    float d = length(uv);
    float vig = smoothstep(0.8, 1.8, d) * u_vignette_strength;
    c.rgb *= 1.0 - vig;

    // Sediment strip
    float sed = smoothstep(0.95, 1.0, v_texcoord.y) * u_sediment_strength;
    c.rgb *= 1.0 - sed;

    gl_FragColor = c;
}
