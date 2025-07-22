"""
データベース最新ロード日時確認スクリプト
"""
import os
import sys
import json
from datetime import datetime

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """最新データロード日時確認"""
    print("📊 データベース最新ロード日時確認")
    print("=" * 50)
    
    # 設定ファイル読み込み
    try:
        import toml
        from supabase import create_client
        
        secrets = toml.load('.streamlit/secrets.toml')
        
        # Supabase接続
        url = secrets['database']['supabase_url']
        key = secrets['database']['supabase_anon_key']
        supabase = create_client(url, key)
        
        print("✅ データベース接続成功")
        
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return
    
    # 最新データ取得
    try:
        # 最新の5件を取得
        result = supabase.table('invoices').select(
            'id, file_name, created_at, updated_at, uploaded_at, status'
        ).order('created_at', desc=True).limit(5).execute()
        
        if not result.data:
            print("⚠️ データが見つかりません")
            return
        
        print(f"\n📋 最新データ ({len(result.data)}件):")
        print("-" * 50)
        
        for i, record in enumerate(result.data, 1):
            print(f"{i}. ID: {record.get('id', 'N/A')}")
            print(f"   ファイル名: {record.get('file_name', 'N/A')}")
            print(f"   ステータス: {record.get('status', 'N/A')}")
            print(f"   作成日時: {record.get('created_at', 'N/A')}")
            print(f"   更新日時: {record.get('updated_at', 'N/A')}")
            print(f"   アップロード日時: {record.get('uploaded_at', 'N/A')}")
            print()
        
        # 最新の1件の詳細
        latest = result.data[0]
        print("🕒 最新ロード情報:")
        print(f"   最新レコードID: {latest.get('id')}")
        print(f"   最新ファイル: {latest.get('file_name')}")
        print(f"   最新ロード日時: {latest.get('created_at')}")
        
        # 日時をパース
        try:
            from datetime import datetime
            created_str = latest.get('created_at', '')
            if created_str:
                # ISO形式の日時をパース
                dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                jst_dt = dt.replace(tzinfo=None)  # タイムゾーン除去
                print(f"   JST換算: {jst_dt}")
        except Exception as e:
            print(f"   日時変換エラー: {e}")
        
        # 総データ数も確認
        count_result = supabase.table('invoices').select('id', count='exact').execute()
        total_count = count_result.count if hasattr(count_result, 'count') else len(result.data)
        print(f"\n📊 総データ数: {total_count}件")
        
    except Exception as e:
        print(f"❌ データ取得エラー: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main() 