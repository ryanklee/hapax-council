struct Params {
    u_swatch_count: f32,
    u_strip_height: f32,
    u_strip_opacity: f32,
    u_width: f32,
    u_height: f32,
}

struct FragmentOutput {
    @location(0) fragColor: vec4<f32>,
}

const SAMPLE_ROWS: f32 = 8f;

var<private> fragColor: vec4<f32>;
var<private> v_texcoord_1: vec2<f32>;
@group(1) @binding(0) 
var tex: texture_2d<f32>;
@group(1) @binding(1) 
var tex_sampler: sampler;
@group(2) @binding(0) 
var<uniform> global: Params;

fn sample_column_mean(col_u0_: f32, col_u1_: f32) -> vec3<f32> {
    var col_u0_1: f32;
    var col_u1_1: f32;
    var sum: vec3<f32> = vec3(0f);
    var count: f32 = 0f;
    var r: f32 = 0f;
    var v: f32;
    var c: f32;
    var u: f32;

    col_u0_1 = col_u0_;
    col_u1_1 = col_u1_;
    loop {
        let _e26 = r;
        if !((_e26 < SAMPLE_ROWS)) {
            break;
        }
        {
            let _e32 = r;
            v = ((_e32 + 0.5f) / SAMPLE_ROWS);
            c = 0f;
            loop {
                let _e39 = c;
                if !((_e39 < 4f)) {
                    break;
                }
                {
                    let _e46 = col_u0_1;
                    let _e47 = col_u1_1;
                    let _e48 = c;
                    u = mix(_e46, _e47, ((_e48 + 0.5f) / 4f));
                    let _e55 = sum;
                    let _e56 = u;
                    let _e57 = v;
                    let _e59 = textureSample(tex, tex_sampler, vec2<f32>(_e56, _e57));
                    sum = (_e55 + _e59.xyz);
                    let _e62 = count;
                    count = (_e62 + 1f);
                }
                continuing {
                    let _e43 = c;
                    c = (_e43 + 1f);
                }
            }
        }
        continuing {
            let _e29 = r;
            r = (_e29 + 1f);
        }
    }
    let _e65 = sum;
    let _e66 = count;
    return (_e65 / vec3(_e66));
}

fn main_1() {
    var source: vec4<f32>;
    var y: f32;
    var count_1: f32;
    var idx: f32;
    var u0_: f32;
    var u1_: f32;
    var swatch: vec3<f32>;
    var blended: vec3<f32>;

    let _e15 = v_texcoord_1;
    let _e16 = textureSample(tex, tex_sampler, _e15);
    source = _e16;
    let _e18 = v_texcoord_1;
    y = _e18.y;
    let _e21 = y;
    let _e22 = global.u_strip_height;
    if (_e21 > _e22) {
        {
            let _e24 = source;
            fragColor = _e24;
            return;
        }
    }
    let _e26 = global.u_swatch_count;
    count_1 = max(3f, floor(_e26));
    let _e30 = v_texcoord_1;
    let _e32 = count_1;
    idx = floor((_e30.x * _e32));
    let _e36 = idx;
    let _e38 = count_1;
    idx = clamp(_e36, 0f, (_e38 - 1f));
    let _e42 = idx;
    let _e43 = count_1;
    u0_ = (_e42 / _e43);
    let _e46 = idx;
    let _e49 = count_1;
    u1_ = ((_e46 + 1f) / _e49);
    let _e52 = u0_;
    let _e53 = u1_;
    let _e54 = sample_column_mean(_e52, _e53);
    swatch = _e54;
    let _e56 = source;
    let _e58 = swatch;
    let _e59 = global.u_strip_opacity;
    blended = mix(_e56.xyz, _e58, vec3(_e59));
    let _e63 = blended;
    fragColor = vec4<f32>(_e63.x, _e63.y, _e63.z, 1f);
    return;
}

@fragment 
fn main(@location(0) v_texcoord: vec2<f32>) -> FragmentOutput {
    v_texcoord_1 = v_texcoord;
    main_1();
    let _e23 = fragColor;
    return FragmentOutput(_e23);
}
