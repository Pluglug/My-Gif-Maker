# MP4→GIF Converter (PyQt)

gpt-5を利用したLLMポン出しアプリです。

OBSで画面キャプチャ → AviUtlで軽く編集 → MP4を書き出し → このツールで低コスト・高品質なGIFにする、という用途向けのラフなGUIアプリです。FFmpegの2パス（パレット生成→適用）でサイズと品質のバランスを取りつつ、ドラッグ&ドロップや一括変換、プレビューも備えています。

## 主な機能
- ドラッグ&ドロップでMP4追加（複数可）
- リアルタイム簡易プレビュー（開始位置の静止画＋短尺GIF）
- 品質プリセット（高品質/標準/軽量）＋カスタム（FPS/幅/色数）
- 時間範囲（開始秒/長さ秒）
- 一括変換と進捗表示、ログ表示
- 設定保存（出力先/プリセット/カスタム/時間/テンプレ/履歴）

## 動作要件
- Windows 10+（PyQt5のホイールが入るPython）
- Python 3.10+ 推奨
- FFmpeg（`ffmpeg` が PATH で呼べること）

## セットアップ / 起動（PowerShell）
```powershell
cd "C:\Users\YourName\Documents\My-Gif-Maker"
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
python -m pip install -U pip setuptools wheel
python -m pip install -r source\requirements.txt

# 開発で起動（推奨）
python -m gif_converter.main

# あるいは未インストールでも実行できる起動口
python run.py
```
※ `python source/gif_converter/main.py` のような直接スクリプト実行は、
パッケージ相対インポートの仕様上失敗します。必ず上記のいずれかで起動してください。

## 使い方
1) 左のリストへMP4をドラッグ&ドロップ（または「追加…」）
2) 右でプリセットを選択（必要ならFPS/幅/色数や時間範囲を調整）
3) 「プレビュー生成」で静止画＋短いGIFを確認
4) 出力先フォルダとファイル名テンプレートを確認
5) 「一括変換開始」で処理

- ファイル名テンプレート: `{name}_{fps}fps_{width}px_{colors}c.gif`（`{name,fps,width,colors}` が展開）
- 設定保存パス（Windows）: `%APPDATA%/GifConverter/config.json`

## プリセット
```python
presets = {
    "高品質": {"fps": 12, "width": 800, "colors": 256},
    "標準": {"fps": 10, "width": 640, "colors": 128},
    "軽量": {"fps": 8, "width": 480, "colors": 64}
}
```

## 変換の中身（FFmpeg 2パス）
- パレット生成
  ```bash
  ffmpeg -y -ss <start> -i <input.mp4> -t <duration> \
    -vf "fps=<fps>,scale=<width>:-1:flags=lanczos,palettegen=max_colors=<colors>:stats_mode=full" \
    palette.png
  ```
- パレット適用
  ```bash
  ffmpeg -y -ss <start> -i <input.mp4> -i palette.png -t <duration> \
    -lavfi "fps=<fps>,scale=<width>:-1:flags=lanczos,paletteuse=dither=sierra2_4a" \
    -loop 0 <output.gif>
  ```
- 時間指定は未設定ならファイル末尾まで。プレビューは短尺（約3秒）で生成。

## 構成
- GUI: PyQt5
- 画像/プレビュー: Pillow（`ImageQt` 経由で `QPixmap`）
- 変換: FFmpeg（`subprocess`）
- パス/設定: `pathlib` / JSON

```text
source/
├── requirements.txt
└── gif_converter/
    ├── main.py              # エントリポイント
    ├── gui/
    │   ├── main_window.py   # メインウィンドウ、D&D、プレビュー、進捗
    │   ├── preview.py       # 静止画/GIFプレビュー
    │   └── settings.py      # プリセット/詳細設定
    ├── core/
    │   ├── converter.py     # FFmpeg 2パス変換（進捗読み取り）
    │   └── utils.py         # ffprobe/時間/出力名ユーティリティ
    ├── config.py            # プリセット/設定保存/履歴
    └── __init__.py
run.py                       # スクリプト実行用の薄いエントリ
```

## メモ
- 進捗はFFmpegのstderrから `time=` を拾って概算表示
- プレビューは開始位置の静止画＋短尺GIFで軽快に
- Pillowの `ImageQt` は環境差があるため、安全な取り回しに変更済み

### TODO
- Mac/Linux 未検証（PyQt5/FFmpegが入れば動く想定）
- 進捗率は近似（カット時間/全体時間でスケール）
- 画面スケール/DPI環境での見た目調整
- もう少し細かいデノイズ/ディザ設定のプリセット化

## 謝辞
- OpenAI、FFmpeg、PyQt、Pillowに感謝します。

## ライセンス
MIT License
