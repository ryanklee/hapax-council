// Content layer — Bachelard phenomenology surface.
// Reads procedural field as input, modulates with 5 effects:
// 1. Materialization from substrate (noise-gated crystallization)
// 2. Corner incubation (low salience → peripheral)
// 3. Off-screen entry / immensity (slide in from beyond viewport)
// 4. Material quality (water/fire/earth/air/void UV + color modulation)
// 5. Dwelling trace boost (luminance boost during fadeout for feedback persistence)

struct FragmentOutput {
    @location(0) fragColor: vec4<f32>,
}

var<private> fragColor: vec4<f32>;
var<private> v_texcoord_1: vec2<f32>;

@group(1) @binding(0)
var tex: texture_2d<f32>;
@group(1) @binding(1)
var tex_sampler: sampler;

// --- Noise ---

fn hash21(p: vec2<f32>) -> f32 {
    return fract(sin(dot(p, vec2<f32>(127.1, 311.7))) * 43758.547);
}

// --- Effects ---

fn materialization(uv: vec2<f32>, salience: f32, time: f32) -> f32 {
    let noise = hash21(uv * 30.0 + time * 0.05);
    return smoothstep(1.0 - salience, 1.0 - salience + 0.3, noise);
}

fn corner_incubation(uv: vec2<f32>, intensity: f32) -> vec2<f32> {
    let center_pull = intensity;
    let corner_offset = (1.0 - center_pull) * 0.3;
    return uv + (uv - 0.5) * corner_offset;
}

fn immensity_entry(uv: vec2<f32>, salience: f32, time: f32) -> vec2<f32> {
    let entry_progress = smoothstep(0.0, 0.5, salience);
    let entry_offset = (1.0 - entry_progress) * 0.4;
    let entry_dir = vec2<f32>(sin(time * 0.1 + 2.1), cos(time * 0.1 + 1.7));
    return uv + entry_dir * entry_offset;
}

fn material_uv(uv: vec2<f32>, material_id: u32, time: f32) -> vec2<f32> {
    var muv = uv;
    switch material_id {
        case 0u: {
            // water: dissolve at edges, flow downward
            muv.y += sin(uv.x * 6.28 + time * 0.3) * 0.02;
            muv.y += time * 0.005;
        }
        case 1u: {
            // fire: burn outward from center
            let d = length(uv - 0.5);
            muv += normalize(uv - 0.5 + 0.001) * d * 0.05 * sin(time * 2.0);
        }
        case 2u: {
            // earth: minimal distortion
        }
        case 3u: {
            // air: drift upward, dispersal
            muv.y -= time * 0.008;
            muv.x += sin(uv.y * 4.0 + time * 0.5) * 0.015;
        }
        case 4u: {
            // void: inward pull
            muv = mix(muv, vec2<f32>(0.5), 0.05);
        }
        default: {}
    }
    return muv;
}

fn material_color(color: vec3<f32>, material_id: u32) -> vec3<f32> {
    switch material_id {
        case 0u: {
            return mix(color, color * vec3<f32>(0.85, 0.92, 1.1), 0.3);
        }
        case 1u: {
            return mix(color, color * vec3<f32>(1.15, 1.0, 0.85), 0.3);
        }
        case 2u: {
            let lum = dot(color, vec3<f32>(0.299, 0.587, 0.114));
            return mix(color, vec3<f32>(lum), 0.15);
        }
        case 3u: {
            return mix(color, vec3<f32>(1.0), 0.1);
        }
        case 4u: {
            return color * 0.7;
        }
        default: {
            return color;
        }
    }
}

fn dwelling_trace_boost(salience: f32) -> f32 {
    return 1.0 + (1.0 - smoothstep(0.3, 0.7, salience)) * 0.15;
}

// --- Main ---

fn main_1() {
    let uv_raw = v_texcoord_1;
    let time = uniforms.time;
    let salience = uniforms.slot_opacities[0];
    let intensity = uniforms.intensity;
    let material_id = u32(round(uniforms.custom[0][0]));

    var uv = corner_incubation(uv_raw, intensity);
    uv = immensity_entry(uv, salience, time);
    uv = material_uv(uv, material_id, time);

    var color = textureSample(tex, tex_sampler, uv);

    let mat_factor = materialization(uv_raw, salience, time);
    color = vec4<f32>(color.rgb * mat_factor, color.a);

    color = vec4<f32>(material_color(color.rgb, material_id), color.a);

    let trace_boost = dwelling_trace_boost(salience);
    color = vec4<f32>(color.rgb * trace_boost, color.a);

    fragColor = color;
    return;
}

@fragment
fn main(@location(0) v_texcoord: vec2<f32>) -> FragmentOutput {
    v_texcoord_1 = v_texcoord;
    main_1();
    let _e11 = fragColor;
    return FragmentOutput(_e11);
}
