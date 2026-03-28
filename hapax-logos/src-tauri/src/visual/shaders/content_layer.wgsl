// Content layer — placeholder passthrough
// Samples the composite texture and returns it unchanged.

struct ContentUniforms {
    slot_opacities: vec4<f32>,
    intensity: f32,
    tension: f32,
    depth: f32,
    coherence: f32,
    spectral_color: f32,
    temporal_distortion: f32,
    degradation: f32,
    pitch_displacement: f32,
    formant_character: f32,
    time: f32,
    _pad0: f32,
    _pad1: f32,
};

@group(0) @binding(0) var<uniform> u: ContentUniforms;
@group(0) @binding(1) var composite_tex: texture_2d<f32>;
@group(0) @binding(2) var slot0_tex: texture_2d<f32>;
@group(0) @binding(3) var slot1_tex: texture_2d<f32>;
@group(0) @binding(4) var slot2_tex: texture_2d<f32>;
@group(0) @binding(5) var slot3_tex: texture_2d<f32>;
@group(0) @binding(6) var samp: sampler;

struct VertexOutput {
    @builtin(position) position: vec4<f32>,
    @location(0) uv: vec2<f32>,
};

@vertex
fn vs_main(@builtin(vertex_index) vi: u32) -> VertexOutput {
    // Full-screen triangle
    let x = f32(i32(vi & 1u)) * 4.0 - 1.0;
    let y = f32(i32(vi >> 1u)) * 4.0 - 1.0;
    var out: VertexOutput;
    out.position = vec4<f32>(x, y, 0.0, 1.0);
    out.uv = vec2<f32>((x + 1.0) * 0.5, 1.0 - (y + 1.0) * 0.5);
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    return textureSample(composite_tex, samp, in.uv);
}
