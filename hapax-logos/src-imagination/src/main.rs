mod ipc;
mod window_state;

fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();
    log::info!("hapax-imagination starting (stub)");
}
