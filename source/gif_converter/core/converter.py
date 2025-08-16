from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import subprocess
import tempfile

from PyQt5.QtCore import QObject, pyqtSignal

from .utils import (
    probe_duration,
    parse_progress_time_from_line,
    format_seconds_to_timestamp,
)


@dataclass
class ConversionTask:
    input_path: Path
    output_dir: Path
    fps: int
    width: int
    colors: int
    start: float  # 秒
    duration: float  # 秒。0なら最後まで
    output_path: Optional[Path] = None


class ConverterWorker(QObject):
    progress = pyqtSignal(str, float, str)  # file, percent[0-100], message
    finished = pyqtSignal(str, bool, str, str)  # file, success, output_path, error
    log = pyqtSignal(str)

    def convert(self, task: ConversionTask) -> None:
        inp = task.input_path
        if not inp.exists():
            self.finished.emit(str(inp), False, "", "入力ファイルが見つかりません")
            return
        total_duration = (
            task.duration if task.duration > 0 else probe_duration(inp) - task.start
        )
        total_duration = max(total_duration, 0.00001)

        with tempfile.TemporaryDirectory(prefix="gifconv_") as td:
            tmpdir = Path(td)
            palette = tmpdir / "palette.png"
            # 1パス目: パレット生成
            vf_palette = [
                f"fps={task.fps}",
                f"scale={task.width}:-1:flags=lanczos",
                f"palettegen=max_colors={task.colors}:stats_mode=full",
            ]
            cmd1 = [
                "ffmpeg",
                "-y",
            ]
            if task.start > 0:
                cmd1 += ["-ss", format_seconds_to_timestamp(task.start)]
            cmd1 += [
                "-i",
                str(inp),
            ]
            if task.duration > 0:
                cmd1 += ["-t", format_seconds_to_timestamp(task.duration)]
            cmd1 += [
                "-vf",
                ",".join(vf_palette),
                str(palette),
            ]

            # 2パス目: パレット適用
            vf_use = [
                f"fps={task.fps}",
                f"scale={task.width}:-1:flags=lanczos",
                f"paletteuse=dither=sierra2_4a",
            ]
            out_path = task.output_path or (task.output_dir / (inp.stem + ".gif"))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            cmd2 = [
                "ffmpeg",
                "-y",
            ]
            if task.start > 0:
                cmd2 += ["-ss", format_seconds_to_timestamp(task.start)]
            cmd2 += [
                "-i",
                str(inp),
                "-i",
                str(palette),
            ]
            if task.duration > 0:
                cmd2 += ["-t", format_seconds_to_timestamp(task.duration)]
            cmd2 += [
                "-lavfi",
                ",".join(vf_use),
                "-loop",
                "0",
                str(out_path),
            ]

            # 実行と進捗
            try:
                self.log.emit("パレット生成を開始しました")
                self._run_with_progress(cmd1, total_duration)
                if not palette.exists():
                    raise RuntimeError("パレット生成に失敗しました")
                self.log.emit("GIF生成を開始しました")
                self._run_with_progress(cmd2, total_duration)
                self.finished.emit(str(inp), True, str(out_path), "")
            except Exception as e:
                self.finished.emit(str(inp), False, "", str(e))

    def _run_with_progress(self, cmd: list[str], total_duration: float) -> None:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        # ffmpegはstderrに進捗を出す
        assert proc.stderr is not None
        for line in proc.stderr:
            t = parse_progress_time_from_line(line)
            if t is not None:
                percent = max(0.0, min(100.0, (t / total_duration) * 100.0))
                self.progress.emit(cmd[-1], percent, line.strip())
        proc.wait()
        if proc.returncode != 0:
            # 失敗時はエラーを読み取る
            err = proc.stderr.read() if proc.stderr else "ffmpeg failed"
            raise RuntimeError(f"ffmpegエラー: {err[:400]}...")
