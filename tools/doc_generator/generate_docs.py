# 請求書処理システム ドキュメント自動生成ツール

"""
概要:
master_data/ ディレクトリ内のYAMLファイルを読み込み、
docs/ ディレクトリのマークダウンドキュメントを自動生成・更新する。

設計思想:
- Single Source of Truth (SSOT): YAMLファイルを唯一のマスターデータとする
- 冪等性: 何度実行しても同じ結果になることを保証する
- 拡張性: 新しいテーブルやクラスの追加が容易な設計
- テンプレートベース: Jinja2テンプレートを使用して出力形式を柔軟に変更可能
"""

import yaml
from jinja2 import Environment, FileSystemLoader
import os

# --- 設定 ---
MASTER_DATA_DIR = 'master_data'
DOCS_DIR = 'docs'
TEMPLATES_DIR = 'tools/doc_generator/templates'
TABLES_YAML_PATH = os.path.join(MASTER_DATA_DIR, 'tables.yml')
TABLE_SPEC_TEMPLATE = 'table_spec_template.md.j2'
TABLE_SPEC_OUTPUT_PATH = os.path.join(DOCS_DIR, '19_テーブル設計詳細仕様書.md')


class DocGenerator:
    """
    ドキュメント自動生成のメインクラス
    """
    def __init__(self):
        """
        コンストラクタ：Jinja2環境を初期化
        """
        self.env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), trim_blocks=True, lstrip_blocks=True)
        print("✅ DocGeneratorが初期化されました。")
        print(f"   - テンプレートディレクトリ: {os.path.abspath(TEMPLATES_DIR)}")

    def load_yaml_data(self, file_path):
        """
        YAMLファイルを読み込み、データを返す

        Args:
            file_path (str): YAMLファイルのパス

        Returns:
            dict: 読み込んだデータ
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                print(f"✅ YAMLファイルを正常に読み込みました: {file_path}")
                return data
        except FileNotFoundError:
            print(f"❌エラー: YAMLファイルが見つかりません: {file_path}")
            return None
        except yaml.YAMLError as e:
            print(f"❌エラー: YAMLの解析に失敗しました: {file_path}\n{e}")
            return None

    def render_template(self, template_name, context, output_path):
        """
        Jinja2テンプレートをレンダリングしてファイルに出力する

        Args:
            template_name (str): テンプレートファイル名
            context (dict): テンプレートに渡すデータ
            output_path (str): 出力先のファイルパス
        """
        try:
            template = self.env.get_template(template_name)
            rendered_content = template.render(context)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered_content)
            
            print(f"✅ ドキュメントが正常に生成されました: {output_path}")

        except Exception as e:
            print(f"❌エラー: テンプレートのレンダリングまたはファイル書き込み中にエラーが発生しました。\n{e}")

    def generate_table_spec_doc(self):
        """
        テーブル設計詳細仕様書を生成する
        """
        print("\n--- テーブル設計詳細仕様書の生成を開始 ---")
        
        tables_data = self.load_yaml_data(TABLES_YAML_PATH)
        
        if tables_data:
            context = {
                'tables': tables_data.get('tables', {})
            }
            self.render_template(TABLE_SPEC_TEMPLATE, context, TABLE_SPEC_OUTPUT_PATH)
        
        print("--- テーブル設計詳細仕様書の生成を終了 ---\n")


def main():
    """
    メイン実行関数
    """
    print("🚀 ドキュメント自動生成プロセスを開始します...")
    
    generator = DocGenerator()
    
    # 将来的に他のドキュメント生成メソッドもここに追加
    generator.generate_table_spec_doc()
    # generator.generate_er_diagram()
    # generator.generate_class_diagram()
    
    print("🎉 すべてのドキュメント生成プロセスが完了しました。")


if __name__ == '__main__':
    # スクリプトが直接実行された場合にmain()を呼び出す
    main() 