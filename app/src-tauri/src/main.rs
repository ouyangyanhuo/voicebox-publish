#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::env;
use tauri::{WebviewUrl, WebviewWindowBuilder};

/// IPC command: return the install directory to the frontend.
#[tauri::command]
fn get_install_dir() -> String {
    env::var("AUDIOSCRIBE_INSTALL_DIR").unwrap_or_default()
}

fn main() {
    // Determine install directory
    let install_dir = if cfg!(debug_assertions) {
        env::var("AUDIOSCRIBE_INSTALL_DIR")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|_| env::current_dir().expect("Failed to get current directory"))
    } else {
        env::current_exe()
            .expect("Failed to get exe path")
            .parent()
            .expect("Failed to get exe parent directory")
            .to_path_buf()
    };

    // Redirect Tauri's internal data (window state, WebView2, plugins) to install dir
    let tauri_data = install_dir.join("data").join("tauri");
    env::set_var("TAURI_APPDATA", &tauri_data);

    // Ensure the sidecar backend knows the install directory
    env::set_var("AUDIOSCRIBE_INSTALL_DIR", &install_dir);

    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![get_install_dir])
        .setup(move |app| {
            // WebView2 data directory — this is what stores EBWebView under AppData\Local
            let webview_data = install_dir.join("data").join("webview");

            let url = if cfg!(debug_assertions) {
                WebviewUrl::External(
                    "http://localhost:1420".parse().expect("invalid dev URL"),
                )
            } else {
                WebviewUrl::App("index.html".into())
            };

            WebviewWindowBuilder::new(app, "main", url)
                .title("AudioScribe")
                .inner_size(1280.0, 820.0)
                .min_inner_size(960.0, 640.0)
                .data_directory(webview_data)
                .build()?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running AudioScribe");
}
