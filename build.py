#!/usr/bin/env python3
"""
GIF Converter ビルドスクリプト
このスクリプトを実行することで、正しい手順でコンパイルできます。
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(command, description):
    """コマンドを実行し、結果を表示"""
    print(f"🔄 {description}...")
    print(f"実行コマンド: {command}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description}完了")
        if result.stdout:
            print("出力:", result.stdout)
    else:
        print(f"❌ {description}失敗")
        print("エラー:", result.stderr)
        return False
    
    return True

def main():
    print("🚀 GIF Converter ビルドプロセス開始")
    print("=" * 50)
    
    # 1. 仮想環境のアクティベート確認
    if not os.environ.get('VIRTUAL_ENV'):
        print("⚠️  仮想環境がアクティベートされていません")
        print("以下のコマンドを実行してください:")
        print("  .venv\\Scripts\\activate")
        return False
    
    print(f"✅ 仮想環境: {os.environ.get('VIRTUAL_ENV')}")
    
    # 2. パッケージのインストール確認
    if not run_command("pip show gif_converter", "パッケージ情報確認"):
        print("📦 パッケージをインストールします...")
        if not run_command("pip install -e .", "パッケージの開発モードインストール"):
            return False
    
    # 3. 古いビルドファイルの削除
    print("🧹 古いビルドファイルを削除...")
    for path in ['build', 'dist', '*.spec']:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"削除: {path}")
    
    # 4. PyInstallerでのコンパイル
    if not run_command(
        'pyinstaller --onefile --windowed --name "GifMaker" run.py',
        "PyInstallerでのコンパイル"
    ):
        return False
    
    # 5. 結果確認
    exe_path = Path("dist/GifMaker.exe")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"🎉 ビルド完了！")
        print(f"実行可能ファイル: {exe_path}")
        print(f"ファイルサイズ: {size_mb:.1f} MB")
        print("\n使用方法:")
        print(f"  直接実行: {exe_path}")
        print("  開発時実行: python run.py")
        print("  モジュール実行: python -m gif_converter.main")
        return True
    else:
        print("❌ 実行可能ファイルが見つかりません")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
