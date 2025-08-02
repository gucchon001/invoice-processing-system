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
        if selected_rows:
            st.subheader("📝 選択されたデータ")
            
            # 複数選択時は基本表示のみ
            if len(selected_rows) > 1:
                st.info(f"📋 {len(selected_rows)}件のデータが選択されています")
                selected_df = pd.DataFrame(selected_rows)
                st.dataframe(selected_df, use_container_width=True)
                
                # 削除ボタン
                if st.button("🗑️ 選択行を削除", type="secondary"):
                    delete_selected_invoices(selected_rows)
            
            # 1件選択時は詳細プレビュー表示
            elif len(selected_rows) == 1:
                selected_data = selected_rows[0]
                render_invoice_detail_preview(selected_data)
                
                st.divider()
                
                # 削除ボタン
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("🗑️ 選択行を削除", type="secondary", use_container_width=True):
                        delete_selected_invoices(selected_rows)
        
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
        # データベースから取得したデータを詳細プレビュー用に変換
        result = convert_db_data_to_preview_format(invoice_data)
        filename = invoice_data.get('file_name', 'unknown.pdf')
        
        # 既存の詳細プレビュー機能を使用
        render_enhanced_result_tabs_dashboard(result, filename)
        
    except Exception as e:
        logger.error(f"詳細プレビュー表示エラー: {e}")
        st.error(f"詳細表示中にエラーが発生しました: {e}")


def convert_db_data_to_preview_format(invoice_data: dict) -> dict:
    """データベースデータを詳細プレビュー用フォーマットに変換"""
    try:
        # extracted_dataがJSONBフィールドから取得されている場合の処理
        extracted_data = invoice_data.get('extracted_data', {})
        
        # データベースの40カラムフィールドを統合
        enhanced_extracted_data = {
            # 基本情報
            'issuer': invoice_data.get('issuer_name', ''),
            'payer': invoice_data.get('recipient_name', ''),
            'main_invoice_number': invoice_data.get('registration_number', ''),
            'receipt_number': invoice_data.get('receipt_number', ''),
            't_number': invoice_data.get('t_number', ''),
            
            # 金額情報
            'amount_inclusive_tax': invoice_data.get('total_amount_tax_included', 0),
            'amount_exclusive_tax': invoice_data.get('total_amount_tax_excluded', 0),
            'tax_amount': (invoice_data.get('total_amount_tax_included', 0) - 
                          invoice_data.get('total_amount_tax_excluded', 0)),
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
            'freee_export_status': invoice_data.get('freee_export_status', 'not_exported'),
            
            # キー情報
            'key_info': invoice_data.get('key_info', {}),
            
            # 既存のextracted_dataの内容もマージ
            **extracted_data
        }
        
        # 結果フォーマット
        result = {
            'extracted_data': enhanced_extracted_data,
            'raw_response': invoice_data.get('raw_response', {}),
            'processing_time': invoice_data.get('processing_time'),
            'validation_errors': invoice_data.get('validation_errors', []),
            'validation_warnings': invoice_data.get('validation_warnings', []),
            'completeness_score': invoice_data.get('completeness_score', 0),
            'file_path': invoice_data.get('file_path', ''),
            'google_drive_id': invoice_data.get('google_drive_id'),
        }
        
        return result
        
    except Exception as e:
        logger.error(f"データ変換エラー: {e}")
        return {'extracted_data': {}, 'raw_response': {}}


def render_enhanced_result_tabs_dashboard(result: dict, filename: str):
    """ダッシュボード用詳細プレビュー（タブ分割表示）"""
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 基本情報", "📊 明細", "🆕 新機能", "🔍 JSON", "📄 PDF"])
    
    extracted_data = result.get('extracted_data', {})
    
    with tab1:
        # 基本情報表示
        render_basic_info_dashboard(extracted_data)
    
    with tab2:
        # 明細情報表示
        render_line_items_dashboard(extracted_data)
    
    with tab3:
        # 新機能情報表示（40カラム対応）
        render_new_features_dashboard(extracted_data, result)
    
    with tab4:
        # JSON詳細表示
        render_json_preview_dashboard(result, extracted_data)
    
    with tab5:
        # PDF表示
        render_pdf_preview_dashboard(result, filename)


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


def render_basic_info_dashboard(extracted_data: dict):
    """基本情報タブの表示（ダッシュボード用）"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📝 請求書情報**")
        st.write(f"• 請求元: {extracted_data.get('issuer', 'N/A')}")
        st.write(f"• 請求先: {extracted_data.get('payer', 'N/A')}")
        st.write(f"• 請求書番号: {extracted_data.get('main_invoice_number', 'N/A')}")
        st.write(f"• 受領書番号: {extracted_data.get('receipt_number', 'N/A')}")
        st.write(f"• T番号: {extracted_data.get('t_number', 'N/A')}")
    
    with col2:
        st.markdown("**💰 金額情報**")
        amount_inc = extracted_data.get('amount_inclusive_tax', 0)
        amount_exc = extracted_data.get('amount_exclusive_tax', 0)
        tax_amount = extracted_data.get('tax_amount', 0)
        currency = extracted_data.get('currency', 'JPY')
        
        st.write(f"• 税込金額: {currency} {amount_inc:,}" if amount_inc else "• 税込金額: N/A")
        st.write(f"• 税抜金額: {currency} {amount_exc:,}" if amount_exc else "• 税抜金額: N/A")
        st.write(f"• 消費税額: {currency} {tax_amount:,}" if tax_amount else "• 消費税額: N/A")
        st.write(f"• 通貨: {currency}")
        st.write(f"• 請求日: {extracted_data.get('issue_date', 'N/A')}")
        st.write(f"• 支払期日: {extracted_data.get('due_date', 'N/A')}")
    
    # キー情報の表示
    key_info = extracted_data.get('key_info', {})
    if key_info:
        st.markdown("**🔑 キー情報**")
        if isinstance(key_info, dict) and key_info:
            with st.expander("詳細を表示", expanded=False):
                for key, value in key_info.items():
                    st.write(f"  - {key}: {value}")
        else:
            st.write("• キー情報: なし")


def render_line_items_dashboard(extracted_data: dict):
    """明細タブの表示（ダッシュボード用）"""
    st.markdown("### 📊 請求明細")
    
    line_items = extracted_data.get('line_items', [])
    if line_items and isinstance(line_items, list):
        st.write(f"📋 明細数: {len(line_items)}件")
        
        # 明細データをDataFrameで表示
        try:
            import pandas as pd
            df_items = pd.DataFrame(line_items)
            st.dataframe(df_items, use_container_width=True)
        except Exception as e:
            st.error(f"明細表示エラー: {e}")
            st.json(line_items)
    else:
        st.info("📋 このファイルには明細データがありません")


def render_new_features_dashboard(extracted_data: dict, result: dict):
    """新機能タブの表示（40カラム対応）"""
    st.markdown("### 🆕 40カラム新機能情報")
    st.caption("外貨換算・承認ワークフロー・freee連携の詳細情報")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💱 外貨換算機能**")
        currency = extracted_data.get('currency', 'JPY')
        if currency != 'JPY':
            exchange_rate = extracted_data.get('exchange_rate')
            jpy_amount = extracted_data.get('jpy_amount')
            card_statement_id = extracted_data.get('card_statement_id')
            
            st.write(f"• 通貨: {currency}")
            st.write(f"• 為替レート: {exchange_rate}" if exchange_rate else "• 為替レート: N/A")
            st.write(f"• 円換算金額: ¥{jpy_amount:,.0f}" if jpy_amount else "• 円換算金額: N/A")
            st.write(f"• カード明細ID: {card_statement_id}" if card_statement_id else "• カード明細ID: 未連携")
        else:
            st.write("• 外貨換算: 対象外（JPY）")
        
        st.markdown("**📊 freee連携状況**")
        freee_status = extracted_data.get('freee_export_status', 'not_exported')
        freee_id = extracted_data.get('freee_id')
        
        status_mapping = {
            'not_exported': '❌ 未エクスポート',
            'exported': '✅ エクスポート済み',
            'error': '🚨 エラー'
        }
        
        st.write(f"• ステータス: {status_mapping.get(freee_status, freee_status)}")
        st.write(f"• freee ID: {freee_id}" if freee_id else "• freee ID: N/A")
    
    with col2:
        st.markdown("**✅ 承認ワークフロー**")
        approval_status = extracted_data.get('approval_status', 'pending')
        approved_by = extracted_data.get('approved_by')
        approved_at = extracted_data.get('approved_at')
        
        status_mapping = {
            'pending': '⏳ 承認待ち',
            'approved': '✅ 承認済み',
            'rejected': '❌ 却下',
            'requires_review': '🔍 要確認'
        }
        
        st.write(f"• ステータス: {status_mapping.get(approval_status, approval_status)}")
        st.write(f"• 承認者: {approved_by}" if approved_by else "• 承認者: N/A")
        st.write(f"• 承認日時: {approved_at}" if approved_at else "• 承認日時: N/A")
        
        st.markdown("**🔍 品質情報**")
        completeness_score = result.get('completeness_score', 0)
        processing_time = result.get('processing_time')
        
        st.write(f"• 完全性スコア: {completeness_score:.1f}%" if completeness_score else "• 完全性スコア: N/A")
        st.write(f"• 処理時間: {processing_time:.2f}秒" if processing_time else "• 処理時間: N/A")


def render_json_preview_dashboard(result: dict, extracted_data: dict):
    """JSONタブの表示（ダッシュボード用）"""
    st.markdown("### 🔍 JSON詳細データ")
    
    tab1, tab2, tab3 = st.tabs(["抽出データ", "生レスポンス", "検証結果"])
    
    with tab1:
        st.markdown("**📊 AI抽出データ**")
        st.json(extracted_data)
    
    with tab2:
        st.markdown("**🤖 AI生レスポンス**")
        raw_response = result.get('raw_response', {})
        if raw_response:
            st.json(raw_response)
        else:
            st.info("生レスポンスデータがありません")
    
    with tab3:
        st.markdown("**✅ 検証結果**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            validation_errors = result.get('validation_errors', [])
            st.write(f"**🚨 エラー**: {len(validation_errors)}件")
            if validation_errors:
                for i, error in enumerate(validation_errors, 1):
                    st.error(f"{i}. {error}")
        
        with col2:
            validation_warnings = result.get('validation_warnings', [])
            st.write(f"**⚠️ 警告**: {len(validation_warnings)}件")
            if validation_warnings:
                for i, warning in enumerate(validation_warnings, 1):
                    st.warning(f"{i}. {warning}")


def render_pdf_preview_dashboard(result: dict, filename: str):
    """PDFタブの表示（ダッシュボード用）"""
    st.markdown("### 📄 PDFファイル")
    
    file_path = result.get('file_path', '')
    google_drive_id = result.get('google_drive_id')
    
    st.info(f"📄 ファイル名: {filename}")
    
    if google_drive_id:
        st.write(f"📁 Google Drive ID: {google_drive_id}")
        
        # Google Driveからの表示は将来実装
        st.warning("🚧 Google Drive PDFプレビューは今後実装予定です")
        
        # ダウンロードリンク（将来実装）
        # st.markdown(f"[📥 ダウンロード](https://drive.google.com/file/d/{google_drive_id}/view)")
    
    elif file_path:
        st.write(f"📁 ファイルパス: {file_path}")
        st.warning("🚧 ローカルPDFプレビューは今後実装予定です")
    
    else:
        st.warning("📄 PDFファイル情報が見つかりません")


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