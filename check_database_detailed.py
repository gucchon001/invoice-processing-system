"""
データベース詳細確認スクリプト
請求書データの保存状況を詳しく調査
"""
import streamlit as st
import sys
import os

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import json
from datetime import datetime

def main():
    """データベース詳細確認"""
    print("=" * 60)
    print("📊 データベース詳細確認スクリプト")
    print("=" * 60)
    
    # 設定ファイル読み込みとデータベース接続
    try:
        import toml
        from supabase import create_client
        
        secrets = toml.load('.streamlit/secrets.toml')
        url = secrets['database']['supabase_url']
        key = secrets['database']['supabase_anon_key']
        supabase = create_client(url, key)
        
        print("✅ 設定ファイル読み込み完了")
        print("✅ データベース接続成功")
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return
    
    # 1. テーブル基本情報
    print("\n📋 テーブル基本情報:")
    try:
        result = supabase.table('invoices').select('*').limit(5).execute()
        total_count = len(result.data) if result.data else 0
        print(f"   請求書データ数: {total_count}件（表示上限5件）")
        
        if result.data and len(result.data) > 0:
            print(f"   カラム数: {len(result.data[0].keys())}")
            print(f"   カラム一覧: {list(result.data[0].keys())}")
    except Exception as e:
        print(f"   ❌ テーブル情報取得エラー: {e}")
    
    # 2. 最新の5件詳細表示
    print("\n📊 最新データ詳細（5件）:")
    try:
        result = supabase.table('invoices').select('*').order('created_at', desc=True).limit(5).execute()
        
        if not result.data:
            print("   ⚠️ データが見つかりません")
            return
        
        for i, record in enumerate(result.data, 1):
            print(f"\n   📄 レコード {i} (ID: {record.get('id', 'N/A')}):")
            print(f"      ファイル名: {record.get('file_name', 'N/A')}")
            print(f"      ステータス: {record.get('status', 'N/A')}")
            print(f"      作成日時: {record.get('created_at', 'N/A')}")
            
            # 基本情報
            print(f"      請求元: {record.get('issuer_name', 'None')}")
            print(f"      請求先: {record.get('recipient_name', 'None')}")
            print(f"      請求書番号: {record.get('invoice_number', 'None')}")
            print(f"      税込金額: {record.get('total_amount_tax_included', 'None')}")
            print(f"      通貨: {record.get('currency', 'None')}")
            print(f"      発行日: {record.get('issue_date', 'None')}")
            
            # AI抽出データ
            extracted_data = record.get('extracted_data')
            if extracted_data:
                print(f"      AI抽出データ: 存在 ({len(extracted_data)}項目)")
                if isinstance(extracted_data, dict):
                    for key, value in list(extracted_data.items())[:5]:  # 最初の5項目
                        print(f"        {key}: {value}")
                    if len(extracted_data) > 5:
                        print(f"        ... 他{len(extracted_data) - 5}項目")
            else:
                print(f"      AI抽出データ: None")
            
            # キー情報
            key_info = record.get('key_info')
            if key_info:
                print(f"      キー情報: 存在 ({len(key_info)}項目)")
                if isinstance(key_info, dict):
                    for key, value in key_info.items():
                        print(f"        {key}: {value}")
            else:
                print(f"      キー情報: None")
            
            # 品質情報
            print(f"      完全性スコア: {record.get('completeness_score', 'None')}")
            print(f"      処理時間: {record.get('processing_time', 'None')}")
            print(f"      有効フラグ: {record.get('is_valid', 'None')}")
            
    except Exception as e:
        print(f"   ❌ データ詳細取得エラー: {e}")
    
    # 3. データ品質分析
    print("\n🔍 データ品質分析:")
    try:
        result = supabase.table('invoices').select('*').execute()
        
        if not result.data:
            print("   ⚠️ 分析用データがありません")
            return
        
        total = len(result.data)
        
        # 各フィールドの充填率
        fields_to_check = [
            'issuer_name', 'recipient_name', 'invoice_number', 
            'total_amount_tax_included', 'issue_date', 'extracted_data'
        ]
        
        print(f"   総レコード数: {total}")
        
        for field in fields_to_check:
            filled = sum(1 for record in result.data if record.get(field) is not None and record.get(field) != '')
            rate = (filled / total * 100) if total > 0 else 0
            print(f"   {field}: {filled}/{total} ({rate:.1f}%)")
        
        # AI抽出成功率
        extracted_success = sum(1 for record in result.data if record.get('extracted_data') is not None)
        success_rate = (extracted_success / total * 100) if total > 0 else 0
        print(f"   AI抽出成功率: {extracted_success}/{total} ({success_rate:.1f}%)")
        
    except Exception as e:
        print(f"   ❌ データ品質分析エラー: {e}")
    
    # 4. 問題のあるレコード特定
    print("\n⚠️ 問題のあるレコード:")
    try:
        result = supabase.table('invoices').select('*').execute()
        
        if result.data:
            problematic = []
            for record in result.data:
                issues = []
                
                # AI抽出データがない
                if not record.get('extracted_data'):
                    issues.append("AI抽出データなし")
                
                # 基本情報が不足
                if not record.get('issuer_name'):
                    issues.append("請求元名なし")
                
                if not record.get('total_amount_tax_included'):
                    issues.append("金額なし")
                
                if issues:
                    problematic.append({
                        'id': record.get('id'),
                        'file_name': record.get('file_name'),
                        'issues': issues
                    })
            
            if problematic:
                print(f"   問題のあるレコード数: {len(problematic)}")
                for prob in problematic[:3]:  # 最初の3件
                    print(f"   ID {prob['id']} ({prob['file_name']}): {', '.join(prob['issues'])}")
                if len(problematic) > 3:
                    print(f"   ... 他{len(problematic) - 3}件")
            else:
                print("   ✅ 問題のあるレコードはありません")
                
    except Exception as e:
        print(f"   ❌ 問題レコード特定エラー: {e}")
    
    print("\n" + "=" * 60)
    print("🔚 データベース詳細確認完了")
    print("=" * 60)

if __name__ == "__main__":
    main() 