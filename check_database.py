#!/usr/bin/env python3
"""
データベース確認スクリプト
最近処理された請求書データを表示します
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
        
        print("🔍 最近の請求書データを取得中...")
        recent_invoices = db.get_recent_invoices(limit=10)
        
        print(f"\n📋 取得結果: {len(recent_invoices)}件")
        print("=" * 60)
        
        for i, invoice in enumerate(recent_invoices, 1):
            print(f"\n【{i}】ID: {invoice.get('id')}")
            print(f"📧 ユーザー: {invoice.get('user_email')}")
            print(f"📁 ファイル名: {invoice.get('file_name')}")
            print(f"📊 ステータス: {invoice.get('status')}")
            print(f"📅 アップロード日時: {invoice.get('uploaded_at')}")
            
        print(f"\n✅ 成功！{len(recent_invoices)}件のデータがデータベースに保存されています。")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main() 