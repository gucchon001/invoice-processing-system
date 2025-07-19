"""
請求書処理自動化システム - メインエントリーポイント

このファイルは新しいディレクトリ構造のエントリーポイントです。
実際のアプリケーションロジックは src/app/main.py に移動されています。
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# メインアプリケーションを実行
if __name__ == "__main__":
    from app.main import main
    main() 