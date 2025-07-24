#!/usr/bin/env python3
"""
統合データベースツール

データベースの状況確認、構造確認、データ表示を行う統合ツール
重複していた複数のスクリプトの機能を統合
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

from infrastructure.database.database import DatabaseManager

class DatabaseTools:
    """データベース操作ツール統合クラス"""
    
    def __init__(self):
        """初期化"""
        self.db_manager = None
        self.supabase_direct = None
        
    def connect(self):
        """データベース接続"""
        try:
            # DatabaseManagerによる接続
            self.db_manager = DatabaseManager()
            print("✅ DatabaseManager接続成功")
            
            # 直接接続も準備（詳細調査用）
            try:
                import toml
                from supabase import create_client
                
                secrets_path = project_root / ".streamlit" / "secrets.toml"
                if secrets_path.exists():
                    secrets = toml.load(secrets_path)
                    url = secrets['database']['supabase_url']
                    key = secrets['database']['supabase_anon_key']
                    self.supabase_direct = create_client(url, key)
                    print("✅ 直接Supabase接続成功")
                else:
                    print("⚠️ secrets.tomlが見つかりません（一部機能制限）")
                    
            except Exception as e:
                print(f"⚠️ 直接接続の準備に失敗: {e}")
                
            return True
            
        except Exception as e:
            print(f"❌ データベース接続エラー: {e}")
            return False
    
    def show_recent_invoices(self, limit: int = 10):
        """最近の請求書データ表示"""
        if not self.db_manager:
            print("❌ データベース接続が必要です")
            return
            
        try:
            print(f"\n📊 最近の請求書データ（{limit}件）")
            print("=" * 60)
            
            recent_invoices = self.db_manager.get_recent_invoices(limit=limit)
            
            if not recent_invoices:
                print("📄 データが見つかりません")
                return
                
            for i, invoice in enumerate(recent_invoices, 1):
                print(f"\n【{i}】ID: {invoice.get('id')}")
                print(f"📧 ユーザー: {invoice.get('user_email')}")
                print(f"📁 ファイル名: {invoice.get('file_name')}")
                print(f"📊 ステータス: {invoice.get('status')}")
                print(f"📅 アップロード日時: {invoice.get('uploaded_at')}")
                
            print(f"\n✅ {len(recent_invoices)}件のデータを表示しました")
            
        except Exception as e:
            print(f"❌ データ取得エラー: {e}")
    
    def show_table_structure(self):
        """テーブル構造の詳細表示"""
        if not self.supabase_direct:
            print("❌ 直接Supabase接続が必要です")
            return
            
        try:
            print("\n📋 invoicesテーブル構造確認")
            print("=" * 60)
            
            # サンプルデータを取得してカラム構造を確認
            result = self.supabase_direct.table('invoices').select('*').limit(1).execute()
            
            if result.data:
                columns = list(result.data[0].keys())
                print(f"📊 カラム数: {len(columns)}")
                print(f"📋 カラム一覧:")
                
                for i, column in enumerate(columns, 1):
                    print(f"  {i:2d}. {column}")
                    
                # データ型情報の推定表示
                sample_row = result.data[0]
                print(f"\n📝 データ型推定（サンプルベース）:")
                for column, value in sample_row.items():
                    value_type = type(value).__name__ if value is not None else "NoneType"
                    print(f"  {column}: {value_type}")
                    
            else:
                print("📄 テーブルにデータがありません")
                
        except Exception as e:
            print(f"❌ 構造取得エラー: {e}")
    
    def show_latest_activity(self):
        """最新データロード日時確認"""
        if not self.supabase_direct:
            print("❌ 直接Supabase接続が必要です")
            return
            
        try:
            print("\n⏰ 最新データロード日時確認")
            print("=" * 60)
            
            # 最新の5件を取得
            result = self.supabase_direct.table('invoices').select(
                'id, file_name, created_at, updated_at, uploaded_at, status'
            ).order('created_at', desc=True).limit(5).execute()
            
            if result.data:
                print(f"📊 最新{len(result.data)}件のアクティビティ:")
                
                for i, item in enumerate(result.data, 1):
                    print(f"\n【{i}】{item.get('file_name', 'N/A')}")
                    print(f"  作成: {item.get('created_at', 'N/A')}")
                    print(f"  更新: {item.get('updated_at', 'N/A')}")
                    print(f"  アップロード: {item.get('uploaded_at', 'N/A')}")
                    print(f"  ステータス: {item.get('status', 'N/A')}")
                    
            else:
                print("📄 アクティビティデータがありません")
                
        except Exception as e:
            print(f"❌ アクティビティ取得エラー: {e}")
    
    def show_detailed_stats(self):
        """詳細統計情報表示"""
        if not self.supabase_direct:
            print("❌ 直接Supabase接続が必要です")
            return
            
        try:
            print("\n📈 詳細統計情報")
            print("=" * 60)
            
            # 総件数
            total_result = self.supabase_direct.table('invoices').select('id', count='exact').execute()
            print(f"📊 総データ件数: {total_result.count}件")
            
            # ステータス別集計
            status_result = self.supabase_direct.table('invoices').select('status').execute()
            if status_result.data:
                from collections import Counter
                status_counts = Counter(item.get('status', 'unknown') for item in status_result.data)
                
                print(f"\n📋 ステータス別集計:")
                for status, count in status_counts.items():
                    print(f"  {status}: {count}件")
            
            # 今日のアップロード数
            today = datetime.now().date().isoformat()
            today_result = self.supabase_direct.table('invoices').select(
                'id', count='exact'
            ).gte('uploaded_at', today).execute()
            
            print(f"\n📅 今日のアップロード: {today_result.count}件")
            
        except Exception as e:
            print(f"❌ 統計情報取得エラー: {e}")
    
    def health_check(self):
        """データベースヘルスチェック"""
        print("\n🏥 データベースヘルスチェック")
        print("=" * 60)
        
        # 基本接続確認
        if self.db_manager and self.db_manager.test_connection():
            print("✅ 基本接続: 正常")
        else:
            print("❌ 基本接続: 異常")
            
        # テーブル存在確認
        if self.db_manager and self.db_manager.check_tables_exist():
            print("✅ 必要テーブル: 存在")
        else:
            print("⚠️ 必要テーブル: 一部不足")
            
        # サンプルデータ確認
        try:
            if self.db_manager:
                sample_data = self.db_manager.get_sample_data()
                if sample_data:
                    print(f"✅ サンプルデータ: {len(sample_data)}件取得可能")
                else:
                    print("⚠️ サンプルデータ: 取得できません")
        except:
            print("❌ サンプルデータ: エラー")

def main():
    """メイン実行関数"""
    print("🔧 統合データベースツール")
    print("=" * 60)
    
    # ツール初期化
    db_tools = DatabaseTools()
    
    # 接続確認
    if not db_tools.connect():
        print("❌ データベース接続に失敗しました")
        return
    
    # 引数による機能切り替え
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "recent":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            db_tools.show_recent_invoices(limit)
        elif command == "structure":
            db_tools.show_table_structure()
        elif command == "activity":
            db_tools.show_latest_activity()
        elif command == "stats":
            db_tools.show_detailed_stats()
        elif command == "health":
            db_tools.health_check()
        elif command == "all":
            db_tools.health_check()
            db_tools.show_recent_invoices(5)
            db_tools.show_table_structure()
            db_tools.show_latest_activity()
            db_tools.show_detailed_stats()
        else:
            print(f"❌ 不明なコマンド: {command}")
            print("\n利用可能なコマンド:")
            print("  recent [件数]  - 最近のデータ表示")
            print("  structure     - テーブル構造表示")
            print("  activity      - 最新アクティビティ")
            print("  stats         - 詳細統計情報")
            print("  health        - ヘルスチェック")
            print("  all           - 全機能実行")
    else:
        # デフォルト実行（全機能）
        db_tools.health_check()
        db_tools.show_recent_invoices(5)
        db_tools.show_latest_activity()

if __name__ == "__main__":
    main() 