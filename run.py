import os
import sys

# 開発環境で未インストールでも動くように、source をパスに追加
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(CURRENT_DIR, "source")
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from gif_converter.main import main

if __name__ == "__main__":
    main()
