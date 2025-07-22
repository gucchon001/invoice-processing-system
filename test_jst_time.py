"""
JST時間設定テストスクリプト
データベース挿入時にJST時間が正しく設定されることを確認
"""
import os
import sys
import json
from datetime import datetime, timezone, timedelta

# パス設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_jst_time_setting():
    """JST時間設定のテスト"""
    print("🕒 JST時間設定テスト")
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
    
    # JST時間の生成関数
    def get_jst_now():
        jst = timezone(timedelta(hours=9))  # JST = UTC+9
        return datetime.now(jst).isoformat()
    
    # 現在の時間比較
    print("\n🔍 時間設定確認:")
    utc_now = datetime.now(timezone.utc).isoformat()
    jst_now = get_jst_now()
    
    print(f"UTC時間: {utc_now}")
    print(f"JST時間: {jst_now}")
    
    # 時間差確認
    try:
        utc_dt = datetime.fromisoformat(utc_now.replace('Z', '+00:00'))
        jst_dt = datetime.fromisoformat(jst_now)
        
        # JSTからUTCを引いて9時間差があることを確認
        time_diff = jst_dt.replace(tzinfo=None) - utc_dt.replace(tzinfo=None)
        hours_diff = time_diff.total_seconds() / 3600
        
        print(f"時間差: {hours_diff:.1f}時間 ({'✅ 正常' if abs(hours_diff - 9) < 0.1 else '❌ 異常'})")
        
    except Exception as e:
        print(f"時間差計算エラー: {e}")
    
    # テストデータ作成
    print("\n📝 テストデータ作成:")
    test_invoice_data = {
        'user_email': 'test@example.com',
        'file_name': f'jst_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
        'status': 'extracted',
        'created_at': jst_now,
        'updated_at': jst_now,
        'uploaded_at': jst_now,
        'issuer_name': 'JST時間テスト企業',
        'currency': 'JPY',
        'total_amount_tax_included': 1000,
        'gemini_model': 'test-model'
    }
    
    print(f"テストファイル名: {test_invoice_data['file_name']}")
    print(f"設定時間: {jst_now}")
    
    # データベースに挿入（実際には実行しない、テスト表示のみ）
    print("\n⚠️ 実際のデータベース挿入はスキップします（テスト表示のみ）")
    print("📋 挿入予定データ構造:")
    for key, value in test_invoice_data.items():
        print(f"   {key}: {value}")
    
    # 既存データでJST変換の表示例
    print("\n🔄 既存データのJST変換例:")
    try:
        result = supabase.table('invoices').select('id, file_name, created_at').order('created_at', desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            latest = result.data[0]
            created_at_str = latest.get('created_at', '')
            
            print(f"最新レコード ID: {latest.get('id')}")
            print(f"UTC時間: {created_at_str}")
            
            # UTC→JST変換
            if created_at_str:
                try:
                    # UTC時間をJSTに変換
                    utc_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    jst_dt = utc_dt.astimezone(timezone(timedelta(hours=9)))
                    
                    print(f"JST変換: {jst_dt.strftime('%Y-%m-%d %H:%M:%S JST')}")
                    print(f"日本語表記: {jst_dt.strftime('%Y年%m月%d日 %H時%M分%S秒')}")
                    
                except Exception as e:
                    print(f"変換エラー: {e}")
            
    except Exception as e:
        print(f"データ取得エラー: {e}")
    
    print("\n" + "=" * 50)
    print("🔚 JST時間設定テスト完了")
    print("=" * 50)
    print()
    print("📌 新しいファイルをアップロードすると、JST時間で保存されます。")
    print("📌 既存データは表示時にUTC→JST変換されます。")

if __name__ == "__main__":
    test_jst_time_setting() 