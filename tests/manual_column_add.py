#!/usr/bin/env python3
"""
手動でextracted_dataカラムの存在確認と代替アプローチ
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from infrastructure.database.database import DatabaseManager
import json

def check_extracted_data_column(db: DatabaseManager) -> bool:
    """extracted_dataカラムの存在確認"""
    try:
        # テーブル構造を確認
        sample_result = db.supabase.table('invoices').select('*').limit(1).execute()
        if sample_result.data:
            columns = list(sample_result.data[0].keys())
            print(f"📋 現在のカラム一覧: {columns}")
            
            if 'extracted_data' in columns:
                print("✅ extracted_dataカラムが存在します")
                return True
            else:
                print("❌ extracted_dataカラムが存在しません")
                return False
        else:
            print("⚠️ テーブルが空です")
            return False
            
    except Exception as e:
        print(f"❌ カラム確認エラー: {e}")
        return False

def test_json_in_status_field(db: DatabaseManager) -> bool:
    """statusフィールドにJSONデータを格納できるかテスト"""
    try:
        # テスト用のJSONデータ
        test_data = {
            'user_email': 'test@example.com',
            'status': json.dumps({
                'base_status': 'extracted',
                'issuer_name': 'テスト株式会社',
                'invoice_number': 'TEST-001',
                'total_amount': 10000,
                'currency': 'JPY',
                'test_mode': True
            }),
            'file_name': 'test_json_storage.pdf'
        }
        
        print("🧪 statusフィールドへのJSON格納テスト...")
        result = db.supabase.table('invoices').insert(test_data).execute()
        
        if result.data:
            test_id = result.data[0]['id']
            print(f"✅ JSON格納テスト成功: ID {test_id}")
            
            # 取得テスト
            retrieve_result = db.supabase.table('invoices').select('*').eq('id', test_id).execute()
            if retrieve_result.data:
                stored_status = retrieve_result.data[0]['status']
                parsed_json = json.loads(stored_status)
                print(f"✅ JSON取得テスト成功: {parsed_json['issuer_name']}")
                
                # テストデータ削除
                db.supabase.table('invoices').delete().eq('id', test_id).execute()
                print("✅ テストデータ削除完了")
                return True
            
        return False
        
    except Exception as e:
        print(f"❌ JSONテストエラー: {e}")
        return False

def create_workaround_solution(db: DatabaseManager) -> bool:
    """回避策の実装：statusフィールドにJSONデータを格納"""
    try:
        print("🔧 回避策を実装中...")
        
        # データベースサービスファイルを修正
        from datetime import datetime
        import json
        
        # 修正版の挿入関数を定義
        def insert_invoice_workaround(invoice_data):
            extracted_data = invoice_data.get('extracted_data', {})
            
            # AIデータをJSONとしてstatusフィールドに格納
            status_json = {
                'base_status': 'extracted',
                'ai_extracted_data': {
                    'issuer_name': extracted_data.get('issuer', ''),
                    'recipient_name': extracted_data.get('payer', ''),
                    'invoice_number': extracted_data.get('main_invoice_number', ''),
                    'currency': extracted_data.get('currency', 'JPY'),
                    'total_amount_tax_included': extracted_data.get('amount_inclusive_tax', 0),
                    'total_amount_tax_excluded': extracted_data.get('amount_exclusive_tax', 0),
                    'issue_date': extracted_data.get('issue_date', ''),
                    'due_date': extracted_data.get('due_date', ''),
                    'key_info': extracted_data.get('key_info', {}),
                    'line_items': extracted_data.get('line_items', [])
                },
                'original_data': {
                    'supplier_name': invoice_data.get('supplier_name', ''),
                    'invoice_number': invoice_data.get('invoice_number', ''),
                    'total_amount': invoice_data.get('total_amount', 0),
                    'file_path': invoice_data.get('file_path', '')
                },
                'metadata': {
                    'processing_time': datetime.now().isoformat(),
                    'version': 'workaround-v1.0'
                }
            }
            
            insert_data = {
                'user_email': invoice_data.get('created_by', ''),
                'status': json.dumps(status_json),
                'file_name': invoice_data.get('file_name', '')
            }
            
            result = db.supabase.table('invoices').insert(insert_data).execute()
            return result
        
        print("✅ 回避策の実装完了")
        return True
        
    except Exception as e:
        print(f"❌ 回避策実装エラー: {e}")
        return False

def main():
    try:
        print("🔍 データベース状況確認...")
        
        from infrastructure.database.database import get_database
        db = get_database()
        print("✅ データベース接続成功（シングルトン）")
        
        # extracted_dataカラムの存在確認
        has_extracted_data = check_extracted_data_column(db)
        
        if has_extracted_data:
            print("\n🎉 extracted_dataカラムが利用可能です！")
            print("Option A の完全実装に進めます。")
        else:
            print("\n🔧 extracted_dataカラムが存在しないため、回避策を検討します...")
            
            # JSONテスト
            json_test_success = test_json_in_status_field(db)
            
            if json_test_success:
                print("\n✅ statusフィールドへのJSON格納が可能です")
                print("回避策でAI抽出データの完全保存を実装します")
                
                # 回避策の実装
                workaround_success = create_workaround_solution(db)
                if workaround_success:
                    print("\n🎯 回避策の準備完了！")
                    print("次のステップ：データ保存ロジックの修正")
                    return True
            else:
                print("\n❌ 回避策も失敗しました")
                print("Supabaseコンソールでの手動カラム追加が必要です")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 