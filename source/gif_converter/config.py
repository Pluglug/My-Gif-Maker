from __future__ import annotations
from pathlib import Path
import json
import os
from typing import Dict, Any, List

# プリセット定義
presets: Dict[str, Dict[str, int]] = {
    "高品質": {"fps": 12, "width": 800, "colors": 256},
    "標準": {"fps": 10, "width": 640, "colors": 128},
    "軽量": {"fps": 8, "width": 480, "colors": 64},
}

DEFAULT_TEMPLATE = "{name}_{fps}fps_{width}px_{colors}c.gif"


def get_config_dir() -> Path:
    app_name = "GifConverter"
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / app_name
    # フォールバック: カレント配下
    return Path.cwd() / ".config" / app_name


def get_config_path() -> Path:
    cfg_dir = get_config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.json"


class AppConfig:
    def __init__(self) -> None:
        self.last_output_dir: str = str((Path.cwd() / "output").resolve())
        self.last_preset: str = "標準"
        self.custom_settings: Dict[str, Any] = {
            "fps": presets[self.last_preset]["fps"],
            "width": presets[self.last_preset]["width"],
            "colors": presets[self.last_preset]["colors"],
            "start": 0.0,
            "duration": 0.0,
        }
        self.filename_template: str = DEFAULT_TEMPLATE
        self.recent_files: List[str] = []
        self.recent_limit: int = 15

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_output_dir": self.last_output_dir,
            "last_preset": self.last_preset,
            "custom_settings": self.custom_settings,
            "filename_template": self.filename_template,
            "recent_files": self.recent_files,
            "recent_limit": self.recent_limit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        cfg = cls()
        cfg.last_output_dir = data.get("last_output_dir", cfg.last_output_dir)
        cfg.last_preset = data.get("last_preset", cfg.last_preset)
        cfg.custom_settings.update(data.get("custom_settings", {}))
        cfg.filename_template = data.get("filename_template", cfg.filename_template)
        cfg.recent_files = data.get("recent_files", [])
        cfg.recent_limit = int(data.get("recent_limit", cfg.recent_limit))
        return cfg

    def add_recent_file(self, path: Path) -> None:
        p = str(Path(path).resolve())
        if p in self.recent_files:
            self.recent_files.remove(p)
        self.recent_files.insert(0, p)
        if len(self.recent_files) > self.recent_limit:
            self.recent_files = self.recent_files[: self.recent_limit]


def load_config() -> AppConfig:
    cfg_path = get_config_path()
    if cfg_path.exists():
        try:
            data = json.load(cfg_path.open("r", encoding="utf-8"))
            return AppConfig.from_dict(data)
        except Exception:
            # 壊れている場合は初期化
            pass
    return AppConfig()


def save_config(cfg: AppConfig) -> None:
    cfg_path = get_config_path()
    try:
        cfg_path.write_text(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # 保存失敗時は黙って無視（UI側で通知する場合は呼び出し側で）
        pass
