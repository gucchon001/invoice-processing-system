"""
デバッグパネル - 開発時の状態確認用
"""
import streamlit as st
import json
from datetime import datetime

def render_debug_panel():
    """デバッグパネルをレンダリング（メイン関数）"""
    try:
        # ログイン状態を確認
        from infrastructure.auth.oauth_handler import get_current_user
        user_info = get_current_user()
        
        # ログインしていない場合はデバッグパネルを表示しない
        if not user_info:
            return
            
        show_debug_panel()
    except Exception:
        pass

def render_sidebar_debug_panel():
    """サイドバー用デバッグパネルをレンダリング"""
    try:
        # ログイン状態を確認
        from infrastructure.auth.oauth_handler import get_current_user
        user_info = get_current_user()
        
        # ログインしていない場合はデバッグパネルを表示しない
        if not user_info:
            return
            
        show_sidebar_debug_panel()
    except Exception:
        pass

def show_debug_panel():
    """デバッグ情報を表示"""
    if not st.secrets.get("app", {}).get("debug", False):
        return
        
    with st.expander("🔧 デバッグパネル", expanded=False):
        st.subheader("セッション状態")
        
        # SessionState クリーンアップボタン
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 セッション状態をクリア", key="debug_clear_session_state"):
                # デバッグ関連のキーのみクリア
                keys_to_remove = [k for k in st.session_state.keys() if k.startswith('debug_')]
                for key in keys_to_remove:
                    del st.session_state[key]
                st.success("✅ デバッグ関連セッション状態をクリアしました")
                st.rerun()
        
        with col2:
            if st.button("🗑️ 全セッション状態をクリア", key="debug_clear_all_session_state"):
                st.session_state.clear()
                st.success("✅ 全セッション状態をクリアしました")
                st.rerun()
        
        # OCRテスト結果の確認
        if "ocr_test_results" in st.session_state:
            st.write("✅ OCRテスト結果あり")
            results = st.session_state.ocr_test_results
            st.json({
                "total_files": results.get("total_files", 0),
                "files_processed": results.get("files_processed", 0),
                "files_success": results.get("files_success", 0),
                "files_failed": results.get("files_failed", 0),
                "results_count": len(results.get("results", []))
            })
        else:
            st.write("❌ OCRテスト結果なし")
        
        # データベースセッション履歴の確認
        st.subheader("データベース履歴確認")
        
        # SessionStateでボタンの重複実行を防ぐ
        if 'debug_session_check_executed' not in st.session_state:
            st.session_state.debug_session_check_executed = False
        
        if st.button("🔍 OCRテストセッション履歴を確認", key="debug_check_sessions_btn"):
            st.session_state.debug_session_check_executed = True
        
        # 結果の表示
        if st.session_state.debug_session_check_executed:
            try:
                # Service Role Keyを使用してRLS回避
                try:
                    service_key = st.secrets["database"]["supabase_service_key"]
                    supabase_url = st.secrets["database"]["supabase_url"]
                    
                    from supabase import create_client
                    service_supabase = create_client(supabase_url, service_key)
                    
                    st.info("🔑 Service Role Keyを使用してデータベース接続")
                    
                except Exception as e:
                    st.warning(f"Service Role Key使用失敗、通常キーで試行: {e}")
                    from infrastructure.database.database import get_database
                    database = get_database()
                    service_supabase = database.supabase
                
                # 現在のユーザー情報取得
                from infrastructure.auth.oauth_handler import get_current_user
                user_info = get_current_user()
                user_email = user_info.get('email', '') if user_info else ''
                
                st.write(f"**検索対象ユーザー:** {user_email}")
                
                if user_email:
                    # セッション履歴を直接取得
                    response = service_supabase.table("ocr_test_sessions").select("*").eq("created_by", user_email).order("created_at", desc=True).limit(10).execute()
                    
                    st.write(f"**クエリ結果:** レスポンス受信")
                    st.write(f"**データ数:** {len(response.data) if response.data else 0}")
                    
                    if response.data:
                        st.success(f"✅ {len(response.data)}件のセッション履歴が見つかりました")
                        
                        for i, session in enumerate(response.data):
                            with st.expander(f"セッション {i+1}: {session.get('id', 'N/A')[:8]}..."):
                                st.json(session)
                    else:
                        st.warning("⚠️ セッション履歴がありません")
                        
                        # 全セッション確認（デバッグ用）
                        st.write("**全セッション確認（デバッグ）:**")
                        all_response = service_supabase.table("ocr_test_sessions").select("*").limit(5).execute()
                        st.write(f"全セッション数: {len(all_response.data) if all_response.data else 0}")
                        
                        if all_response.data:
                            st.write("最新5件:")
                            for session in all_response.data[:5]:
                                st.write(f"- ID: {session.get('id', 'N/A')[:8]}..., 作成者: {session.get('created_by', 'N/A')}")
                else:
                    st.error("❌ ユーザー情報が取得できません")
                    
            except Exception as e:
                st.error(f"❌ データベース確認エラー: {e}")
                import traceback
                st.code(traceback.format_exc())
            
            # リセットボタン
            if st.button("🔄 結果をクリア", key="debug_clear_results"):
                st.session_state.debug_session_check_executed = False
                st.rerun()
        
        # PDFファイル一覧の確認
        if "pdf_files" in st.session_state:
            st.write(f"✅ PDFファイル一覧: {len(st.session_state.pdf_files)}件")
        else:
            st.write("❌ PDFファイル一覧なし")
        
        # 全セッション状態のキー表示
        st.write("**セッション状態キー一覧:**")
        st.write(list(st.session_state.keys()))

def show_ocr_results_debug():
    """OCRテスト結果の詳細デバッグ表示"""
    if not st.secrets.get("app", {}).get("debug", False):
        return
        
    if "ocr_test_results" not in st.session_state:
        st.warning("OCRテスト結果がセッション状態に保存されていません")
        return
        
    with st.expander("📋 OCRテスト結果詳細", expanded=False):
        results = st.session_state.ocr_test_results
        
        st.write("**テスト統計:**")
        st.json({
            "開始時刻": results.get("start_time"),
            "終了時刻": results.get("end_time"),
            "総ファイル数": results.get("total_files"),
            "処理済み": results.get("files_processed"),
            "成功": results.get("files_success"),
            "失敗": results.get("files_failed")
        })
        
        st.write("**処理結果:**")
        for i, result in enumerate(results.get("results", [])):
            with st.expander(f"ファイル {i+1}: {result.get('filename', 'unknown')}"):
                st.json(result)

def show_sidebar_debug_panel():
    """サイドバー用デバッグ情報を表示（コンパクト版）"""
    if not st.secrets.get("app", {}).get("debug", False):
        return
        
    with st.expander("🔧 デバッグパネル", expanded=False):
        # セッション状態の要約
        st.subheader("📋 セッション状態")
        
        # OCRテスト結果の確認
        if "ocr_test_results" in st.session_state:
            results = st.session_state.ocr_test_results
            st.success(f"✅ OCR結果: {results.get('files_success', 0)}件成功")
        else:
            st.warning("❌ OCRテスト結果なし")
        
        # データベース履歴の確認
        st.subheader("🗄️ データベース履歴")
        
        # SessionStateでボタンの重複実行を防ぐ
        if 'sidebar_debug_session_check_executed' not in st.session_state:
            st.session_state.sidebar_debug_session_check_executed = False
        
        if st.button("🔍 履歴確認", key="sidebar_debug_check_sessions_btn", use_container_width=True):
            st.session_state.sidebar_debug_session_check_executed = True
        
        # 結果の表示（コンパクト版）
        if st.session_state.sidebar_debug_session_check_executed:
            try:
                # Service Role Keyを使用してRLS回避
                try:
                    service_key = st.secrets["database"]["supabase_service_key"]
                    supabase_url = st.secrets["database"]["supabase_url"]
                    
                    from supabase import create_client
                    service_supabase = create_client(supabase_url, service_key)
                    
                    st.info("🔑 Service Role接続")
                    
                except Exception as e:
                    st.warning(f"Service Role失敗: {e}")
                    from infrastructure.database.database import get_database
                    database = get_database()
                    service_supabase = database.supabase
                
                # 現在のユーザー情報取得
                from infrastructure.auth.oauth_handler import get_current_user
                user_info = get_current_user()
                user_email = user_info.get('email', '') if user_info else ''
                
                if user_email:
                    # セッション履歴を直接取得
                    response = service_supabase.table("ocr_test_sessions").select("*").eq("created_by", user_email).order("created_at", desc=True).limit(5).execute()
                    
                    if response.data:
                        st.success(f"✅ {len(response.data)}件のセッション")
                        
                        # コンパクト表示
                        for i, session in enumerate(response.data):
                            session_id = session.get('id', 'N/A')[:8]
                            created_at = session.get('created_at', 'N/A')
                            st.caption(f"{i+1}. {session_id}... ({created_at[:10]})")
                    else:
                        st.warning("⚠️ セッション履歴なし")
                else:
                    st.error("❌ ユーザー情報取得失敗")
                    
            except Exception as e:
                st.error(f"❌ DB確認エラー: {str(e)[:50]}...")
            
            # リセットボタン
            if st.button("🔄 クリア", key="sidebar_debug_clear_results", use_container_width=True):
                st.session_state.sidebar_debug_session_check_executed = False
                st.rerun()
        
        # セッション状態クリア
        st.subheader("🧹 セッション管理")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Debug", key="sidebar_debug_clear_session", use_container_width=True):
                keys_to_remove = [k for k in st.session_state.keys() if k.startswith('debug_')]
                for key in keys_to_remove:
                    del st.session_state[key]
                st.success("✅ Debugクリア完了")
                st.rerun()
        
        with col2:
            if st.button("🗑️ All", key="sidebar_debug_clear_all", use_container_width=True):
                st.session_state.clear()
                st.success("✅ 全クリア完了")
                st.rerun()
        
        # キー数の表示
        st.caption(f"現在のキー数: {len(st.session_state.keys())}")