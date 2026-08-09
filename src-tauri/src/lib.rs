mod backend_runtime;

use std::{
    fs::{create_dir_all, OpenOptions},
    io::Write,
    sync::Mutex,
};

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

struct BackendProcess(Mutex<Option<CommandChild>>);

fn write_runtime_log(app: &tauri::AppHandle, message: &str) {
    eprintln!("{message}");

    let log_dir = app
        .path()
        .app_log_dir()
        .or_else(|_| app.path().app_data_dir());
    let Ok(log_dir) = log_dir else {
        return;
    };

    if create_dir_all(&log_dir).is_err() {
        return;
    }

    let log_path = log_dir.join("jazrielle.log");
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(file, "{message}");
    }
}

fn kill_backend_process(process: CommandChild) {
    let pid = process.pid();

    #[cfg(windows)]
    {
        let tree_killed = std::process::Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .status()
            .map(|status| status.success())
            .unwrap_or(false);

        if !tree_killed {
            let _ = process.kill();
        }
    }

    #[cfg(not(windows))]
    {
        let _ = process.kill();
    }
}

fn kill_backend(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<BackendProcess>() {
        if let Ok(mut child) = state.0.lock() {
            if let Some(process) = child.take() {
                kill_backend_process(process);
            }
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let startup: Result<_, String> = (|| {
                let source_assets =
                    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../ai");
                let resource_dir = app
                    .path()
                    .resource_dir()
                    .map_err(|error| error.to_string())?;
                let asset_dir = backend_runtime::select_asset_dir(&resource_dir, &source_assets)?;

                for (key, value) in backend_runtime::asset_environment(&asset_dir) {
                    std::env::set_var(key, value);
                }

                app.shell()
                    .sidecar(backend_runtime::sidecar_name())
                    .map_err(|error| error.to_string())?
                    .spawn()
                    .map_err(|error| error.to_string())
            })();

            let (mut events, child) = match startup {
                Ok(result) => result,
                Err(error) => {
                    write_runtime_log(
                        &app.handle(),
                        &format!("Jazrielle backend startup failed: {error}"),
                    );
                    return Err(std::io::Error::other(error).into());
                }
            };
            app.manage(BackendProcess(Mutex::new(Some(child))));

            let log_app = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    match event {
                        CommandEvent::Error(error) => write_runtime_log(
                            &log_app,
                            &format!("Jazrielle backend process error: {error}"),
                        ),
                        CommandEvent::Terminated(payload) => write_runtime_log(
                            &log_app,
                            &format!("Jazrielle backend terminated: {payload:?}"),
                        ),
                        event => eprintln!("Jazrielle backend: {event:?}"),
                    }
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .unwrap_or_else(|error| panic!("error while building Jazrielle: {error}"));

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit) {
            kill_backend(app_handle);
        }
    });
}
