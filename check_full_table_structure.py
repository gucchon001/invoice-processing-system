#!/usr/bin/env python3
"""
invoicesテーブルの完全なカラム構造確認スクリプト
データベースの全28カラムを特定し、ブラウザ表示との差異を確認
"""
import os
import sys
import json
from datetime import datetime

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """invoicesテーブルの全カラム構造を確認"""
    print("🔍 invoicesテーブル完全構造確認")
    print("=" * 60)
    
    try:
        import toml
        from supabase import create_client
        
        secrets = toml.load('.streamlit/secrets.toml')
        url = secrets['database']['supabase_url']
        key = secrets['database']['supabase_anon_key']
        supabase = create_client(url, key)
        
        print("✅ データベース接続成功")
        
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return
    
    # 1. サンプルデータから全カラムを取得
    try:
        result = supabase.table('invoices').select('*').limit(1).execute()
        
        if result.data and len(result.data) > 0:
            all_columns = list(result.data[0].keys())
            total_columns = len(all_columns)
            
            print(f"📊 総カラム数: {total_columns}")
            print(f"🎯 目標カラム数: 28")
            print(f"📈 差異: {total_columns - 28} カラム")
            
            print(f"\n📋 全カラム一覧:")
            for i, column in enumerate(all_columns, 1):
                sample_value = result.data[0].get(column)
                value_type = type(sample_value).__name__
                value_preview = str(sample_value)[:50] if sample_value is not None else "None"
                print(f"  {i:2d}. {column:<30} | {value_type:<10} | {value_preview}")
            
            # 2. カラムを分類
            print(f"\n🏷️ カラム分類:")
            
            basic_columns = [col for col in all_columns if col in [
                'id', 'user_email', 'file_name', 'status', 'uploaded_at', 'created_at', 'updated_at'
            ]]
            
            invoice_info_columns = [col for col in all_columns if col in [
                'issuer_name', 'recipient_name', 'invoice_number', 'registration_number', 'currency'
            ]]
            
            amount_columns = [col for col in all_columns if col in [
                'total_amount_tax_included', 'total_amount_tax_excluded'
            ]]
            
            date_columns = [col for col in all_columns if col in [
                'issue_date', 'due_date'
            ]]
            
            json_columns = [col for col in all_columns if col in [
                'key_info', 'raw_response', 'extracted_data'
            ]]
            
            validation_columns = [col for col in all_columns if col in [
                'is_valid', 'completeness_score', 'validation_errors', 'validation_warnings'
            ]]
            
            meta_columns = [col for col in all_columns if col in [
                'processing_time', 'gemini_model', 'gdrive_file_id', 'file_path', 'file_size'
            ]]
            
            # 分類されていないカラム
            classified_columns = (basic_columns + invoice_info_columns + amount_columns + 
                                date_columns + json_columns + validation_columns + meta_columns)
            other_columns = [col for col in all_columns if col not in classified_columns]
            
            print(f"  📂 基本情報 ({len(basic_columns)}): {basic_columns}")
            print(f"  📄 請求書情報 ({len(invoice_info_columns)}): {invoice_info_columns}")
            print(f"  💰 金額情報 ({len(amount_columns)}): {amount_columns}")
            print(f"  📅 日付情報 ({len(date_columns)}): {date_columns}")
            print(f"  📋 JSON情報 ({len(json_columns)}): {json_columns}")
            print(f"  ✅ 検証情報 ({len(validation_columns)}): {validation_columns}")
            print(f"  🔧 メタデータ ({len(meta_columns)}): {meta_columns}")
            print(f"  ❓ その他 ({len(other_columns)}): {other_columns}")
            
            # 3. 現在のag-grid表示用カラムとの比較
            print(f"\n🔄 ブラウザ表示用カラム定義を確認...")
            
            # ag-grid用に使用されているカラム（main.pyから推定）
            aggrid_columns = [
                'id', 'file_name', 'supplier_name', 'recipient_name', 'invoice_number',
                'invoice_date', 'due_date', 'amount_inclusive_tax', 'amount_exclusive_tax',
                'currency', 'is_valid', 'completeness_score', 'processing_time',
                'registration_number', 'status', 'created_at', 'updated_at',
                'user_email', 'gdrive_file_id', 'file_size', 'gemini_model'
            ]
            
            # データベースカラムとag-gridカラムのマッピング問題を特定
            missing_in_aggrid = [col for col in all_columns if col not in aggrid_columns]
            missing_in_db = [col for col in aggrid_columns if col not in all_columns]
            
            print(f"\n⚠️ 差異分析:")
            print(f"  📊 DBに存在するがag-gridに無い: {missing_in_aggrid}")
            print(f"  📊 ag-gridで使用されているがDBに無い: {missing_in_db}")
            
            # 4. 完全な28カラム定義を出力
            print(f"\n📄 完全な28カラム構造:")
            with open('complete_table_structure.json', 'w', encoding='utf-8') as f:
                structure = {
                    'total_columns': total_columns,
                    'all_columns': all_columns,
                    'column_details': {}
                }
                
                for column in all_columns:
                    sample_value = result.data[0].get(column)
                    structure['column_details'][column] = {
                        'type': type(sample_value).__name__,
                        'sample_value': sample_value,
                        'category': 'unknown'
                    }
                    
                    # カテゴリ分類
                    if column in basic_columns:
                        structure['column_details'][column]['category'] = 'basic'
                    elif column in invoice_info_columns:
                        structure['column_details'][column]['category'] = 'invoice_info'
                    elif column in amount_columns:
                        structure['column_details'][column]['category'] = 'amount'
                    elif column in date_columns:
                        structure['column_details'][column]['category'] = 'date'
                    elif column in json_columns:
                        structure['column_details'][column]['category'] = 'json'
                    elif column in validation_columns:
                        structure['column_details'][column]['category'] = 'validation'
                    elif column in meta_columns:
                        structure['column_details'][column]['category'] = 'meta'
                
                json.dump(structure, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"  💾 完全構造をcomplete_table_structure.jsonに保存しました")
            
        else:
            print("❌ データが見つかりません")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main() 