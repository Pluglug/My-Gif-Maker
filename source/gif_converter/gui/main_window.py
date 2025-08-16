from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import tempfile

from PyQt5.QtCore import Qt, QThread, pyqtSlot
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QFileDialog,
    QLabel,
    QProgressBar,
    QPlainTextEdit,
    QSplitter,
    QMessageBox,
    QLineEdit,
    QDoubleSpinBox,
    QMenu,
    QAction,
)

from ..config import AppConfig, load_config, save_config, DEFAULT_TEMPLATE
from ..core.converter import ConverterWorker, ConversionTask
from ..core.utils import (
    ensure_output_dir,
    extract_frame_png,
    build_output_filename,
    probe_duration,
)
from .settings import SettingsPanel
from .preview import PreviewWidget


class FileListWidget(QListWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(self.ExtendedSelection)

    def dragEnterEvent(self, e):  # type: ignore[override]
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):  # type: ignore[override]
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):  # type: ignore[override]
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi"} and p.exists():
                    if not self._has_path(p):
                        self.addItem(str(p))
            e.acceptProposedAction()
        else:
            super().dropEvent(e)

    def _has_path(self, p: Path) -> bool:
        for i in range(self.count()):
            if self.item(i).text() == str(p):
                return True
        return False


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MP4→GIF コンバーター")
        self.resize(900, 640)

        self.cfg: AppConfig = load_config()
        ensure_output_dir(Path(self.cfg.last_output_dir))

        self.worker: Optional[ConverterWorker] = None
        self.thread: Optional[QThread] = None
        self._batch_tasks: List[ConversionTask] = []
        self._batch_index: int = 0

        self._init_ui()

    def _init_ui(self) -> None:
        # メニュー
        file_menu = self.menuBar().addMenu("ファイル")
        self.menu_recent = QMenu("最近使ったファイル", self)
        file_menu.addMenu(self.menu_recent)
        act_quit = QAction("終了", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        central = QWidget()
        root = QVBoxLayout(central)
        self.setCentralWidget(central)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        # 左: ファイルリスト + 操作
        left = QWidget()
        left_v = QVBoxLayout(left)
        self.list_files = FileListWidget()
        self.label_drop = QLabel("ここにMP4をドラッグ&ドロップ")
        self.label_drop.setAlignment(Qt.AlignCenter)
        left_v.addWidget(self.label_drop)
        left_v.addWidget(self.list_files, 1)
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("追加…")
        self.btn_remove = QPushButton("削除")
        self.btn_clear = QPushButton("クリア")
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch(1)
        left_v.addLayout(btn_row)

        # 右: プレビュー + 設定
        right = QWidget()
        right_v = QVBoxLayout(right)
        self.preview = PreviewWidget()
        right_v.addWidget(self.preview, 1)
        self.settings = SettingsPanel()
        self.settings.apply_dict({
            "preset": self.cfg.last_preset,
            **self.cfg.custom_settings,
        })
        right_v.addWidget(self.settings)

        # 出力先/テンプレート
        out_row = QHBoxLayout()
        self.edit_output = QLineEdit(self.cfg.last_output_dir)
        self.btn_browse = QPushButton("出力先…")
        out_row.addWidget(QLabel("出力フォルダ:"))
        out_row.addWidget(self.edit_output, 1)
        out_row.addWidget(self.btn_browse)
        right_v.addLayout(out_row)

        # 時間範囲
        t_row = QHBoxLayout()
        self.start_sec = QDoubleSpinBox()
        self.start_sec.setRange(0.0, 24*3600)
        self.start_sec.setDecimals(3)
        self.start_sec.setSingleStep(0.1)
        self.duration_sec = QDoubleSpinBox()
        self.duration_sec.setRange(0.0, 24*3600)
        self.duration_sec.setDecimals(3)
        self.duration_sec.setSingleStep(0.1)
        t_row.addWidget(QLabel("開始(s)"))
        t_row.addWidget(self.start_sec)
        t_row.addWidget(QLabel("長さ(s)"))
        t_row.addWidget(self.duration_sec)
        t_row.addStretch(1)
        right_v.addLayout(t_row)

        # 設定の初期反映（時間）
        try:
            self.start_sec.setValue(float(self.cfg.custom_settings.get("start", 0.0)))
            self.duration_sec.setValue(float(self.cfg.custom_settings.get("duration", 0.0)))
        except Exception:
            pass

        tpl_row = QHBoxLayout()
        self.edit_template = QLineEdit(self.cfg.filename_template or DEFAULT_TEMPLATE)
        tpl_row.addWidget(QLabel("ファイル名テンプレート:"))
        tpl_row.addWidget(self.edit_template, 1)
        right_v.addLayout(tpl_row)

        # 実行/プレビュー
        act_row = QHBoxLayout()
        self.btn_preview = QPushButton("プレビュー生成")
        self.btn_convert = QPushButton("一括変換開始")
        act_row.addWidget(self.btn_preview)
        act_row.addWidget(self.btn_convert)
        act_row.addStretch(1)
        right_v.addLayout(act_row)

        # 進捗/ログ
        self.progress = QProgressBar()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        right_v.addWidget(self.progress)
        right_v.addWidget(self.log, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([360, 540])

        # シグナル
        self.btn_add.clicked.connect(self._on_add_files)
        self.btn_remove.clicked.connect(self._on_remove_selected)
        self.btn_clear.clicked.connect(self.list_files.clear)
        self.btn_browse.clicked.connect(self._on_browse_output)
        self.btn_convert.clicked.connect(self._on_convert)
        self.btn_preview.clicked.connect(self._on_make_preview)
        self.list_files.itemSelectionChanged.connect(self._on_selection_changed)

        # 最近使ったファイルメニュー構築
        self._rebuild_recent_menu()

    def closeEvent(self, e):  # type: ignore[override]
        # 設定保存
        s = self.settings.to_dict()
        self.cfg.last_preset = s.get("preset", self.cfg.last_preset)
        self.cfg.custom_settings.update({k: s[k] for k in ("fps", "width", "colors")})
        self.cfg.custom_settings.update({
            "start": float(self.start_sec.value()),
            "duration": float(self.duration_sec.value()),
        })
        self.cfg.last_output_dir = self.edit_output.text().strip() or self.cfg.last_output_dir
        self.cfg.filename_template = self.edit_template.text().strip() or self.cfg.filename_template
        save_config(self.cfg)
        super().closeEvent(e)

    # 操作系
    def _on_add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "動画ファイルを選択", str(Path.cwd()), "Video (*.mp4 *.mov *.mkv *.avi)")
        for f in files:
            p = Path(f)
            if not self._has_in_list(p):
                self.list_files.addItem(str(p))
                self.cfg.add_recent_file(p)
        self._rebuild_recent_menu()

    def _on_remove_selected(self) -> None:
        for it in self.list_files.selectedItems():
            row = self.list_files.row(it)
            self.list_files.takeItem(row)

    def _on_browse_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "出力フォルダ", self.edit_output.text())
        if d:
            self.edit_output.setText(d)

    def _on_selection_changed(self) -> None:
        pass

    def _has_in_list(self, p: Path) -> bool:
        for i in range(self.list_files.count()):
            if self.list_files.item(i).text() == str(p):
                return True
        return False

    def _append_log(self, text: str) -> None:
        self.log.appendPlainText(text)

    # プレビュー生成（短いGIFと静止画）
    def _on_make_preview(self) -> None:
        it = self.list_files.currentItem()
        if not it:
            QMessageBox.information(self, "プレビュー", "ファイルを選択してください")
            return
        input_path = Path(it.text())
        if not input_path.exists():
            QMessageBox.warning(self, "プレビュー", "ファイルが存在しません")
            return
        s = self.settings.to_dict()
        out_dir = Path(tempfile.mkdtemp(prefix="gifprev_"))
        # 静止画
        png = out_dir / "frame.png"
        extract_frame_png(input_path, float(self.start_sec.value()), png, s["width"])  # 開始時刻のフレーム
        self.preview.show_source_png(png)
        # 短いGIF
        base_dur = probe_duration(input_path)
        preview_dur = 3.0
        dur_from_ui = float(self.duration_sec.value())
        dur = dur_from_ui if dur_from_ui > 0 else min(preview_dur, max(0.1, base_dur - float(self.start_sec.value())))
        task = ConversionTask(
            input_path=input_path,
            output_dir=out_dir,
            fps=int(s["fps"]),
            width=int(s["width"]),
            colors=int(s["colors"]),
            start=float(self.start_sec.value()),
            duration=dur,
            output_path=out_dir / "preview.gif",
        )
        self._run_worker_for_preview(task, out_dir)

    def _run_worker_for_preview(self, task: ConversionTask, temp_dir: Path) -> None:
        self._stop_worker()
        self.thread = QThread(self)
        self.worker = ConverterWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.worker.convert(task))
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(lambda f, ok, out, err: self._on_preview_done(temp_dir, ok, out, err))
        self.worker.log.connect(self._append_log)
        self.thread.start()

    @pyqtSlot(str, float, str)
    def _on_progress(self, _file: str, percent: float, _line: str) -> None:
        self.progress.setValue(int(percent))

    def _on_preview_done(self, _temp_dir: Path, ok: bool, out_path: str, err: str) -> None:
        self._stop_worker()
        if ok:
            self.preview.show_gif(Path(out_path))
            self._append_log("プレビューGIFを更新しました")
        else:
            QMessageBox.warning(self, "プレビュー失敗", err)

    def _stop_worker(self) -> None:
        if self.thread:
            self.thread.quit()
            self.thread.wait(2000)
            self.thread = None
        self.worker = None

    # 一括変換
    def _on_convert(self) -> None:
        if self.list_files.count() == 0:
            QMessageBox.information(self, "変換", "ファイルを追加してください")
            return
        out_dir = Path(self.edit_output.text().strip())
        ensure_output_dir(out_dir)
        s = self.settings.to_dict()
        fps, width, colors = int(s["fps"]), int(s["width"]), int(s["colors"])
        template = self.edit_template.text().strip() or DEFAULT_TEMPLATE
        start_val = float(self.start_sec.value())
        duration_val = float(self.duration_sec.value())

        files: List[Path] = [Path(self.list_files.item(i).text()) for i in range(self.list_files.count())]
        tasks: List[ConversionTask] = []
        for f in files:
            if not f.exists():
                continue
            self.cfg.add_recent_file(f)
            output_name = build_output_filename(template, f, {"fps": fps, "width": width, "colors": colors})
            tasks.append(ConversionTask(
                input_path=f,
                output_dir=out_dir,
                fps=fps,
                width=width,
                colors=colors,
                start=start_val,
                duration=duration_val,
                output_path=out_dir / output_name,
            ))
        if not tasks:
            QMessageBox.warning(self, "変換", "有効なファイルがありません")
            return

        self._append_log(f"{len(tasks)} 件の変換を開始します")
        self._rebuild_recent_menu()
        self._run_batch(tasks)

    def _run_batch(self, tasks: List[ConversionTask]) -> None:
        # 直列に1つずつ処理
        self._batch_tasks = tasks  # type: ignore[attr-defined]
        self._batch_index = 0      # type: ignore[attr-defined]
        self._start_next_in_batch()

    def _start_next_in_batch(self) -> None:
        tasks: List[ConversionTask] = getattr(self, "_batch_tasks", [])
        idx: int = getattr(self, "_batch_index", 0)
        if idx >= len(tasks):
            self._append_log("すべて完了しました")
            self.progress.setValue(100)
            save_config(self.cfg)
            return
        task = tasks[idx]
        self._append_log(f"[{idx+1}/{len(tasks)}] 変換中: {task.input_path.name}")
        self._stop_worker()
        self.thread = QThread(self)
        self.worker = ConverterWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.worker.convert(task))
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_batch_item_done)
        self.worker.log.connect(self._append_log)
        self.thread.start()

    @pyqtSlot(str, bool, str, str)
    def _on_batch_item_done(self, file: str, ok: bool, out_path: str, err: str) -> None:
        if ok:
            self._append_log(f"完了: {Path(out_path).name}")
        else:
            self._append_log(f"失敗: {Path(file).name} -> {err}")
        self._stop_worker()
        # 次へ
        self._batch_index += 1  # type: ignore[attr-defined]
        self._start_next_in_batch()

    def _rebuild_recent_menu(self) -> None:
        self.menu_recent.clear()
        if not self.cfg.recent_files:
            act = QAction("(なし)", self)
            act.setEnabled(False)
            self.menu_recent.addAction(act)
            return
        for p in self.cfg.recent_files:
            act = QAction(p, self)
            act.triggered.connect(lambda checked=False, path=p: self._open_recent(path))
            self.menu_recent.addAction(act)

    def _open_recent(self, path: str) -> None:
        p = Path(path)
        if p.exists() and p.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi"}:
            if not self._has_in_list(p):
                self.list_files.addItem(str(p))
        else:
            QMessageBox.warning(self, "最近使ったファイル", "ファイルが見つからないか対応形式ではありません")

