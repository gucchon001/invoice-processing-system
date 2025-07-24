#!/usr/bin/env python3
"""
28カラム表示テストスクリプト
データベースとブラウザ表示の一致を確認
"""
import os
import sys
import json
from datetime import datetime

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_28_column_display():
    """28カラム表示テスト"""
    print("🧪 28カラム表示一致テスト")
    print("=" * 60)
    
    try:
        import toml
        from supabase import create_client
        # インポートパスを修正
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", "src/app/main.py")
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        prepare_invoice_data_for_aggrid = main_module.prepare_invoice_data_for_aggrid
        
        secrets = toml.load('.streamlit/secrets.toml')
        url = secrets['database']['supabase_url']
        key = secrets['database']['supabase_anon_key']
        supabase = create_client(url, key)
        
        print("✅ データベース接続成功")
        
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return
    
    # 1. データベースから実際のデータを取得
    try:
        result = supabase.table('invoices').select('*').limit(3).execute()
        
        if not result.data:
            print("❌ テストデータが見つかりません")
            return
            
        db_data = result.data
        print(f"📊 テストデータ取得: {len(db_data)}件")
        
        # データベースのカラム一覧
        db_columns = list(db_data[0].keys())
        print(f"📋 データベースカラム数: {len(db_columns)}")
        
    except Exception as e:
        print(f"❌ データベース取得エラー: {e}")
        return
    
    # 2. ag-grid用データ変換テスト
    try:
        df = prepare_invoice_data_for_aggrid(db_data)
        aggrid_columns = list(df.columns)
        print(f"📊 ag-gridカラム数: {len(aggrid_columns)}")
        
    except Exception as e:
        print(f"❌ データ変換エラー: {e}")
        return
    
    # 3. カラム一致確認
    print(f"\n🔍 カラム一致確認:")
    print(f"  データベース: {len(db_columns)}カラム")
    print(f"  ag-grid表示: {len(aggrid_columns)}カラム")
    
    # 完全一致確認
    db_set = set(db_columns)
    aggrid_set = set(aggrid_columns)
    
    if db_set == aggrid_set:
        print("✅ **完全一致**: データベースとag-grid表示のカラムが完全に一致しています")
    else:
        print("⚠️ **差異あり**: カラムに違いがあります")
        
        missing_in_aggrid = db_set - aggrid_set
        extra_in_aggrid = aggrid_set - db_set
        
        if missing_in_aggrid:
            print(f"  📊 ag-gridに不足: {missing_in_aggrid}")
        if extra_in_aggrid:
            print(f"  📊 ag-gridに余分: {extra_in_aggrid}")
    
    # 4. 詳細カラム確認
    print(f"\n📋 完全カラム一覧対比:")
    
    all_columns = sorted(db_set | aggrid_set)
    for i, column in enumerate(all_columns, 1):
        db_status = "✅" if column in db_set else "❌"
        aggrid_status = "✅" if column in aggrid_set else "❌"
        
        # サンプル値の取得
        sample_value = "N/A"
        if column in db_columns and len(db_data) > 0:
            sample_value = str(db_data[0].get(column, "None"))[:30]
        
        print(f"  {i:2d}. {column:<30} | DB:{db_status} | AG:{aggrid_status} | {sample_value}")
    
    # 5. データ型の確認
    print(f"\n🔧 データ型確認:")
    if len(df) > 0:
        for column in aggrid_columns[:10]:  # 最初の10カラムのみ表示
            dtype = str(df[column].dtype)
            sample = df[column].iloc[0] if len(df) > 0 else "N/A"
            print(f"  {column:<25} | {dtype:<15} | {str(sample)[:20]}")
        
        if len(aggrid_columns) > 10:
            print(f"  ... 他{len(aggrid_columns) - 10}カラム")
    
    # 6. 結果レポート
    print(f"\n📊 最終結果:")
    print(f"  🎯 目標: 28カラム完全一致")
    print(f"  📊 データベース: {len(db_columns)}カラム")
    print(f"  📺 ブラウザ表示: {len(aggrid_columns)}カラム")
    
    if len(db_columns) == 28 and len(aggrid_columns) == 28 and db_set == aggrid_set:
        print("🎉 **SUCCESS**: 28カラム完全一致が達成されました！")
        
        # 成功レポートをファイルに保存
        success_report = {
            'test_time': datetime.now().isoformat(),
            'status': 'SUCCESS',
            'db_columns': len(db_columns),
            'aggrid_columns': len(aggrid_columns),
            'perfect_match': True,
            'all_columns': all_columns
        }
        
        with open('28_column_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(success_report, f, indent=2, ensure_ascii=False)
        
        print("📄 成功レポートを28_column_test_report.jsonに保存しました")
        
    else:
        print("❌ **FAILED**: 完全一致に到達していません")
        print("   修正が必要です")

if __name__ == "__main__":
    test_28_column_display() 