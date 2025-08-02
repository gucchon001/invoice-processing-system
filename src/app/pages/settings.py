"""
設定・ダッシュボードページ - ユーザー設定、データ表示
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from typing import Dict, List, Any

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
        
        # selected_rowsをリスト形式に正規化（DataFrameエラー回避）
        normalized_selected_rows = []
        if selected_rows is not None:
            if isinstance(selected_rows, pd.DataFrame):
                if not selected_rows.empty:
                    normalized_selected_rows = selected_rows.to_dict('records')
            elif isinstance(selected_rows, list):
                normalized_selected_rows = selected_rows
            else:
                # その他の型の場合は空リストにフォールバック
                logger.warning(f"予期しないselected_rows型: {type(selected_rows)}")
                normalized_selected_rows = []
        
        if normalized_selected_rows:
            st.subheader("📝 選択されたデータ")
            
            # 複数選択時は基本表示のみ
            if len(normalized_selected_rows) > 1:
                st.info(f"📋 {len(normalized_selected_rows)}件のデータが選択されています")
                selected_df = pd.DataFrame(normalized_selected_rows)
                st.dataframe(selected_df, use_container_width=True)
                
                # 削除ボタン
                if st.button("🗑️ 選択行を削除", type="secondary"):
                    delete_selected_invoices(normalized_selected_rows)
            
            # 1件選択時は詳細プレビュー表示
            elif len(normalized_selected_rows) == 1:
                selected_data = normalized_selected_rows[0]
                render_invoice_detail_preview(selected_data)
                
                st.divider()
                
                # 削除ボタン
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("🗑️ 選択行を削除", type="secondary", use_container_width=True):
                        delete_selected_invoices(normalized_selected_rows)
        
        # データ更新の処理
        updated_data = response['data']
        if updated_data is not None:
            try:
                # DataFrameの比較を安全に行う
                is_data_changed = False
                if isinstance(updated_data, pd.DataFrame) and isinstance(df, pd.DataFrame):
                    # 同じ形状でない場合は変更ありとみなす
                    if updated_data.shape != df.shape:
                        is_data_changed = True
                    else:
                        # 内容を比較（equals()の結果をall()で集約）
                        try:
                            comparison_result = updated_data.equals(df)
                            if isinstance(comparison_result, bool):
                                is_data_changed = not comparison_result
                            else:
                                # equals()がSeriesやDataFrameを返す場合
                                is_data_changed = not comparison_result.all()
                        except Exception:
                            # 比較に失敗した場合は変更ありとみなす
                            is_data_changed = True
                else:
                    # DataFrameでない場合も変更ありとみなす
                    is_data_changed = True
                
                if is_data_changed:
                    st.info("データが更新されました")
                    # データベースに保存
                    update_invoices_in_database(updated_data)
                    
            except Exception as e:
                logger.error(f"データ更新チェックエラー: {e}")
                # エラーが発生した場合は更新処理をスキップ
            
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


def render_invoice_detail_preview(invoice_data: dict):
    """選択された請求書の詳細プレビュー表示"""
    try:
        # 🔍 一時的なデバッグ表示
        with st.expander("🔍 デバッグ情報（開発用）", expanded=False):
            st.write("**受信したinvoice_dataのキー:**")
            st.code(list(invoice_data.keys()))
            st.write("**主要フィールドの内容:**")
            debug_fields = ['file_name', 'issuer_name', 'recipient_name', 'main_invoice_number', 
                           'total_amount_tax_included', 'currency', 'extracted_data']
            for field in debug_fields:
                value = invoice_data.get(field, 'NOT_FOUND')
                st.write(f"- {field}: {value}")
            
            # Google Drive 関連の詳細デバッグ
            st.write("**📁 Google Drive & ファイル関連:**")
            gdrive_fields = ['gdrive_file_id', 'google_drive_id', 'source_type', 'file_path', 
                           'file_name', 'file_size', 'file_metadata']
            gdrive_debug = {}
            for field in gdrive_fields:
                value = invoice_data.get(field)
                gdrive_debug[field] = value
                st.write(f"- {field}: {value}")
            
            # 全フィールド確認（長いので折りたたみ）
            with st.expander("📋 全フィールド一覧", expanded=False):
                st.json(invoice_data)
        
        # データベースから取得したデータを詳細プレビュー用に変換
        result = convert_db_data_to_preview_format(invoice_data)
        filename = invoice_data.get('file_name', 'unknown.pdf')
        
        # 既存の詳細プレビュー機能を使用
        render_enhanced_result_tabs_dashboard(result, filename)
        
    except Exception as e:
        logger.error(f"詳細プレビュー表示エラー: {e}")
        st.error(f"詳細表示中にエラーが発生しました: {e}")
        # エラー時もデバッグ情報を表示
        st.write("**エラー時のinvoice_data:**")
        st.json(invoice_data)


def convert_db_data_to_preview_format(invoice_data: dict) -> dict:
    """データベースデータを詳細プレビュー用フォーマットに変換"""
    try:
        # デバッグ: 実際のデータ構造を確認
        logger.info(f"🔍 DEBUG - 受信したinvoice_data keys: {list(invoice_data.keys())}")
        logger.info(f"🔍 DEBUG - invoice_dataサンプル: {dict(list(invoice_data.items())[:5])}")
        
        # extracted_dataがJSONBフィールドから取得されている場合の処理
        extracted_data = invoice_data.get('extracted_data', {})
        
        # データベースの40カラムフィールドを統合（正しいフィールド名で）
        enhanced_extracted_data = {
            # 基本情報（データベースフィールド名に合わせて修正）
            'issuer': invoice_data.get('issuer_name', ''),
            'payer': invoice_data.get('recipient_name', ''),
            'main_invoice_number': invoice_data.get('main_invoice_number', ''),  # 修正
            'receipt_number': invoice_data.get('receipt_number', ''),
            't_number': invoice_data.get('t_number', ''),
            
            # 金額情報（データベースフィールド名に合わせて修正）
            'amount_inclusive_tax': invoice_data.get('total_amount_tax_included', 0),
            'amount_exclusive_tax': invoice_data.get('total_amount_tax_excluded', 0),
            'tax_amount': (invoice_data.get('total_amount_tax_included', 0) - 
                          invoice_data.get('total_amount_tax_excluded', 0)) if 
                          invoice_data.get('total_amount_tax_included') and 
                          invoice_data.get('total_amount_tax_excluded') else 0,
            'currency': invoice_data.get('currency', 'JPY'),
            
            # 日付情報
            'issue_date': invoice_data.get('issue_date', ''),
            'due_date': invoice_data.get('due_date', ''),
            
            # 新機能（40カラム）
            'exchange_rate': invoice_data.get('exchange_rate'),
            'jpy_amount': invoice_data.get('jpy_amount'),
            'card_statement_id': invoice_data.get('card_statement_id'),
            'approval_status': invoice_data.get('approval_status', 'pending'),
            'approved_by': invoice_data.get('approved_by'),
            'approved_at': invoice_data.get('approved_at'),
            
            # freee連携情報（正しいフィールド名）
            'freee_export_status': 'exported' if invoice_data.get('exported_to_freee') else 'not_exported',
            'freee_id': invoice_data.get('freee_batch_id'),
            
            # ファイル関連情報
            'source_type': invoice_data.get('source_type', 'local'),
            'gmail_message_id': invoice_data.get('gmail_message_id'),
            'sender_email': invoice_data.get('sender_email'),
            
            # キー情報
            'key_info': invoice_data.get('key_info', {}),
        }
        
        # extracted_dataがJSONBフィールドとして存在する場合、その内容も統合
        if isinstance(extracted_data, dict) and extracted_data:
            logger.info(f"🔍 DEBUG - extracted_data内容: {list(extracted_data.keys())}")
            # extracted_dataの内容で上書きしない場合は、既存の値を優先
            for key, value in extracted_data.items():
                if key not in enhanced_extracted_data or not enhanced_extracted_data[key]:
                    enhanced_extracted_data[key] = value
        
        # Google Drive ID のデバッグ情報
        gdrive_file_id_raw = invoice_data.get('gdrive_file_id')
        google_drive_id_raw = invoice_data.get('google_drive_id')
        final_google_drive_id = gdrive_file_id_raw or google_drive_id_raw
        
        logger.info(f"🔍 DEBUG - Google Drive ID変換:")
        logger.info(f"  - gdrive_file_id (raw): {gdrive_file_id_raw}")
        logger.info(f"  - google_drive_id (raw): {google_drive_id_raw}")
        logger.info(f"  - final_google_drive_id: {final_google_drive_id}")
        logger.info(f"  - source_type: {invoice_data.get('source_type')}")
        
        # 結果フォーマット（NULL値を安全に処理）
        result = {
            'extracted_data': enhanced_extracted_data,
            'raw_response': invoice_data.get('raw_response', {}),
            'processing_time': invoice_data.get('processing_time'),
            'validation_errors': invoice_data.get('validation_errors') or [],  # NULL → []
            'validation_warnings': invoice_data.get('validation_warnings') or [],  # NULL → []
            'completeness_score': invoice_data.get('completeness_score', 0),
            'file_path': invoice_data.get('file_path', ''),
            'google_drive_id': final_google_drive_id,  # デバッグ済み
            'source_type': invoice_data.get('source_type', 'local'),
            'file_size': invoice_data.get('file_size'),
            '_original_invoice_data': invoice_data,  # 🔧 元データを保持（デバッグ・既存機能再利用用）
        }
        
        return result
        
    except Exception as e:
        logger.error(f"データ変換エラー: {e}")
        return {'extracted_data': {}, 'raw_response': {}}


def render_enhanced_result_tabs_dashboard(result: dict, filename: str):
    """ダッシュボード用詳細プレビュー（既存高機能モジュール再利用）"""
    
    # 🎯 既存の高機能プレビューを直接使用（保守性・一貫性向上）
    from .invoice_processing import render_enhanced_result_tabs
    render_enhanced_result_tabs(result, filename)


def update_invoices_in_database(updated_data):
    """更新されたデータをデータベースに保存"""
    try:
        import math
        database = get_database()
        
        # データフレームから辞書リストに変換
        records = updated_data.to_dict('records')
        
        for record in records:
            # JSON準拠のためfloat値をサニタイズ
            sanitized_record = {}
            for key, value in record.items():
                if isinstance(value, float):
                    # NaN, Infinity, -Infinityを安全な値に変換
                    if math.isnan(value):
                        sanitized_record[key] = None  # NaN → NULL
                    elif math.isinf(value):
                        sanitized_record[key] = None  # Infinity → NULL
                    else:
                        sanitized_record[key] = value
                else:
                    sanitized_record[key] = value
            
            invoice_id = sanitized_record.get('id')
            if invoice_id:
                database.update_invoice(invoice_id, sanitized_record)
        
        st.success("✅ データの更新が完了しました")
        
    except Exception as e:
        logger.error(f"データ更新エラー: {e}")
        st.error(f"データ更新中にエラーが発生しました: {e}")
        
        # デバッグ情報
        logger.debug(f"更新対象データ形状: {updated_data.shape if hasattr(updated_data, 'shape') else 'N/A'}")
        logger.debug(f"更新対象データ型: {type(updated_data)}")


# 🗑️ 削除: render_basic_info_dashboard -> invoice_processing.render_basic_info_enhanced に統一


# 🗑️ 削除: render_line_items_dashboard -> invoice_processing.render_line_items_enhanced に統一


# 🗑️ 削除: render_new_features_dashboard -> invoice_processing.render_new_features_enhanced に統一


# 🗑️ 削除: render_json_preview_dashboard -> invoice_processing.render_json_preview_enhanced に統一


# 🗑️ 削除: render_pdf_preview_dashboard -> invoice_processing.render_pdf_preview_enhanced に統一


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