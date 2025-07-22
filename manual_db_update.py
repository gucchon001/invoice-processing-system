#!/usr/bin/env python3
"""
Supabaseデータベースの手動更新スクリプト
invoicesテーブルにextracted_dataカラムを追加します
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from infrastructure.database.database import DatabaseManager
import json

def main():
    try:
        print("📊 データベース接続中...")
        db = DatabaseManager()
        
        print("🔧 invoicesテーブルにextracted_dataカラムを追加中...")
        
        # SQLクエリの実行
        sql_queries = [
            # extracted_dataカラムを追加
            "ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS extracted_data JSONB;",
            
            # カラムにコメントを追加
            "COMMENT ON COLUMN public.invoices.extracted_data IS 'AI抽出された請求書データ（JSON形式）';",
            
            # インデックス作成（JSON検索高速化のため）
            "CREATE INDEX IF NOT EXISTS idx_invoices_extracted_data_gin ON public.invoices USING GIN (extracted_data);"
        ]
        
        for i, sql in enumerate(sql_queries, 1):
            print(f"🔄 SQL実行中 ({i}/{len(sql_queries)}): {sql[:50]}...")
            try:
                result = db.supabase.rpc('execute_sql', {'query': sql}).execute()
                print(f"✅ SQL実行成功: クエリ {i}")
            except Exception as e:
                # エラーを無視して続行（カラムが既に存在する場合など）
                print(f"⚠️ SQL実行でエラー（続行します）: {e}")
        
        print("\n🔍 更新後のテーブル構造を確認中...")
        
        # テーブル構造確認
        sample_result = db.supabase.table('invoices').select('*').limit(1).execute()
        if sample_result.data:
            columns = list(sample_result.data[0].keys())
            print(f"📋 現在のカラム一覧: {columns}")
            
            if 'extracted_data' in columns:
                print("✅ extracted_dataカラムが正常に追加されました！")
            else:
                print("❌ extracted_dataカラムが見つかりません")
        
        print("\n✅ データベース更新処理完了！")
        
    except Exception as e:
        print(f"❌ データベース更新エラー: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 