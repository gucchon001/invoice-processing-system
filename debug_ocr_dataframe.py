import streamlit as st
import pandas as pd
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="OCR DataFrame エラーデバッグ", layout="wide")

st.title("🔍 OCR DataFrame エラーデバッグ")

st.markdown("### 📋 STEP 1: 各モジュールの個別テスト")

# STEP 1: データベース接続テスト
try:
    from infrastructure.database.database import get_database
    
    st.markdown("#### 🗄️ データベース接続テスト")
    
    if st.button("データベース接続テスト"):
        try:
            database = get_database()
            connection_test = database.test_connection()
            st.success(f"✅ データベース接続: {connection_test}")
        except Exception as e:
            st.error(f"❌ データベース接続エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # STEP 2: 請求書データ取得テスト
    st.markdown("#### 📄 請求書データ取得テスト")
    
    if st.button("請求書データ取得テスト"):
        try:
            database = get_database()
            user_email = "test@example.com"
            
            st.write("**請求書データ取得中...**")
            invoices_data = database.get_invoices(user_email)
            
            st.write(f"**取得結果の型:** {type(invoices_data)}")
            st.write(f"**データ件数:** {len(invoices_data) if invoices_data else 0}")
            
            # DataFrame条件判定安全性テスト
            try:
                result_len = len(invoices_data) > 0
                st.success(f"✅ len(invoices_data) > 0: {result_len}")
            except Exception as e:
                st.error(f"❌ len()でエラー: {e}")
            
            # DataFrameかどうかのチェック
            if hasattr(invoices_data, 'to_dict'):
                st.warning("⚠️ 結果がDataFrameです！これがエラーの原因です")
                st.write("**DataFrameの内容:**")
                st.dataframe(invoices_data)
                
                # 安全に変換
                invoices_data = invoices_data.to_dict('records')
                st.success("✅ リストに変換しました")
            
            if invoices_data:
                st.write("**最初のデータサンプル:**")
                st.json(invoices_data[0] if invoices_data else {})
                
        except Exception as e:
            st.error(f"❌ 請求書データ取得エラー: {e}")
            import traceback
            st.code(traceback.format_exc())

except ImportError as e:
    st.error(f"❌ データベースモジュールインポートエラー: {e}")

# STEP 3: OCRテストマネージャーテスト
try:
    from utils.ocr_test_helper import OCRTestManager
    from infrastructure.storage.google_drive_helper import get_google_drive
    from infrastructure.ai.gemini_helper import get_gemini_api
    
    st.markdown("#### 🤖 OCRテストマネージャーテスト")
    
    if st.button("OCRテストマネージャー初期化テスト"):
        try:
            drive_manager = get_google_drive()
            gemini_manager = get_gemini_api()
            database_manager = get_database()
            
            ocr_test_manager = OCRTestManager(drive_manager, gemini_manager, database_manager)
            st.success("✅ OCRテストマネージャー初期化成功")
            
            # セッション履歴読み込みテスト
            st.write("**セッション履歴読み込みテスト**")
            user_email = "test@example.com"
            
            sessions = ocr_test_manager.load_sessions_from_supabase(user_email)
            st.write(f"**セッション履歴の型:** {type(sessions)}")
            st.write(f"**セッション件数:** {len(sessions) if sessions else 0}")
            
            # DataFrame条件判定安全性テスト
            try:
                result_len = len(sessions) > 0
                st.success(f"✅ len(sessions) > 0: {result_len}")
            except Exception as e:
                st.error(f"❌ len()でエラー: {e}")
            
            # DataFrameかどうかのチェック
            if hasattr(sessions, 'to_dict'):
                st.warning("⚠️ セッション履歴がDataFrameです！これがエラーの原因です")
                st.write("**DataFrameの内容:**")
                st.dataframe(sessions)
                
        except Exception as e:
            st.error(f"❌ OCRテストマネージャーエラー: {e}")
            import traceback
            st.code(traceback.format_exc())

except ImportError as e:
    st.error(f"❌ OCRテストモジュールインポートエラー: {e}")

# STEP 4: Supabaseレスポンス直接テスト
try:
    st.markdown("#### 🔍 Supabase レスポンス直接テスト")
    
    if st.button("Supabaseレスポンス直接テスト"):
        try:
            from supabase import create_client
            
            supabase_url = st.secrets["database"]["supabase_url"]
            supabase_key = st.secrets["database"]["supabase_anon_key"]
            
            supabase = create_client(supabase_url, supabase_key)
            
            # 直接クエリを実行
            response = supabase.table("ocr_test_sessions").select("*").limit(5).execute()
            
            st.write(f"**レスポンスの型:** {type(response)}")
            st.write(f"**レスポンス.dataの型:** {type(response.data)}")
            st.write(f"**データ件数:** {len(response.data) if response.data else 0}")
            
            # DataFrame条件判定テスト
            data = response.data
            try:
                # 危険なテスト
                if data:
                    st.success("✅ if data: は成功（リストの場合）")
                else:
                    st.info("📋 データが空です")
            except Exception as e:
                st.error(f"❌ if data: でエラー発生: {e}")
                st.error("🚨 これがDataFrameエラーの原因です！")
                
                # DataFrameかどうか確認
                if hasattr(data, 'to_dict'):
                    st.warning("⚠️ response.dataがDataFrameです！")
                    st.write("**DataFrameの内容:**")
                    st.dataframe(data)
                
        except Exception as e:
            st.error(f"❌ Supabaseレスポンステストエラー: {e}")
            import traceback
            st.code(traceback.format_exc())

except Exception as e:
    st.error(f"❌ Supabaseテストでエラー: {e}")

# STEP 5: ag-gridヘルパーテスト
try:
    from infrastructure.ui.aggrid_helper import get_aggrid_manager
    
    st.markdown("#### 📊 ag-gridヘルパーテスト")
    
    if st.button("ag-gridヘルパーテスト"):
        try:
            aggrid_manager = get_aggrid_manager()
            st.success("✅ ag-gridマネージャー取得成功")
            
            # テストデータでag-grid表示
            test_data = [
                {"ID": 1, "名前": "テスト1", "値": 100},
                {"ID": 2, "名前": "テスト2", "値": 200}
            ]
            
            df_test = pd.DataFrame(test_data)
            
            st.write("**テストデータでag-grid表示**")
            grid_response = aggrid_manager.create_data_grid(
                df_test,
                editable=False,
                selection_mode="single",
                height=200
            )
            
            # 選択行テスト
            selected_rows = aggrid_manager.get_selected_rows(grid_response)
            st.write(f"**選択行の型:** {type(selected_rows)}")
            st.write(f"**選択行数:** {len(selected_rows) if selected_rows else 0}")
            
        except Exception as e:
            st.error(f"❌ ag-gridヘルパーエラー: {e}")
            import traceback
            st.code(traceback.format_exc())

except ImportError as e:
    st.error(f"❌ ag-gridモジュールインポートエラー: {e}")

st.markdown("### 📋 デバッグ結果")
st.info("""
**チェックポイント:**
1. データベース接続は正常か？
2. 請求書データ取得時にDataFrameが返されていないか？
3. セッション履歴読み込み時にDataFrameが返されていないか？
4. Supabaseの生レスポンスがDataFrameになっていないか？
5. ag-gridヘルパーは正常に動作するか？

**エラーパターン:**
- "The truth value of a DataFrame is ambiguous" が発生 → DataFrameを条件判定している
- どの段階でエラーが出るかで原因を特定
""") 