import os
import json

# --- APP INFO ---
APP_NAME = "Project Context Copier"
VERSION = "0.1.0-alpha"
AUTHOR = "Parmarth"

# --- DEFAULT CONFIGURATION ---
DEFAULT_CONFIG = {
    "allowed_extensions": ".py, .md, .kt, txt",
    "ignored_folders": ".venv, venv, __pycache__, .git, README, node_modules, stress_tests, pytest_cache, utilities, memory, experiments",
    "ignored_files": ".env, .gitignore, stress_test.py",
    "theme": "dark",
    "recent_folders": [],
    "recent_copies": [],
    "redact_keywords": "",
    "large_file_threshold_kb": 200,
    "separator_template": "Default Markdown",
    "use_regex": False,
    "parse_gitignore": True,
    "git_diff_only": False,
    "sound_enabled": True,
    "geometry": "1000x850",
    "compress_mode": "None"
}

def get_config_path():
    home = os.path.expanduser("~")
    app_dir = os.path.join(home, ".project-context-copier")
    if not os.path.exists(app_dir):
        try:
            os.makedirs(app_dir, exist_ok=True)
        except Exception:
            pass
    return os.path.join(app_dir, "config.json")

CONFIG_FILE = get_config_path()

THEMES = {
    "dark": {
        "bg": "#1e1e2e",
        "card_bg": "#252538",
        "text_primary": "#cdd6f4",
        "text_secondary": "#a6adc8",
        "accent": "#89b4fa",
        "accent_hover": "#b4befe",
        "copy_btn": "#a6e3a1",
        "copy_btn_hover": "#85c1e9",
        "entry_bg": "#313244",
        "entry_border": "#45475a",
        "console_bg": "#11111b",
        "lbl_status_ready": "#a6adc8",
        "lbl_status_success": "#a6e3a1",
        "lbl_status_error": "#f38ba8",
        "scrollbar_thumb": "#313244",
        "tag_code": "#89b4fa",
        "tag_doc": "#a6e3a1",
        "tag_config": "#f9e2af"
    },
    "light": {
        "bg": "#eff1f5",
        "card_bg": "#e6e9ef",
        "text_primary": "#4c4f69",
        "text_secondary": "#6c6f85",
        "accent": "#1e66f5",
        "accent_hover": "#04a5e5",
        "copy_btn": "#40a02b",
        "copy_btn_hover": "#8839ef",
        "entry_bg": "#ccd0da",
        "entry_border": "#bcc0cc",
        "console_bg": "#dce0e8",
        "lbl_status_ready": "#6c6f85",
        "lbl_status_success": "#40a02b",
        "lbl_status_error": "#d20f39",
        "scrollbar_thumb": "#bcc0cc",
        "tag_code": "#1e66f5",
        "tag_doc": "#40a02b",
        "tag_config": "#df8e1d"
    }
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
