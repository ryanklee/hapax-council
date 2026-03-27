//! PoC: Test if wgpu can render to the Tauri window surface
//! with webkit2gtk compositing a transparent webview on top.
//!
//! If this works (red background visible behind UI), Phase 4 uses
//! GPU texture sharing. If not, fall back to shm frame transfer.

use tauri::{AppHandle, Runtime, WebviewWindow};

/// Spawn a simple wgpu clear-to-red loop on the Tauri window.
pub fn spawn_overlay_poc<R: Runtime + 'static>(
    _app_handle: AppHandle<R>,
    window: WebviewWindow<R>,
) {
    tauri::async_runtime::spawn(async move {
        let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
            backends: wgpu::Backends::VULKAN,
            ..Default::default()
        });

        // Critical test: can we create a wgpu surface from a Tauri WebviewWindow?
        let surface = match instance.create_surface(&window) {
            Ok(s) => s,
            Err(e) => {
                log::error!("PoC FAILED: Cannot create wgpu surface from Tauri window: {}", e);
                return;
            }
        };

        let adapter = instance
            .request_adapter(&wgpu::RequestAdapterOptions {
                power_preference: wgpu::PowerPreference::HighPerformance,
                compatible_surface: Some(&surface),
                force_fallback_adapter: false,
            })
            .await
            .expect("No GPU adapter");

        let (device, queue) = adapter
            .request_device(&wgpu::DeviceDescriptor {
                label: Some("poc-overlay"),
                required_features: wgpu::Features::empty(),
                required_limits: wgpu::Limits::default(),
                ..Default::default()
            }, None)
            .await
            .expect("Failed to create device");

        let size = window.inner_size().unwrap_or(tauri::PhysicalSize { width: 1600, height: 1000 });
        let caps = surface.get_capabilities(&adapter);
        let format = caps.formats.iter().find(|f| f.is_srgb()).copied().unwrap_or(caps.formats[0]);

        let config = wgpu::SurfaceConfiguration {
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            format,
            width: size.width.max(1),
            height: size.height.max(1),
            present_mode: wgpu::PresentMode::Fifo,
            alpha_mode: caps.alpha_modes[0],
            view_formats: vec![],
            desired_maximum_frame_latency: 2,
        };
        surface.configure(&device, &config);

        log::info!("PoC: wgpu surface created from Tauri window — rendering red");

        let mut interval = tokio::time::interval(std::time::Duration::from_millis(33));
        loop {
            interval.tick().await;

            let output = match surface.get_current_texture() {
                Ok(t) => t,
                Err(_) => continue,
            };

            let view = output.texture.create_view(&wgpu::TextureViewDescriptor::default());
            let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("poc-frame"),
            });

            // Clear to bright red — if this shows behind the webview, Option B works
            {
                let _pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                    label: Some("poc-clear"),
                    color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                        view: &view,
                        resolve_target: None,
                        ops: wgpu::Operations {
                            load: wgpu::LoadOp::Clear(wgpu::Color {
                                r: 1.0,
                                g: 0.0,
                                b: 0.0,
                                a: 1.0,
                            }),
                            store: wgpu::StoreOp::Store,
                        },
                    })],
                    depth_stencil_attachment: None,
                    timestamp_writes: None,
                    occlusion_query_set: None,
                });
            }

            queue.submit(std::iter::once(encoder.finish()));
            output.present();
        }
    });
}
