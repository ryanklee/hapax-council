struct Params {
    u_palette_id: f32,
    u_cycle_rate: f32,
    u_n_bands: f32,
    u_blend: f32,
    u_time: f32,
}

struct FragmentOutput {
    @location(0) fragColor: vec4<f32>,
}

var<private> fragColor: vec4<f32>;
var<private> v_texcoord_1: vec2<f32>;
@group(1) @binding(0) 
var tex: texture_2d<f32>;
@group(1) @binding(1) 
var tex_sampler: sampler;
@group(2) @binding(0) 
var<uniform> global: Params;

fn synthwavePalette(t: f32) -> vec3<f32> {
    var t_1: f32;

    t_1 = t;
    let _e16 = t_1;
    if (_e16 < 1f) {
        return vec3<f32>(0.784f, 0.196f, 1f);
    }
    let _e23 = t_1;
    if (_e23 < 2f) {
        return vec3<f32>(1f, 0.392f, 1f);
    }
    let _e30 = t_1;
    if (_e30 < 3f) {
        return vec3<f32>(1f, 0.196f, 0.784f);
    }
    let _e37 = t_1;
    if (_e37 < 4f) {
        return vec3<f32>(0.392f, 0.196f, 1f);
    }
    let _e44 = t_1;
    if (_e44 < 5f) {
        return vec3<f32>(0.196f, 0.784f, 1f);
    }
    let _e51 = t_1;
    if (_e51 < 6f) {
        return vec3<f32>(0.196f, 1f, 0.784f);
    }
    let _e58 = t_1;
    if (_e58 < 7f) {
        return vec3<f32>(0.392f, 1f, 0.392f);
    }
    let _e65 = t_1;
    if (_e65 < 8f) {
        return vec3<f32>(0.784f, 1f, 0.196f);
    }
    let _e72 = t_1;
    if (_e72 < 9f) {
        return vec3<f32>(1f, 0.784f, 0.196f);
    }
    let _e79 = t_1;
    if (_e79 < 10f) {
        return vec3<f32>(1f, 0.392f, 0.314f);
    }
    let _e86 = t_1;
    if (_e86 < 11f) {
        return vec3<f32>(1f, 0.196f, 0.196f);
    }
    return vec3<f32>(1f, 0.196f, 0.588f);
}

fn main_1() {
    var color: vec4<f32>;
    var intensity: f32;
    var n: f32;
    var time_offset: f32;
    var col: f32;
    var idx: f32;
    var palette_color: vec3<f32>;
    var mapped: vec3<f32>;
    var final_rgb: vec3<f32>;

    let _e14 = v_texcoord_1;
    let _e15 = textureSample(tex, tex_sampler, _e14);
    color = _e15;
    let _e17 = color;
    let _e19 = color;
    let _e22 = color;
    intensity = max(max(_e17.x, _e19.y), _e22.z);
    let _e26 = global.u_n_bands;
    n = _e26;
    let _e28 = global.u_time;
    let _e29 = global.u_cycle_rate;
    time_offset = floor((_e28 * _e29));
    let _e33 = v_texcoord_1;
    let _e35 = n;
    col = floor((_e33.x * _e35));
    let _e39 = col;
    let _e40 = time_offset;
    let _e41 = (_e39 + _e40);
    let _e42 = n;
    idx = (_e41 - (floor((_e41 / _e42)) * _e42));
    let _e48 = idx;
    let _e49 = synthwavePalette(_e48);
    palette_color = _e49;
    let _e51 = palette_color;
    let _e52 = intensity;
    mapped = (_e51 * _e52);
    let _e55 = color;
    let _e57 = mapped;
    let _e58 = global.u_blend;
    final_rgb = mix(_e55.xyz, _e57, vec3(_e58));
    let _e62 = final_rgb;
    let _e63 = color;
    fragColor = vec4<f32>(_e62.x, _e62.y, _e62.z, _e63.w);
    return;
}

@fragment 
fn main(@location(0) v_texcoord: vec2<f32>) -> FragmentOutput {
    v_texcoord_1 = v_texcoord;
    main_1();
    let _e21 = fragColor;
    return FragmentOutput(_e21);
}
