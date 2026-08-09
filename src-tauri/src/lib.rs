mod backend_runtime;

use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct BackendProcess(Mutex<Option<CommandChild>>);

fn kill_backend(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<BackendProcess>() {
        if let Ok(mut child) = state.0.lock() {
            if let Some(process) = child.take() {
                let _ = process.kill();
            }
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let source_assets = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../ai");
            let resource_dir = app
                .path()
                .resource_dir()
                .map_err(|error| std::io::Error::other(error.to_string()))?;
            let asset_dir = backend_runtime::select_asset_dir(&resource_dir, &source_assets)
                .map_err(std::io::Error::other)?;

            for (key, value) in backend_runtime::asset_environment(&asset_dir) {
                std::env::set_var(key, value);
            }

            let (mut events, child) = app
                .shell()
                .sidecar(backend_runtime::sidecar_name())
                .map_err(|error| std::io::Error::other(error.to_string()))?
                .spawn()
                .map_err(|error| std::io::Error::other(error.to_string()))?;
            app.manage(BackendProcess(Mutex::new(Some(child))));

            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    eprintln!("Jazrielle backend: {event:?}");
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Jazrielle");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit) {
            kill_backend(app_handle);
        }
    });
}
