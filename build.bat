@echo off
chcp 65001 >nul
echo 🚀 GIF Converter ビルドプロセス開始
echo ==================================================

REM 仮想環境のアクティベート
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ 仮想環境が見つかりません
    echo python -m venv .venv を実行してください
    pause
    exit /b 1
)

echo 🔄 仮想環境をアクティベート中...
call .venv\Scripts\activate.bat

REM パッケージのインストール確認
echo 🔄 パッケージ情報確認中...
pip show gif_converter >nul 2>&1
if errorlevel 1 (
    echo 📦 パッケージをインストール中...
    pip install -e .
    if errorlevel 1 (
        echo ❌ パッケージのインストールに失敗しました
        pause
        exit /b 1
    )
)

REM 古いビルドファイルの削除
echo 🧹 古いビルドファイルを削除中...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec"

REM PyInstallerでのコンパイル
echo 🔄 PyInstallerでコンパイル中...
pyinstaller --onefile --windowed --name "GifMaker" run.py
if errorlevel 1 (
    echo ❌ コンパイルに失敗しました
    pause
    exit /b 1
)

REM 結果確認
if exist "dist\GifMaker.exe" (
    echo 🎉 ビルド完了！
    echo 実行可能ファイル: dist\GifMaker.exe
    echo.
    echo 使用方法:
    echo   直接実行: dist\GifMaker.exe
    echo   開発時実行: python run.py
    echo   モジュール実行: python -m gif_converter.main
) else (
    echo ❌ 実行可能ファイルが見つかりません
)

pause
