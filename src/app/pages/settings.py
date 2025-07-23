"""
設定・ダッシュボードページ - ユーザー設定、データ表示
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent  # src/ ディレクトリ
sys.path.insert(0, str(project_root))

try:
    from infrastructure.auth.oauth_handler import get_current_user
    from infrastructure.database.database import get_database
    from infrastructure.ui.aggrid_helper import get_aggrid_manager
    from utils.log_config import get_logger
    
    logger = get_logger(__name__)
    
except ImportError as e:
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.stop()


def render_dashboard_page():
    """処理状況ダッシュボード画面（ag-grid実装版）"""
    st.markdown("## 📊 処理状況ダッシュボード")
    
    st.info("📋 アップロードした請求書の処理状況を確認・編集できます。")
    
    # 現在のユーザー情報取得
    user_info = get_current_user()
    user_email = user_info.get('email', '') if user_info else ''
    
    if not user_email:
        st.error("ユーザー情報が取得できません。再ログインしてください。")
        return
    
    # データベースから請求書データを取得
    try:
        with st.spinner("データを読み込み中..."):
            database = get_database()
            invoices_data = database.get_invoices(user_email)
            
        if not invoices_data:
            st.info("📄 まだ請求書データがありません。「📤 請求書処理」からファイルをアップロードしてください。")
            
            # アップロードページへのショートカット
            if st.button("📤 請求書をアップロード", type="primary", use_container_width=True):
                st.session_state.main_menu = "📤 請求書処理"
                st.rerun()
            return
        
        # ag-gridでデータを表示・編集
        render_invoice_aggrid(invoices_data)
        
    except Exception as e:
        logger.error(f"ダッシュボードデータ取得エラー: {e}")
        st.error(f"データの取得中にエラーが発生しました: {e}")
        
        # データ更新ボタン
        if st.button("🔄 再試行", use_container_width=True):
            st.rerun()


def render_invoice_aggrid(invoices_data):
    """ag-gridを使用した請求書データの表示・編集"""
    st.markdown("### 📋 請求書一覧 (ag-grid)")
    
    try:
        # ag-gridマネージャー取得
        aggrid_manager = get_aggrid_manager()
        
        if not aggrid_manager:
            st.error("ag-gridマネージャーの初期化に失敗しました")
            return
        
        # データフレーム変換
        df = pd.DataFrame(invoices_data)
        
        if df.empty:
            st.info("表示するデータがありません")
            return
        
        # ag-gridでデータ表示
        response = aggrid_manager.display_invoice_grid(df)
        
        # 選択された行の処理
        selected_rows = response['selected_rows']
        if selected_rows:
            st.subheader("📝 選択されたデータ")
            selected_df = pd.DataFrame(selected_rows)
            st.dataframe(selected_df, use_container_width=True)
            
            # 削除ボタン
            if st.button("🗑️ 選択行を削除", type="secondary"):
                delete_selected_invoices(selected_rows)
        
        # データ更新の処理
        updated_data = response['data']
        if updated_data is not None and not updated_data.equals(df):
            st.info("データが更新されました")
            # データベースに保存
            update_invoices_in_database(updated_data)
            
    except Exception as e:
        logger.error(f"ag-grid表示エラー: {e}")
        st.error(f"データ表示中にエラーが発生しました: {e}")


def delete_selected_invoices(selected_rows):
    """選択された請求書を削除"""
    try:
        database = get_database()
        
        for row in selected_rows:
            invoice_id = row.get('id')
            if invoice_id:
                database.delete_invoice(invoice_id)
        
        st.success(f"✅ {len(selected_rows)}件の請求書を削除しました")
        st.rerun()
        
    except Exception as e:
        logger.error(f"請求書削除エラー: {e}")
        st.error(f"削除中にエラーが発生しました: {e}")


def update_invoices_in_database(updated_data):
    """更新されたデータをデータベースに保存"""
    try:
        database = get_database()
        
        # データフレームから辞書リストに変換
        records = updated_data.to_dict('records')
        
        for record in records:
            invoice_id = record.get('id')
            if invoice_id:
                database.update_invoice(invoice_id, record)
        
        st.success("✅ データの更新が完了しました")
        
    except Exception as e:
        logger.error(f"データ更新エラー: {e}")
        st.error(f"データ更新中にエラーが発生しました: {e}")


def render_settings_page():
    """メール設定画面"""
    st.markdown("## ⚙️ メール設定")
    
    st.info("📧 通知設定を管理できます。")
    
    # 通知設定
    st.markdown("### 📬 通知設定")
    
    notify_success = st.checkbox(
        "✅ 処理完了時にメールで通知する",
        value=True,
        help="請求書の AI 処理が完了した際にメール通知を送信します",
        key="email_notify_success"
    )
    
    notify_error = st.checkbox(
        "❌ エラー発生時にメールで通知する",
        value=True,
        help="処理中にエラーが発生した際にメール通知を送信します",
        key="email_notify_error"
    )
    
    # 保存ボタン
    if st.button("💾 設定を保存", type="primary", use_container_width=True):
        save_notification_settings(notify_success, notify_error)


def save_notification_settings(notify_success, notify_error):
    """通知設定を保存"""
    try:
        # 現在のユーザー情報取得
        user_info = get_current_user()
        user_email = user_info.get('email', '') if user_info else ''
        
        if not user_email:
            st.error("ユーザー情報が取得できません")
            return
        
        # データベースに設定を保存
        database = get_database()
        settings = {
            'user_email': user_email,
            'notify_success': notify_success,
            'notify_error': notify_error
        }
        
        # 設定保存（データベーススキーマに応じて実装）
        # database.save_user_settings(settings)
        
        st.success("✅ 設定を保存しました")
        
        # TODO: 実際の設定保存処理を実装
        logger.info(f"通知設定保存: {user_email} - 成功通知:{notify_success}, エラー通知:{notify_error}")
        
    except Exception as e:
        logger.error(f"設定保存エラー: {e}")
        st.error(f"設定の保存中にエラーが発生しました: {e}") 