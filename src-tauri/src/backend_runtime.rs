use std::path::{Path, PathBuf};

pub fn select_asset_dir(resource_dir: &Path, development_asset_dir: &Path) -> Result<PathBuf, String> {
    let bundled = resource_dir.join("ai");
    if bundled.is_dir() {
        return Ok(bundled);
    }
    if development_asset_dir.is_dir() {
        return Ok(development_asset_dir.to_path_buf());
    }
    Err(format!(
        "Jazrielle AI resources were not found in {} or {}",
        bundled.display(),
        development_asset_dir.display()
    ))
}

pub fn asset_environment(asset_dir: &Path) -> Vec<(String, String)> {
    vec![
        (
            "MODEL_PATH".into(),
            asset_dir.join("qwen3-0.6b-q4_k_m.gguf").display().to_string(),
        ),
        (
            "SYSTEM_PROMPT_PATH".into(),
            asset_dir.join("system-prompt.md").display().to_string(),
        ),
        (
            "ACTION_CONFIG_PATH".into(),
            asset_dir.join("assistant-actions.json").display().to_string(),
        ),
        (
            "CORS_ORIGINS".into(),
            "tauri://localhost,http://tauri.localhost".into(),
        ),
    ]
}

pub fn sidecar_name() -> &'static str {
    "jazrielle-backend"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prefers_bundled_ai_resources() {
        let root = tempfile::tempdir().unwrap();
        let bundled = root.path().join("ai");
        let development = root.path().join("source-ai");
        std::fs::create_dir_all(&bundled).unwrap();
        std::fs::create_dir_all(&development).unwrap();

        assert_eq!(select_asset_dir(root.path(), &development).unwrap(), bundled);
    }

    #[test]
    fn falls_back_to_source_ai_resources() {
        let root = tempfile::tempdir().unwrap();
        let development = root.path().join("source-ai");
        std::fs::create_dir_all(&development).unwrap();

        assert_eq!(select_asset_dir(root.path(), &development).unwrap(), development);
    }

    #[test]
    fn builds_backend_asset_environment() {
        let asset_dir = Path::new("C:/Jazrielle/ai");
        let values = asset_environment(asset_dir);

        assert!(values.iter().any(|(key, value)| key == "MODEL_PATH" && value.ends_with("qwen3-0.6b-q4_k_m.gguf")));
        assert!(values.iter().any(|(key, value)| key == "SYSTEM_PROMPT_PATH" && value.ends_with("system-prompt.md")));
        assert!(values.iter().any(|(key, value)| key == "ACTION_CONFIG_PATH" && value.ends_with("assistant-actions.json")));
        assert!(values.iter().any(|(key, value)| key == "CORS_ORIGINS" && value.contains("tauri://localhost")));
    }

    #[test]
    fn sidecar_name_is_stable() {
        assert_eq!(sidecar_name(), "jazrielle-backend");
    }
}
