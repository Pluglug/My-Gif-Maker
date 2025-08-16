from __future__ import annotations
from pathlib import Path
import subprocess
import re
from typing import Optional, Dict, Any

TIME_RE = re.compile(r"time=([0-9:.]+)")


def parse_time_to_seconds(time_str: str) -> float:
    s = time_str.strip()
    if not s:
        return 0.0
    if ":" not in s:
        try:
            return float(s)
        except ValueError:
            return 0.0
    parts = s.split(":")
    parts = [float(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, sec = parts[-3], parts[-2], parts[-1]
    return float(h) * 3600.0 + float(m) * 60.0 + float(sec)


def format_seconds_to_timestamp(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def probe_duration(input_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(input_path),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return float(out.decode("utf-8").strip())
    except Exception:
        return 0.0


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_output_filename(template: str, input_path: Path, settings: Dict[str, Any]) -> str:
    name = input_path.stem
    mapping = {
        "name": name,
        **{k: settings.get(k) for k in ("fps", "width", "colors")},
    }
    try:
        return template.format(**mapping)
    except Exception:
        return f"{name}.gif"


def parse_progress_time_from_line(line: str) -> Optional[float]:
    m = TIME_RE.search(line)
    if not m:
        return None
    return parse_time_to_seconds(m.group(1))


def extract_frame_png(input_path: Path, time_sec: float, output_png: Path, width: int) -> bool:
    # 1フレーム抽出
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        format_seconds_to_timestamp(time_sec),
        "-i",
        str(input_path),
        "-vframes",
        "1",
        "-vf",
        f"scale={width}:-1:flags=lanczos",
        str(output_png),
    ]
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return output_png.exists()
    except Exception:
        return False
