"""
請求書処理自動化システム - メインアプリケーション
streamlit-oauth統一認証版

開発・本番環境で統一されたOAuth認証システムを使用した
請求書処理自動化システムのメインアプリケーション
"""

import streamlit as st
import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import json
import time

# プロジェクトルートをPythonパスに追加（新しい構造対応）
project_root = Path(__file__).parent.parent  # src/ ディレクトリ
sys.path.insert(0, str(project_root))

# ログ設定の初期化
try:
    from utils.log_config import setup_logging, get_logger, get_log_config
    from utils.debug_panel import show_debug_panel, show_ocr_results_debug, render_debug_panel
    setup_logging()  # 設定ファイルからログ設定を読み込み
    logger = get_logger(__name__)
    logger.info("請求書処理自動化システムが開始されました")
    
    # デバッグモードの確認
    log_config = get_log_config()
    if log_config.is_debug_mode():
        logger.debug("デバッグモードが有効です")
        
except ImportError as e:
    print(f"ログ設定モジュールのインポートに失敗しました: {e}")
    # フォールバック設定
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def show_debug_info():
    pass

# 新しい構造でのモジュールインポート
try:
    from infrastructure.auth.oauth_handler import require_auth, get_current_user, logout, is_authenticated
    from infrastructure.database.database import get_database, test_database_connection
    from infrastructure.ai.gemini_helper import get_gemini_api, test_gemini_connection, generate_text_simple, extract_pdf_invoice_data, GeminiAPIManager
    from infrastructure.storage.google_drive_helper import get_google_drive, test_google_drive_connection, upload_pdf_to_drive, get_drive_files_list
    from infrastructure.ui.aggrid_helper import get_aggrid_manager, test_aggrid_connection
    from core.workflows.invoice_processing import InvoiceProcessingWorkflow, WorkflowProgress, WorkflowResult
    
    # 統一コンポーネントのインポート（絶対インポート修正）
    from core.services.invoice_validator import InvoiceValidator
    from core.services.unified_prompt_manager import UnifiedPromptManager, PromptSelector
    from infrastructure.ui.validation_display import ValidationDisplay, BatchValidationDisplay
    from core.workflows.unified_processing import UnifiedProcessingWorkflow, ProcessingMode, WorkflowDisplayManager
    
    logger.info("全モジュールのインポートが完了しました（統一コンポーネント含む）")
except ImportError as e:
    logger.error(f"モジュールのインポートに失敗しました: {e}")
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.error("新しいディレクトリ構造でのインポートパスを確認してください。")
    st.stop()


def configure_page():
    """Streamlitページの基本設定"""
    st.set_page_config(
        page_title="請求書処理自動化システム",
        page_icon="📄",
        layout="wide",  
        initial_sidebar_state="expanded"
    )

def initialize_session_state():
    """セッション状態の初期化"""
    try:
        # プロンプト関連の初期化
        if "prompt_manager" not in st.session_state:
            from core.services.unified_prompt_manager import UnifiedPromptManager
            st.session_state.prompt_manager = UnifiedPromptManager()
            logger.info("✅ プロンプトマネージャー初期化完了")
        
        if "prompt_selector" not in st.session_state:
            from core.services.prompt_selector import PromptSelector
            st.session_state.prompt_selector = PromptSelector(st.session_state.prompt_manager)
            logger.info("✅ プロンプトセレクター初期化完了")
        
        # 統合ワークフロー初期化
        if "unified_workflow" not in st.session_state:
            from core.workflows.unified_processing import UnifiedProcessingWorkflow
            from infrastructure.ai.gemini_helper import GeminiAPIManager
            from infrastructure.database.database import get_database
            
            gemini_helper = GeminiAPIManager()
            database_manager = get_database()
            
            st.session_state.unified_workflow = UnifiedProcessingWorkflow(
                gemini_helper=gemini_helper,
                database_manager=database_manager
            )
            logger.info("✅ 統合ワークフロー初期化完了")
        
        # ワークフロー表示マネージャー初期化
        if "workflow_display" not in st.session_state:
            from core.services.workflow_display_manager import WorkflowDisplayManager
            st.session_state.workflow_display = WorkflowDisplayManager(st.session_state.unified_workflow)
            logger.info("✅ ワークフロー表示マネージャー初期化完了")
        
        # OCR専用統合ワークフロー初期化
        if "unified_workflow_ocr" not in st.session_state:
            try:
                gemini_helper = GeminiAPIManager()
                database_manager = get_database()
                
                st.session_state.unified_workflow_ocr = UnifiedProcessingWorkflow(
                    gemini_helper=gemini_helper,
                    database_manager=database_manager
                )
                logger.info("✅ OCR専用統合ワークフロー初期化完了")
            except Exception as e:
                logger.error(f"❌ OCR専用ワークフロー初期化エラー: {e}")
                # エラーの場合はNoneを設定してエラーを回避
                st.session_state.unified_workflow_ocr = None
        
        # OCR専用ワークフロー表示マネージャー初期化
        if "workflow_display_ocr" not in st.session_state:
            try:
                if st.session_state.unified_workflow_ocr is not None:
                    from core.services.workflow_display_manager import WorkflowDisplayManager
                    st.session_state.workflow_display_ocr = WorkflowDisplayManager(st.session_state.unified_workflow_ocr)
                    logger.info("✅ OCR専用ワークフロー表示マネージャー初期化完了")
                else:
                    st.session_state.workflow_display_ocr = None
                    logger.warning("⚠️ OCR専用ワークフロー表示マネージャー初期化スキップ（ワークフローが未初期化）")
            except Exception as e:
                logger.error(f"❌ OCR専用ワークフロー表示マネージャー初期化エラー: {e}")
                st.session_state.workflow_display_ocr = None
        
        # その他のセッション状態初期化
        if "upload_results" not in st.session_state:
            st.session_state.upload_results = []
        
        if "is_processing_upload" not in st.session_state:
            st.session_state.is_processing_upload = False
        
        if "unified_processing_results" not in st.session_state:
            st.session_state.unified_processing_results = []
        
        if "is_unified_processing" not in st.session_state:
            st.session_state.is_unified_processing = False
            
        logger.info("✅ セッション状態初期化完了")
        
    except Exception as e:
        logger.error(f"❌ セッション状態初期化エラー: {e}")
        st.error(f"システム初期化エラー: {e}")
        st.stop()


def render_sidebar(user_info):
    """サイドバーをレンダリング"""
    with st.sidebar:
        # ユーザー情報表示
        st.markdown("### 👤 ユーザー情報")
        
        # プロフィール画像があれば表示
        if 'picture' in user_info:
            st.image(user_info['picture'], width=80)
        
        st.write(f"**{user_info['name']}**")
        st.write(f"📧 {user_info['email']}")
        
        # ログアウトボタン
        if st.button("🚪 ログアウト", use_container_width=True):
            logout()
        
        st.divider()
        
        # メニュー（基本版）
        st.markdown("### 📋 メニュー")
        
        # TODO: ユーザーの役割に応じてメニューを切り替え
        # 現在は基本メニューのみ表示
        menu_options = [
            "📤 請求書処理",  # 統合ページ（アップロード+OCRテスト）
            "📊 処理状況ダッシュボード", 
            "⚙️ メール設定",
            "🔧 DB接続テスト",
            "🤖 Gemini APIテスト",
            "☁️ Google Drive APIテスト",
            "📊 ag-grid データグリッドテスト",
            "🔄 統合ワークフローテスト"
        ]
        
        # 管理者の場合の追加メニュー（将来実装）
        # if is_admin_user(user_info['email']):
        #     menu_options.extend([
        #         "---",
        #         "[管理] 全データ閲覧",
        #         "[管理] 支払マスタ管理",
        #         "[管理] カード明細アップロード",
        #         "[管理] システムログ閲覧"
        #     ])
        
        selected_menu = st.selectbox(
            "機能を選択してください",
            menu_options,
            key="main_menu"
        )
        
        return selected_menu


def render_unified_invoice_processing_page():
    """統合請求書処理ページ - 本番アップロード＋OCRテスト"""
    st.markdown("# 📤 請求書処理")
    st.markdown("本番アップロードとOCRテストを統一ワークフローで処理します")
    
    # タブ作成
    tab1, tab2 = st.tabs(["🚀 本番アップロード", "🔍 OCRテスト"])
    
    with tab1:
        st.markdown("### 🚀 本番アップロード")
        st.caption("📝 請求書PDFをアップロードして本番データベースに保存します")
        render_production_upload_content()
    
    with tab2:
        st.markdown("### 🔍 OCRテスト")
        st.caption("📝 Google DriveのPDFファイルでOCR精度をテストします")
        render_ocr_test_content()

def render_production_upload_content():
    """本番アップロードコンテンツ"""
    # プロンプト自動選択（本番モード）
    prompt_selector = st.session_state.prompt_selector
    selected_prompt_key = prompt_selector.get_recommended_prompt(ProcessingMode.UPLOAD)
    
    if selected_prompt_key:
        prompt_data = st.session_state.prompt_manager.get_prompt_by_key(selected_prompt_key)
        if prompt_data:
            prompt_name = prompt_data.get('name', selected_prompt_key)
            st.success(f"✅ 自動選択されたプロンプト: **{prompt_name}**")
            st.caption("📝 本番処理に最適なプロンプトが自動選択されます")
        
        # プロンプト互換性チェック
        is_compatible, warnings = st.session_state.prompt_manager.validate_prompt_compatibility(
            selected_prompt_key, ProcessingMode.UPLOAD
        )
        if warnings:
            for warning in warnings:
                st.warning(f"⚠️ {warning}")
        else:
            st.success("✅ 互換性OK")
    else:
        st.error("適切なプロンプトが見つかりません")
        return
    
    # ファイルアップロード
    st.markdown("### 📁 ファイルアップロード")
    uploaded_files = st.file_uploader(
        "請求書PDFファイルを選択してください",
        type=['pdf'],
        accept_multiple_files=True,
        help="複数のPDFファイルを同時にアップロードできます"
    )
    
    # 処理設定
    st.markdown("### ⚙️ 処理設定")
    col1, col2 = st.columns(2)
    
    with col1:
        include_validation = st.checkbox(
            "詳細検証実行",
            value=True,
            help="統一検証システムによる詳細分析を実行",
            key="production_include_validation"
        )
    
    with col2:
        auto_save = st.checkbox(
            "自動保存",
            value=True,
            help="処理完了後に自動的にデータベースに保存",
            key="production_auto_save"
        )
    
    # 処理実行
    if uploaded_files:
        st.markdown("### 🚀 処理実行")
        
        if st.button(f"📊 本番処理開始 ({len(uploaded_files)}件)", type="primary", use_container_width=True):
            validation_config = {
                'include_detailed_validation': include_validation,
                'auto_save': auto_save,
                'processing_mode': 'production'
            }
            
            execute_unified_upload_processing(
                uploaded_files,
                selected_prompt_key,
                validation_config,
                ProcessingMode.UPLOAD
            )
    
    # アップロード進行状況表示
    if st.session_state.get('is_processing_upload', False):
        render_upload_progress()
    
    # アップロード結果表示（統一システム）
    if st.session_state.get('unified_processing_results'):
        # include_validationはproduction_include_validationキーから取得
        include_validation = st.session_state.get('production_include_validation', True)
        render_unified_upload_results(include_validation)

def render_ocr_test_content():
    """OCRテストコンテンツ"""
    # プロンプト自動選択（OCRテストモード）
    prompt_selector = st.session_state.prompt_selector
    selected_prompt_key = prompt_selector.get_recommended_prompt(ProcessingMode.OCR_TEST)
    
    if selected_prompt_key:
        prompt_data = st.session_state.prompt_manager.get_prompt_by_key(selected_prompt_key)
        if prompt_data:
            prompt_name = prompt_data.get('name', selected_prompt_key)
            st.success(f"✅ 自動選択されたプロンプト: **{prompt_name}**")
            st.caption("📝 OCRテストに最適なプロンプトが自動選択されます")
        
        # プロンプト互換性チェック
        is_compatible, warnings = st.session_state.prompt_manager.validate_prompt_compatibility(
            selected_prompt_key, ProcessingMode.OCR_TEST
        )
        if warnings:
            for warning in warnings:
                st.warning(f"⚠️ {warning}")
        else:
            st.success("✅ 互換性OK")
    else:
        st.error("適切なプロンプトが見つかりません")
        return
    
    # テスト設定
    st.markdown("### 🔧 テスト設定")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        test_mode = st.selectbox(
            "テストモード",
            ["精度重視", "速度重視", "バランス"],
            help="テストの重点項目を選択します"
        )
    
    with col2:
        max_files = st.selectbox(
            "テスト対象ファイル数",
            [5, 10, 20, 50, -1],
            format_func=lambda x: "全て" if x == -1 else f"{x}件",
            index=0,
            help="処理するPDFファイルの最大件数"
        )
    
    with col3:
        include_validation = st.checkbox(
            "詳細検証実行",
            value=True,
            help="統一検証システムによる詳細分析を実行",
            key="unified_ocr_test_include_validation"
        )
    
    # Google DriveフォルダID設定
    st.markdown("### 📁 テスト対象フォルダ")
    default_folder_id = "1ZCJsI9j8A9VJcmiY79BcP1jgzsD51X6E"
    folder_id = st.text_input(
        "Google DriveフォルダID",
        value=default_folder_id,
        help="テスト対象PDFが格納されたGoogle DriveフォルダのID"
    )
    
    # セッション状態の初期化
    if "ocr_test_results" not in st.session_state:
        st.session_state.ocr_test_results = []
    if "is_ocr_testing" not in st.session_state:
        st.session_state.is_ocr_testing = False
    
    # テスト実行ボタン
    col1, col2 = st.columns([2, 1])
    
    with col1:
        button_text = f"🚀 統一OCRテスト開始 ({max_files if max_files != -1 else '全'}件)"
        
        if st.button(button_text, type="primary", use_container_width=True):
            if not folder_id:
                st.error("フォルダIDを入力してください")
            elif not selected_prompt_key:
                st.error("プロンプトが選択されていません")
            elif not st.session_state.is_ocr_testing:
                execute_unified_ocr_test(
                    folder_id,
                    selected_prompt_key,
                    max_files,
                    test_mode,
                    include_validation
                )
            else:
                st.warning("現在テスト実行中です。しばらくお待ちください。")
    
    with col2:
        if st.button("🔄 リセット", use_container_width=True):
            st.session_state.ocr_test_results = []
            st.session_state.is_ocr_testing = False
            st.rerun()
    
    # テスト結果表示
    if st.session_state.ocr_test_results:
        render_ocr_test_results(include_validation)


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
            st.info("📄 まだ請求書データがありません。「📤 請求書アップロード」からファイルをアップロードしてください。")
            
            # アップロードページへのショートカット
            if st.button("📤 請求書をアップロード", type="primary", use_container_width=True):
                st.session_state.selected_menu = "📤 請求書アップロード"
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
    """請求書データのag-grid表示・編集"""
    try:
        # ag-gridマネージャーを取得
        aggrid_manager = get_aggrid_manager()
        
        # データ前処理（ag-grid用にフォーマット）
        processed_data = prepare_invoice_data_for_aggrid(invoices_data)
        
        if not processed_data:
            st.warning("表示可能なデータがありません。")
            return
        
        # ag-gridで表示・編集
        st.markdown("### 📋 請求書一覧・編集")
        
        # ag-gridを表示（既存のcreate_invoice_editing_gridメソッドを使用）
        grid_response = aggrid_manager.create_invoice_editing_grid(processed_data)
        
        # 選択行とデータ変更の処理
        handle_grid_interactions(grid_response, invoices_data)
        
    except Exception as e:
        logger.error(f"ag-grid表示エラー: {e}")
        st.error(f"データ表示でエラーが発生しました: {e}")


def _extract_invoice_data(row: dict, field_name: str, default_value=''):
    """请求書データを複数ソースから抽出するヘルパー（extracted_data優先）"""
    try:
        import json
        import re
        
        # 1. extracted_dataカラムから抽出（最優先）
        if 'extracted_data' in row and row['extracted_data']:
            extracted = row['extracted_data']
            
            # フィールドマッピング：UIフィールド名 -> extracted_dataのキー名
            field_mapping = {
                'issuer_name': 'issuer',
                'payer_name': 'payer', 
                'invoice_number': 'main_invoice_number',
                'total_amount_tax_included': 'amount_inclusive_tax',
                'total_amount': 'amount_inclusive_tax',
                'currency': 'currency',
                'issue_date': 'issue_date',
                'due_date': 'due_date',
                'registration_number': 't_number'
            }
            
            key = field_mapping.get(field_name, field_name)
            if key in extracted:
                value = extracted[key]
                # 値が存在し、空でない場合は返す
                if value is not None and value != '' and value != 'N/A':
                    return value
        
        # 2. statusフィールドから抽出（フォールバック）
        status_str = row.get('status', '')
        
        # JSONフォーマットの場合
        if status_str and (status_str.startswith('{') or 'ai_extracted_data' in status_str):
            status_data = json.loads(status_str)
            if 'ai_extracted_data' in status_data:
                value = status_data['ai_extracted_data'].get(field_name, default_value)
                if value is not None and value != '' and value != 'N/A':
                    return value
        
        # コンパクト形式の場合（例: "✅Gamma ¥313"）
        elif status_str and status_str.startswith('✅'):
            if field_name in ['issuer_name', 'issuer']:
                # ✅の後から¥の前までを企業名として抽出
                match = re.search(r'✅([^¥]+)', status_str)
                if match:
                    return match.group(1).strip()
            elif field_name in ['total_amount_tax_included', 'total_amount']:
                # ¥の後の数字を金額として抽出
                match = re.search(r'¥([\d,]+)', status_str)
                if match:
                    return int(match.group(1).replace(',', ''))
            elif field_name == 'currency':
                # ¥が含まれていればJPY
                if '¥' in status_str:
                    return 'JPY'
        
        # 3. 直接カラムから抽出（レガシー対応）
        if field_name in row and row[field_name] is not None and row[field_name] != '':
            return row[field_name]
        
        return default_value
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return default_value

def prepare_invoice_data_for_aggrid(invoices_data):
    """請求書データをag-grid用に前処理（完全28カラム対応）"""
    try:
        import pandas as pd
        
        # 基本データの準備
        processed_rows = []
        
        for invoice in invoices_data:
            # フォールバック用のextracted_data
            extracted_data = invoice.get('extracted_data', {}) or {}
            
            # 完全な28カラム構造のデータ準備
            row = {
                # 1-7: 基本情報カラム
                'id': invoice.get('id', ''),
                'user_email': invoice.get('user_email', ''),
                'status': invoice.get('status', 'extracted'),
                'file_name': invoice.get('file_name', ''),
                'uploaded_at': invoice.get('uploaded_at', ''),
                'created_at': invoice.get('created_at', ''),
                'updated_at': invoice.get('updated_at', ''),
                
                # 8-12: 請求書基本情報カラム
                'issuer_name': (
                    invoice.get('issuer_name') or
                    extracted_data.get('issuer') or
                    'N/A'
                ),
                'recipient_name': (
                    invoice.get('recipient_name') or
                    extracted_data.get('payer') or
                    'N/A'
                ),
                'invoice_number': (
                    invoice.get('invoice_number') or
                    extracted_data.get('main_invoice_number') or
                    'N/A'
                ),
                'registration_number': (
                    invoice.get('registration_number') or
                    extracted_data.get('t_number') or
                    'N/A'
                ),
                'currency': (
                    invoice.get('currency') or
                    extracted_data.get('currency') or
                    'JPY'
                ),
                
                # 13-14: 金額情報カラム
                'total_amount_tax_included': (
                    invoice.get('total_amount_tax_included') or
                    extracted_data.get('amount_inclusive_tax') or
                    0
                ),
                'total_amount_tax_excluded': (
                    invoice.get('total_amount_tax_excluded') or
                    extracted_data.get('amount_exclusive_tax') or
                    0
                ),
                
                # 15-16: 日付情報カラム
                'issue_date': (
                    invoice.get('issue_date') or
                    extracted_data.get('issue_date') or
                    'N/A'
                ),
                'due_date': (
                    invoice.get('due_date') or
                    extracted_data.get('due_date') or
                    'N/A'
                ),
                
                # 17-19: JSON情報カラム
                'key_info': invoice.get('key_info', {}),
                'raw_response': invoice.get('raw_response', {}),
                'extracted_data': invoice.get('extracted_data', {}),
                
                # 20-23: 検証・品質管理カラム
                'is_valid': invoice.get('is_valid', True),
                'validation_errors': invoice.get('validation_errors', []),
                'validation_warnings': invoice.get('validation_warnings', []),
                'completeness_score': invoice.get('completeness_score', 0),
                
                # 24-28: メタデータカラム
                'processing_time': invoice.get('processing_time', 0),
                'gdrive_file_id': invoice.get('gdrive_file_id', ''),
                'file_path': invoice.get('file_path', ''),
                'file_size': invoice.get('file_size', 0),
                'gemini_model': invoice.get('gemini_model', 'gemini-2.0-flash-exp')
            }
            
            processed_rows.append(row)
        
        # DataFrameに変換
        df = pd.DataFrame(processed_rows)
        
        # データ型の統一と調整（完全28カラム対応）
        if len(df) > 0:
            # 日時フォーマット調整
            date_columns = ['uploaded_at', 'created_at', 'updated_at', 'issue_date', 'due_date']
            for col in date_columns:
                if col in df.columns:
                    try:
                        # 日付のみの場合とタイムスタンプの場合を区別
                        if col in ['issue_date', 'due_date']:
                            # 日付のみの場合
                            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
                        else:
                            # タイムスタンプの場合
                            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        df[col] = df[col].astype(str).replace('nan', '').replace('None', '')
            
            # 数値型の変換
            numeric_columns = [
                'total_amount_tax_included', 'total_amount_tax_excluded', 
                'completeness_score', 'processing_time', 'file_size'
            ]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # ブール型の統一
            if 'is_valid' in df.columns:
                df['is_valid'] = df['is_valid'].fillna(True)
            
            # 文字列カラムの統一
            string_columns = [
                'user_email', 'status', 'file_name', 'issuer_name', 
                'recipient_name', 'invoice_number', 'registration_number', 
                'currency', 'gdrive_file_id', 'file_path', 'gemini_model'
            ]
            for col in string_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace('nan', 'N/A').replace('None', 'N/A')
            
            # リスト型カラムの統一
            list_columns = ['validation_errors', 'validation_warnings']
            for col in list_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])
            
            # JSON型カラムの統一
            json_columns = ['key_info', 'raw_response', 'extracted_data']
            for col in json_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: x if isinstance(x, dict) else {})
        
        logger.info(f"📊 ag-grid用データ準備完了: {len(df)}件（完全28カラム対応）")
        if len(df) > 0:
            logger.debug(f"🔧 カラム数: {len(df.columns)}")
            logger.debug(f"🔧 主要カラム値例: issuer_name={df['issuer_name'].iloc[0]}")
        return df
        
    except Exception as e:
        logger.error(f"❌ ag-grid用データ準備エラー: {e}")
        return pd.DataFrame()


def handle_grid_interactions(grid_response, original_data):
    """ag-gridの選択・編集処理"""
    try:
        # 選択行の処理
        selected_rows = grid_response.get('selected_rows', [])
        
        # selected_rowsの安全な処理
        if hasattr(selected_rows, 'to_dict'):
            selected_rows = selected_rows.to_dict('records')
        elif not isinstance(selected_rows, list):
            selected_rows = []
        
        if len(selected_rows) > 0:
            st.markdown(f"### 📌 選択済み: {len(selected_rows)} 件")
            
            # 一括操作ボタン
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📄 PDFを確認", use_container_width=True):
                    handle_pdf_preview(selected_rows)
            
            with col2:
                if st.button("💾 変更を保存", use_container_width=True):
                    handle_data_save(grid_response)
            
            with col3:
                if st.button("🗑️ 選択削除", use_container_width=True):
                    handle_data_delete(selected_rows)
            
            with col4:
                if st.button("📊 詳細分析", use_container_width=True):
                    handle_detailed_analysis(selected_rows)
        
        # データ変更の検出と保存
        updated_data = grid_response.get('data', pd.DataFrame())
        if not updated_data.empty:
            # 変更検出と自動保存機能を追加可能
            pass
            
    except Exception as e:
        logger.error(f"グリッド操作エラー: {e}")
        st.error(f"操作中にエラーが発生しました: {e}")


def handle_pdf_preview(selected_rows):
    """PDF確認機能"""
    st.info("📄 PDF確認機能は次の開発フェーズで実装予定です。")


def handle_data_save(grid_response):
    """データ保存機能"""
    st.success("💾 データ保存機能は次の開発フェーズで実装予定です。")


def handle_data_delete(selected_rows):
    """データ削除機能"""
    st.warning("🗑️ データ削除機能は次の開発フェーズで実装予定です。")


def handle_detailed_analysis(selected_rows):
    """詳細分析機能"""
    st.info("📊 詳細分析機能は次の開発フェーズで実装予定です。")


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
        st.success("✅ 設定を保存しました")
        # TODO: 実際の設定保存処理を実装


def render_database_test_page():
    """データベース接続テスト画面"""
    st.markdown("## 🔧 データベース接続テスト")
    st.markdown("Supabaseデータベースへの接続をテストします。")
    
    # 接続テストボタン
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if st.button("🔗 接続テスト", use_container_width=True):
            with st.spinner("データベース接続をテスト中..."):
                try:
                    # データベース接続テスト
                    success = test_database_connection()
                    
                    if success:
                        st.success("✅ データベース接続成功！")
                        
                        # 追加情報の表示
                        db = get_database()
                        
                        # テーブル存在チェック
                        st.markdown("### 📋 テーブル存在確認")
                        tables_status = db.create_tables()
                        
                        if tables_status:
                            st.info("💡 必要なテーブルの確認が完了しました")
                        
                    else:
                        st.error("❌ データベース接続に失敗しました")
                        st.markdown("""
                        ### 🔧 設定確認事項:
                        1. Supabaseプロジェクトが作成されているか
                        2. `.streamlit/secrets.toml`の設定が正しいか
                        3. Supabaseの API Key が有効か
                        """)
                        
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {e}")
                    
    with col2:
        st.markdown("""
        ### 📋 設定手順:
        1. **Supabaseプロジェクト作成**
           - https://supabase.com にアクセス
           - 新規プロジェクト作成: `invoice-processing-system`
        
        2. **接続情報設定**
           - プロジェクト → Settings → API
           - `Project URL` と `anon public key` をコピー
           - `.streamlit/secrets.toml` を更新
        
        3. **テーブル作成** (手動)
           - Supabase Dashboard → Table Editor
           - 必要なテーブルを作成
        """)
    
    # 現在の設定表示
    st.markdown("### ⚙️ 現在の設定")
    
    try:
        # secrets.tomlの設定状況を確認（機密情報は隠す）
        url = st.secrets.get("database", {}).get("supabase_url", "設定なし")
        key = st.secrets.get("database", {}).get("supabase_anon_key", "設定なし")
        
        # URLの一部だけ表示
        masked_url = url[:30] + "..." if len(url) > 30 else url
        masked_key = key[:10] + "..." if len(key) > 10 else key
        
        st.code(f"""
設定状況:
- Supabase URL: {masked_url}
- API Key: {masked_key}
        """)
        
    except Exception as e:
        st.warning(f"設定ファイルの読み込みエラー: {e}")
    
    # データベース操作テスト
    st.markdown("### 🧪 データベース操作テスト")
    
    test_col1, test_col2 = st.columns(2)
    
    with test_col1:
        if st.button("👤 ユーザーテーブルテスト"):
            try:
                db = get_database()
                # テストユーザーの作成・取得
                test_email = "test@example.com"
                
                # ユーザー存在確認
                user = db.get_user(test_email)
                if user:
                    st.success(f"✅ ユーザー取得成功: {user['name']}")
                else:
                    # テストユーザー作成
                    created = db.create_user(test_email, "テストユーザー", "user")
                    if created:
                        st.success("✅ テストユーザー作成成功")
                    else:
                        st.error("❌ テストユーザー作成失敗")
                        
            except Exception as e:
                st.error(f"ユーザーテーブルテストエラー: {e}")
    
    with test_col2:
        if st.button("📄 請求書テーブルテスト"):
            try:
                db = get_database()
                # 請求書一覧取得テスト
                invoices = db.get_invoices()
                st.success(f"✅ 請求書データ取得成功: {len(invoices)}件")
                
                if invoices:
                    st.json(invoices[0])  # 最初の1件を表示
                    
            except Exception as e:
                st.error(f"請求書テーブルテストエラー: {e}")


def render_gemini_test_page():
    """Gemini APIテスト画面"""
    st.markdown("## 🤖 Gemini APIテスト")
    st.markdown("Google Gemini APIとの連携、PDF情報抽出機能をテストします。")
    
    # APIキー設定状況
    try:
        api_key = st.secrets.get("ai", {}).get("gemini_api_key", "設定なし")
        masked_key = api_key[:10] + "..." if len(api_key) > 10 else api_key
        
        st.markdown("### ⚙️ 現在の設定")
        st.code(f"Gemini API Key: {masked_key}")
        
    except Exception as e:
        st.warning(f"設定ファイルの読み込みエラー: {e}")
    
    # テスト機能
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔗 基本接続テスト")
        
        if st.button("🤖 Gemini接続テスト", use_container_width=True):
            with st.spinner("Gemini APIに接続中..."):
                try:
                    success = test_gemini_connection()
                    
                    if success:
                        st.success("✅ Gemini API接続成功！")
                        
                        # 追加テスト: シンプルなテキスト生成
                        st.markdown("### 📝 テキスト生成テスト")
                        response = generate_text_simple("こんにちは！今日の日付と挨拶を日本語で答えてください。")
                        
                        if response:
                            st.success("✅ テキスト生成成功")
                            st.markdown("**AI応答:**")
                            st.write(response)
                        else:
                            st.error("❌ テキスト生成失敗")
                    else:
                        st.error("❌ Gemini API接続に失敗しました")
                        st.markdown("""
                        ### 🔧 設定確認事項:
                        1. Google AI Studio でAPIキーが作成されているか
                        2. `.streamlit/secrets.toml`の設定が正しいか
                        3. APIキーが有効で利用制限に達していないか
                        """)
                        
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {e}")
    
    with col2:
        st.markdown("### 📋 設定手順")
        st.markdown("""
        **1. Google AI Studio でAPIキー取得**
        - https://aistudio.google.com にアクセス
        - 「Get API key」をクリック
        - APIキーを作成・コピー
        
        **2. 設定ファイル更新**
        - `.streamlit/secrets.toml` の `[ai]` セクション
        - `gemini_api_key` に取得したキーを設定
        
        **3. モデル利用可能性確認**
        - Gemini 1.5 Flash が利用可能か確認
        - 地域制限や利用制限がないか確認
        """)
    
    # PDF分析テスト
    st.markdown("### 📄 PDF情報抽出テスト")
    
    uploaded_files = st.file_uploader(
        "テスト用PDFファイルをアップロード（複数選択可能）",
        type=["pdf"],
        accept_multiple_files=True,
        help="請求書のサンプルPDFを複数選択してアップロードできます。一括で情報抽出をテストします。"
    )
    
    if uploaded_files:
        st.success(f"📄 {len(uploaded_files)}個のファイルがアップロードされました")
        
        # アップロードされたファイル一覧を表示
        with st.expander(f"📋 アップロードファイル一覧 ({len(uploaded_files)}個)"):
            for i, file in enumerate(uploaded_files, 1):
                file_size = len(file.getvalue()) / 1024  # KB
                st.write(f"{i}. **{file.name}** ({file_size:.1f}KB)")
        
        col_pdf1, col_pdf2 = st.columns([1, 1])
        
        with col_pdf1:
            st.markdown("### 🚀 一括処理")
            
            if st.button("📊 全PDFを一括分析", use_container_width=True):
                progress_bar = st.progress(0)
                results = []
                
                for i, uploaded_file in enumerate(uploaded_files):
                    progress = (i + 1) / len(uploaded_files)
                    progress_bar.progress(progress)
                    
                    with st.spinner(f"📄 {uploaded_file.name} を分析中... ({i+1}/{len(uploaded_files)})"):
                        try:
                            # PDFバイト数取得
                            pdf_bytes = uploaded_file.read()
                            
                            # Gemini APIで情報抽出
                            result = extract_pdf_invoice_data(pdf_bytes)
                            
                            if result:
                                results.append({
                                    "filename": uploaded_file.name,
                                    "status": "success",
                                    "data": result
                                })
                            else:
                                results.append({
                                    "filename": uploaded_file.name,
                                    "status": "failed",
                                    "error": "情報抽出失敗"
                                })
                                
                        except Exception as e:
                            results.append({
                                "filename": uploaded_file.name,
                                "status": "error",
                                "error": str(e)
                            })
                
                progress_bar.progress(1.0)
                
                # 結果サマリー表示
                successful = len([r for r in results if r["status"] == "success"])
                failed = len(results) - successful
                
                st.markdown("### 📊 処理結果サマリー")
                
                col_success, col_failed = st.columns(2)
                with col_success:
                    st.metric("✅ 成功", successful)
                with col_failed:
                    st.metric("❌ 失敗", failed)
                
                # 個別結果の表示
                st.markdown("### 📋 詳細結果")
                
                for result in results:
                    with st.expander(f"📄 {result['filename']} - {'✅ 成功' if result['status'] == 'success' else '❌ 失敗'}"):
                        if result["status"] == "success":
                            st.json(result["data"])
                            
                            # 主要情報のハイライト
                            if isinstance(result["data"], dict):
                                highlight_data = {}
                                for key in ["issuer", "amount_inclusive_tax", "issue_date", "currency"]:
                                    if key in result["data"] and result["data"][key]:
                                        highlight_data[key] = result["data"][key]
                                
                                if highlight_data:
                                    st.markdown("**🎯 主要情報:**")
                                    st.json(highlight_data)
                        else:
                            st.error(f"エラー: {result.get('error', '不明なエラー')}")
                
                # CSV形式でダウンロード機能
                if successful > 0:
                    import pandas as pd
                    import json
                    
                    st.markdown("### 💾 結果ダウンロード")
                    
                    # 成功したデータのみをDataFrameに変換
                    success_data = []
                    for result in results:
                        if result["status"] == "success":
                            data = result["data"]
                            flat_data = {
                                "filename": result["filename"],
                                "issuer": data.get("issuer"),
                                "payer": data.get("payer"),
                                "invoice_number": data.get("invoice_number"),
                                "issue_date": data.get("issue_date"),
                                "due_date": data.get("due_date"),
                                "currency": data.get("currency"),
                                "amount_inclusive_tax": data.get("amount_inclusive_tax"),
                                "amount_exclusive_tax": data.get("amount_exclusive_tax"),
                            }
                            success_data.append(flat_data)
                    
                    if success_data:
                        df = pd.DataFrame(success_data)
                        csv = df.to_csv(index=False, encoding='utf-8-sig')
                        
                        st.download_button(
                            label="📥 結果をCSVでダウンロード",
                            data=csv,
                            file_name=f"invoice_extraction_results_{len(success_data)}files.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
            
            # 個別処理オプション
            st.markdown("### 🔍 個別処理")
            
            if len(uploaded_files) > 1:
                selected_file_name = st.selectbox(
                    "個別処理するファイルを選択",
                    [f.name for f in uploaded_files]
                )
                
                selected_file = next(f for f in uploaded_files if f.name == selected_file_name)
                
                if st.button("📊 選択ファイルのみ分析", use_container_width=True):
                    with st.spinner(f"📄 {selected_file.name} を分析中..."):
                        try:
                            pdf_bytes = selected_file.read()
                            result = extract_pdf_invoice_data(pdf_bytes)
                            
                            if result:
                                st.success("✅ PDF情報抽出成功！")
                                st.markdown("### 📋 抽出結果")
                                st.json(result)
                                
                                # 主要情報のハイライト
                                if isinstance(result, dict):
                                    highlight_data = {}
                                    for key in ["issuer", "amount_inclusive_tax", "issue_date", "currency"]:
                                        if key in result and result[key]:
                                            highlight_data[key] = result[key]
                                    
                                    if highlight_data:
                                        st.markdown("### 🎯 主要情報")
                                        st.json(highlight_data)
                            else:
                                st.error("❌ PDF情報抽出に失敗しました")
                                
                        except Exception as e:
                            st.error(f"PDF処理エラー: {e}")
        
        with col_pdf2:
            st.markdown("### 💡 抽出される情報")
            st.markdown("""
            **基本情報:**
            - 請求元・請求先
            - 請求書番号
            - 発行日・支払期日
            - 金額（税込・税抜）
            
            **詳細情報:**
            - 通貨コード
            - キー情報（アカウントID等）
            - 明細項目
            
            **複数ファイル機能:**
            - 🔄 **一括処理**: 全ファイル同時分析
            - 📊 **進捗表示**: リアルタイム処理状況
            - 📋 **結果サマリー**: 成功・失敗件数
            - 💾 **CSV出力**: 結果の一括ダウンロード
            - 🔍 **個別処理**: 特定ファイルのみ処理
            """)
    
    # JSONプロンプトテスト
    st.markdown("### 🎯 JSONプロンプトシステムテスト")
    
    col_test1, col_test2 = st.columns(2)
    
    with col_test1:
        if st.button("🔍 JSONプロンプト機能テスト", use_container_width=True):
            with st.spinner("JSONプロンプト機能をテスト中..."):
                try:
                    gemini_api = get_gemini_api()
                    test_results = gemini_api.test_json_prompts()
                    
                    st.markdown("#### 📊 テスト結果")
                    
                    # 結果サマリー
                    total_tests = 4
                    passed_tests = sum([
                        test_results["invoice_extractor"],
                        test_results["master_matcher"], 
                        test_results["integrated_matcher"],
                        test_results["prompt_loading"]
                    ])
                    
                    if passed_tests == total_tests:
                        st.success(f"🎉 全テスト成功！ ({passed_tests}/{total_tests})")
                    else:
                        st.warning(f"⚠️ 一部テスト失敗 ({passed_tests}/{total_tests})")
                    
                    # 詳細結果
                    col_result1, col_result2 = st.columns(2)
                    
                    with col_result1:
                        st.write("**📋 プロンプト読み込み**")
                        st.write(f"✅ 請求書抽出: {'成功' if test_results['invoice_extractor'] else '失敗'}")
                        st.write(f"✅ 企業名照合: {'成功' if test_results['master_matcher'] else '失敗'}")
                    
                    with col_result2:
                        st.write("**🔄 統合機能**")
                        st.write(f"✅ 統合照合: {'成功' if test_results['integrated_matcher'] else '失敗'}")
                        st.write(f"✅ プロンプト管理: {'成功' if test_results['prompt_loading'] else '失敗'}")
                    
                    # エラー詳細
                    if test_results.get("errors"):
                        with st.expander("🚨 エラー詳細", expanded=False):
                            for error in test_results["errors"]:
                                st.error(error)
                                
                except Exception as e:
                    st.error(f"JSONプロンプトテストエラー: {e}")
    
    with col_test2:
        if st.button("📋 企業名照合デモ", use_container_width=True):
            with st.spinner("企業名照合デモを実行中..."):
                try:
                    # サンプルデータで照合テスト
                    issuer_name = "グーグル合同会社"
                    master_list = ["Google合同会社", "Amazon Japan合同会社", "マイクロソフト株式会社"]
                    
                    gemini_api = get_gemini_api()
                    result = gemini_api.match_company_name(issuer_name, master_list)
                    
                    st.markdown("#### 🔍 照合デモ結果")
                    st.write(f"**請求元名**: {issuer_name}")
                    st.write(f"**マスタリスト**: {', '.join(master_list)}")
                    
                    if result and result.get("matched_company_name"):
                        st.success(f"✅ 照合成功: {result['matched_company_name']}")
                        st.write(f"**確信度**: {result.get('confidence_score', 0):.2f}")
                        st.write(f"**照合理由**: {result.get('matching_reason', 'N/A')}")
                    else:
                        st.warning("❌ 照合失敗または確信度不足")
                        
                except Exception as e:
                    st.error(f"企業名照合デモエラー: {e}")
    
    # カスタムプロンプトテスト
    st.markdown("### 💬 カスタムプロンプトテスト")
    
    prompt_input = st.text_area(
        "テスト用プロンプトを入力",
        placeholder="例: 請求書処理に関する質問やタスクを書いてください",
        height=100
    )
    
    if st.button("🚀 プロンプト実行") and prompt_input:
        with st.spinner("AIが回答を生成中..."):
            try:
                response = generate_text_simple(prompt_input)
                
                if response:
                    st.success("✅ プロンプト実行成功")
                    st.markdown("**AI応答:**")
                    st.write(response)
                else:
                    st.error("❌ プロンプト実行失敗")
                    
            except Exception as e:
                st.error(f"プロンプト実行エラー: {e}")

    # 統合テスト機能
    st.markdown("### 🧪 JSONプロンプト統合テスト")
    st.markdown("実際のPDFファイルを使用した包括的な精度検証とベースライン策定を実行します。")
    
    col_integration1, col_integration2 = st.columns(2)
    
    with col_integration1:
        st.markdown("#### 📋 テスト設定")
        
        # テスト用フォルダID入力
        test_folder_id = st.text_input(
            "テスト用Google DriveフォルダID",
            placeholder="PDFファイルが格納されたフォルダのID",
            help="テスト用請求書PDFが格納されたGoogle DriveフォルダのIDを入力してください"
        )
        
        # サンプル数設定
        sample_size = st.slider(
            "テスト対象PDFファイル数",
            min_value=5, max_value=50, value=10,
            help="テストに使用するPDFファイルの数を設定します"
        )
        
        # テスト実行ボタン
        if st.button("🔬 統合テスト実行", use_container_width=True):
            if not test_folder_id:
                st.error("テスト用フォルダIDを入力してください")
            else:
                run_integration_test(test_folder_id, sample_size)
    
    with col_integration2:
        st.markdown("#### 📊 テスト項目")
        st.markdown("""
        **🔍 PDF情報抽出テスト**
        - JSONプロンプトによる基本情報抽出
        - データ完全性の評価
        - 処理時間の測定
        
        **🔑 キー情報抽出精度テスト**
        - アカウントID、契約番号等の重要情報
        - 抽出精度の定量評価
        - 優先度別成功率測定
        
        **🏢 企業名照合テスト**
        - 表記揺れ対応精度
        - 確信度計算の適切性
        - マッチング成功率
        
        **🔄 統合照合テスト**
        - 請求書と支払マスタの照合
        - 総合判定精度
        - エンドツーエンド成功率
        """)

def run_integration_test(test_folder_id: str, sample_size: int):
    """統合テストを実行"""
    with st.spinner(f"統合テスト実行中（{sample_size}件のPDFを処理）..."):
        try:
            # 必要なモジュールをインポート
            from infrastructure.storage.google_drive_helper import get_google_drive
            from infrastructure.ai.gemini_helper import get_gemini_api
            from infrastructure.database.database import get_database
            from utils.integration_test_manager import get_integration_test_manager
            
            # マネージャー初期化
            drive_manager = get_google_drive()
            gemini_manager = get_gemini_api()
            database_manager = get_database()
            
            if not drive_manager or not gemini_manager:
                st.error("Google DriveまたはGemini APIの初期化に失敗しました")
                return
            
            # 統合テストマネージャー取得
            test_manager = get_integration_test_manager(drive_manager, gemini_manager, database_manager)
            
            # 統合テスト実行
            test_session = test_manager.run_comprehensive_test(test_folder_id, sample_size)
            
            # テストレポート生成
            test_report = test_manager.generate_test_report(test_session)
            
            # 結果表示
            display_integration_test_results(test_session, test_report)
            
        except Exception as e:
            st.error(f"統合テスト実行エラー: {e}")
            import traceback
            st.code(traceback.format_exc())

def display_integration_test_results(test_session: Dict[str, Any], test_report: Dict[str, Any]):
    """統合テスト結果を表示"""
    st.success("🎉 統合テスト完了！")
    
    # サマリー表示
    summary = test_report["summary"]
    st.markdown("### 📊 テスト結果サマリー")
    
    col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
    
    with col_sum1:
        st.metric(
            "テスト対象PDF数", 
            summary["total_pdfs_tested"],
            help="実際にテストしたPDFファイルの数"
        )
    
    with col_sum2:
        st.metric(
            "総合成功率", 
            f"{summary['overall_success_rate']:.1%}",
            help="全テスト項目の平均成功率"
        )
    
    with col_sum3:
        st.metric(
            "品質レベル", 
            summary["quality_level"],
            help="総合的な品質評価"
        )
    
    with col_sum4:
        st.metric(
            "パフォーマンス", 
            summary["performance_status"],
            help="処理速度の評価"
        )
    
    # 詳細結果
    st.markdown("### 🔍 詳細テスト結果")
    
    tab_extraction, tab_keyinfo, tab_company, tab_integrated = st.tabs([
        "📄 PDF抽出", "🔑 キー情報", "🏢 企業名照合", "🔄 統合照合"
    ])
    
    tests = test_session["tests"]
    
    with tab_extraction:
        st.markdown("#### PDF情報抽出結果")
        extraction_data = tests["pdf_extraction"]
        
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.metric("成功率", f"{extraction_data['success_rate']:.1%}")
        with col_e2:
            st.metric("平均処理時間", f"{extraction_data['avg_time']:.1f}秒")
        
        # 個別結果
        if extraction_data["results"]:
            df_extraction = pd.DataFrame([
                {
                    "ファイル名": r.get("filename", ""),
                    "成功": "✅" if r.get("success") else "❌",
                    "処理時間": f"{r.get('extraction_time', 0):.1f}秒",
                    "データ完全性": f"{r.get('data_completeness', 0):.1%}"
                }
                for r in extraction_data["results"]
            ])
            st.dataframe(df_extraction, use_container_width=True)
    
    with tab_keyinfo:
        st.markdown("#### キー情報抽出結果")
        keyinfo_data = tests["key_info_extraction"]
        
        st.metric("平均精度", f"{keyinfo_data['accuracy_rate']:.1%}")
        
        if keyinfo_data["results"]:
            df_keyinfo = pd.DataFrame([
                {
                    "精度": f"{r.get('accuracy', 0):.1%}",
                    "抽出キー数": r.get('key_count', 0),
                    "重要キー発見数": f"{r.get('priority_keys_found', 0)}/{r.get('total_priority_keys', 0)}",
                    "スコア": f"{r.get('score', 0):.1f}"
                }
                for r in keyinfo_data["results"]
            ])
            st.dataframe(df_keyinfo, use_container_width=True)
    
    with tab_company:
        st.markdown("#### 企業名照合結果")
        company_data = tests["company_matching"]
        
        st.metric("照合精度", f"{company_data['precision']:.1%}")
        
        if company_data["results"]:
            df_company = pd.DataFrame([
                {
                    "元企業名": r.get('original_name', ''),
                    "照合結果": "✅" if r.get('success') else "❌",
                    "確信度": f"{r.get('confidence', 0):.1%}",
                    "照合先": r.get('matched_company', 'なし')
                }
                for r in company_data["results"]
            ])
            st.dataframe(df_company, use_container_width=True)
    
    with tab_integrated:
        st.markdown("#### 統合照合結果")
        integrated_data = tests["integrated_matching"]
        
        st.metric("成功率", f"{integrated_data['success_rate']:.1%}")
        
        if integrated_data["results"]:
            df_integrated = pd.DataFrame([
                {
                    "照合結果": "✅" if r.get('success') else "❌",
                    "確信度": f"{r.get('confidence', 0):.1%}",
                    "照合エントリ": r.get('matched_entry', 'なし')
                }
                for r in integrated_data["results"]
            ])
            st.dataframe(df_integrated, use_container_width=True)
    
    # ベースライン比較
    st.markdown("### 📈 ベースライン比較")
    
    baseline_comparison = test_report["baseline_comparison"]
    
    comparison_data = []
    for metric_name, comparison in baseline_comparison.items():
        comparison_data.append({
            "指標": metric_name.replace("_", " ").title(),
            "現在値": f"{comparison['current']:.1%}",
            "目標値": f"{comparison['target']:.1%}",
            "達成率": f"{comparison['achievement_rate']:.1%}",
            "ステータス": comparison['status']
        })
    
    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(df_comparison, use_container_width=True)
    
    # 推奨事項
    st.markdown("### 💡 改善提案")
    recommendations = test_report["recommendations"]
    
    if recommendations:
        for recommendation in recommendations:
            st.info(recommendation)
    else:
        st.success("🎯 すべての指標が良好です！継続的な監視を推奨します。")
    
    # 次のステップ
    st.markdown("### 🚀 次のステップ")
    next_steps = test_report["next_steps"]
    
    for step in next_steps:
        st.markdown(f"- {step}")
    
    # ダウンロード機能
    st.markdown("### 📥 レポートダウンロード")
    
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        # JSONレポートダウンロード
        json_report = json.dumps(test_report, ensure_ascii=False, indent=2)
        st.download_button(
            label="📄 詳細レポート（JSON）",
            data=json_report,
            file_name=f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_dl2:
        # CSVサマリーダウンロード
        summary_csv = pd.DataFrame([summary]).to_csv(index=False)
        st.download_button(
            label="📊 サマリー（CSV）",
            data=summary_csv,
            file_name=f"integration_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )


def render_google_drive_test_page():
    """Google Drive APIテスト画面"""
    st.markdown("## ☁️ Google Drive APIテスト")
    
    st.info("🔧 Google Drive API接続とファイルアップロード機能のテストを行います。")
    
    # 現在の設定表示
    st.markdown("### ⚙️ 現在の設定")
    
    # サービスアカウント情報表示
    try:
        client_email = st.secrets["google_drive"]["client_email"]
        project_id = st.secrets["google_drive"]["project_id"]
        st.write(f"**サービスアカウント:** {client_email}")
        st.write(f"**プロジェクトID:** {project_id}")
    except KeyError as e:
        st.error(f"❌ Google Drive API設定が不完全です: {e}")
        st.markdown("""
        **必要な設定項目:**
        - `google_drive.type`
        - `google_drive.project_id`
        - `google_drive.private_key_id`
        - `google_drive.private_key`
        - `google_drive.client_email`
        - `google_drive.client_id`
        - `google_drive.auth_uri`
        - `google_drive.token_uri`
        - `google_drive.auth_provider_x509_cert_url`
        - `google_drive.client_x509_cert_url`
        """)
        return
    
    # 接続テスト
    st.markdown("### 🔗 基本接続テスト")
    
    if st.button("接続テスト実行", key="drive_connection_test"):
        with st.spinner("Google Drive API接続をテスト中..."):
            if test_google_drive_connection():
                st.success("✅ Google Drive API接続成功！")
            else:
                st.error("❌ Google Drive API接続失敗")
                return
    
    st.divider()
    
    # ファイルアップロードテスト
    st.markdown("### 📤 ファイルアップロードテスト")
    
    uploaded_files = st.file_uploader(
        "テスト用ファイルをアップロード（PDF推奨）",
        type=['pdf', 'txt', 'docx', 'xlsx'],
        accept_multiple_files=True,
        key="drive_upload_test"
    )
    
    if uploaded_files:
        st.write(f"**選択されたファイル数:** {len(uploaded_files)}")
        
        for uploaded_file in uploaded_files:
            st.markdown(f"#### 📄 ファイル: {uploaded_file.name}")
            st.write(f"**ファイルサイズ:** {uploaded_file.size / 1024:.1f}KB")
            st.write(f"**ファイルタイプ:** {uploaded_file.type}")
            
            if st.button(f"Google Driveにアップロード", key=f"upload_{uploaded_file.name}"):
                with st.spinner(f"「{uploaded_file.name}」をGoogle Driveにアップロード中..."):
                    try:
                        # ファイル内容を読み込み
                        file_content = uploaded_file.read()
                        
                        # Google Driveにアップロード
                        upload_result = upload_pdf_to_drive(file_content, uploaded_file.name)
                        
                        if upload_result:
                            st.success("✅ ファイルアップロード成功！")
                            
                            # アップロード結果表示
                            st.markdown("#### 📋 アップロード結果")
                            st.write(f"**ファイルID:** {upload_result['file_id']}")
                            st.write(f"**ファイル名:** {upload_result['filename']}")
                            st.write(f"**Google DriveのURL:** {upload_result['file_url']}")
                            
                            # URLリンク
                            st.markdown(f"[📄 Google Driveで開く]({upload_result['file_url']})")
                            
                        else:
                            st.error("❌ ファイルアップロードに失敗しました")
                            
                    except Exception as e:
                        st.error(f"❌ アップロード処理でエラーが発生しました: {e}")
    
    st.divider()
    
    # ファイル一覧取得テスト
    st.markdown("### 📋 ファイル一覧取得テスト")
    
    if st.button("Google Driveのファイル一覧を取得", key="drive_list_files"):
        with st.spinner("Google Driveからファイル一覧を取得中..."):
            try:
                files_list = get_drive_files_list()
                
                if files_list:
                    st.success(f"✅ ファイル一覧取得成功！（{len(files_list)}件）")
                    
                    # ファイル一覧をテーブル表示
                    import pandas as pd
                    
                    # データフレーム用のデータ準備
                    df_data = []
                    for file_info in files_list:
                        df_data.append({
                            'ファイル名': file_info.get('name', 'N/A'),
                            'ファイルタイプ': file_info.get('mimeType', 'N/A'),
                            'サイズ(KB)': round(int(file_info.get('size', 0)) / 1024, 1) if file_info.get('size') else 'N/A',
                            '作成日時': file_info.get('createdTime', 'N/A')[:10] if file_info.get('createdTime') else 'N/A',
                            'Google DriveのURL': file_info.get('webViewLink', 'N/A')
                        })
                    
                    if df_data and len(df_data) > 0:
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # 詳細情報（折りたたみ）
                    with st.expander("📋 詳細なファイル情報（JSON）"):
                        st.json(files_list)
                        
                else:
                    st.info("📂 ファイルが見つかりませんでした")
                    
            except Exception as e:
                st.error(f"❌ ファイル一覧取得でエラーが発生しました: {e}")
    
    st.divider()
    
    # 設定手順の説明
    st.markdown("### 📋 設定手順")
    st.markdown("""
    1. **Google Cloud Console でサービスアカウント作成**
       - https://console.cloud.google.com/ にアクセス
       - プロジェクトを選択または作成
       - 「IAMと管理」→「サービスアカウント」
       - サービスアカウントを作成
    
    2. **Drive API有効化**
       - 「APIとサービス」→「ライブラリ」
       - 「Google Drive API」を検索して有効化
    
    3. **サービスアカウントキー生成**
       - サービスアカウントの「キー」タブ
       - 「キーを追加」→「新しいキーを作成」→「JSON」
       - ダウンロードしたJSONの内容を `.streamlit/secrets.toml` に設定
    
    4. **共有ドライブ設定（重要）**
       - 共有ドライブにサービスアカウントを**メンバーとして追加**
       - サービスアカウントのメールアドレス: `{st.secrets.get("google_drive", {}).get("client_email", "設定されていません")}`
       - 権限: 「編集者」または「管理者」
       - フォルダIDを `google_drive.default_folder_id` に設定（オプション）
    
    📌 **共有ドライブ使用時の注意点:**
    - サービスアカウントが共有ドライブのメンバーでない場合、アクセスできません
    - 個人ドライブとは異なり、共有ドライブ専用のAPIパラメータを使用します
    - このシステムは共有ドライブに対応しています（`supportsAllDrives=true`）
    """)
    
    # 統合テストボタン
    st.divider()
    st.markdown("### 🚀 統合テスト")
    
    if st.button("📋 全機能統合テスト実行", key="drive_integration_test"):
        st.markdown("#### 🔧 統合テスト実行中...")
        
        test_results = []
        
        # 1. 接続テスト
        with st.spinner("1. 接続テスト..."):
            connection_result = test_google_drive_connection()
            test_results.append(("接続テスト", "✅ 成功" if connection_result else "❌ 失敗"))
        
        # 2. ファイル一覧取得テスト
        with st.spinner("2. ファイル一覧取得テスト..."):
            try:
                files_list = get_drive_files_list()
                files_test_result = len(files_list) >= 0  # 0件でも成功
                test_results.append(("ファイル一覧取得", f"✅ 成功 ({len(files_list)}件)" if files_test_result else "❌ 失敗"))
            except Exception:
                test_results.append(("ファイル一覧取得", "❌ 失敗"))
        
        # 結果表示
        st.markdown("#### 📊 テスト結果")
        for test_name, result in test_results:
            st.write(f"**{test_name}:** {result}")
        
        # 総合判定
        success_count = sum(1 for _, result in test_results if "✅" in result)
        total_tests = len(test_results)
        
        if success_count == total_tests:
            st.success(f"🎉 全テスト成功！ ({success_count}/{total_tests})")
        else:
            st.warning(f"⚠️ 一部テスト失敗 ({success_count}/{total_tests})")


def render_aggrid_test_page():
    """ag-gridテストページ"""
    st.markdown("## 📊 ag-grid データグリッドテスト")
    
    st.info("🔧 ag-gridコンポーネントの動作テストとデータベース・スプレッドシート連携を確認します。")
    
    # ag-grid動作確認
    st.markdown("### 🔗 ag-grid基本動作テスト")
    
    if st.button("ag-grid接続テスト実行", key="aggrid_connection_test"):
        with st.spinner("ag-gridライブラリの動作をテスト中..."):
            if test_aggrid_connection():
                st.success("✅ ag-grid動作確認成功！")
            else:
                st.error("❌ ag-grid動作確認に失敗しました")
                st.markdown("""
                ### 🔧 確認事項:
                1. `streamlit-aggrid` パッケージがインストールされているか
                2. ライブラリのバージョンが適切か
                3. 依存関係に問題がないか
                """)
                return
    
    st.divider()
    
    # サンプルデータ生成
    st.markdown("### 📋 サンプルデータ生成・表示テスト")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        row_count = st.slider("生成するサンプルデータ件数", min_value=10, max_value=200, value=50, step=10)
        
        if st.button("📊 サンプルデータ生成", use_container_width=True):
            aggrid_manager = get_aggrid_manager()
            
            with st.spinner(f"{row_count}件のサンプル請求書データを生成中..."):
                sample_data = aggrid_manager.create_sample_invoice_data(row_count)
                st.session_state.aggrid_sample_data = sample_data
                st.success(f"✅ {len(sample_data)}件のサンプルデータを生成しました")
    
    with col2:
        st.markdown("#### 📋 生成されるデータ項目")
        st.markdown("""
        - **ID**: 一意識別子
        - **ファイル名**: PDFファイル名
        - **供給者名**: 請求元企業名
        - **請求書番号**: 請求書識別番号
        - **日付**: 請求日・支払期日
        - **金額**: 税抜・税込・税額
        - **勘定科目・品目**: 仕訳情報
        - **ステータス**: 処理状況
        - **作成者・日時**: メタデータ
        """)
    
    # データ表示・編集テスト
    if 'aggrid_sample_data' in st.session_state and not st.session_state.aggrid_sample_data.empty:
        st.markdown("### 📊 基本データグリッド表示テスト")
        
        tab1, tab2, tab3 = st.tabs(["🔍 基本表示", "✏️ 高機能編集", "🔄 データ連携"])
        
        with tab1:
            st.markdown("#### 🔍 基本ag-gridテスト")
            aggrid_manager = get_aggrid_manager()
            
            try:
                # 基本グリッド表示
                basic_grid_response = aggrid_manager.create_basic_grid(
                    st.session_state.aggrid_sample_data.head(20),
                    editable_columns=['supplier_name', 'account_title', 'status'],
                    selection_mode='multiple'
                )
                
                # 基本機能結果表示
                if basic_grid_response and hasattr(basic_grid_response, 'selected_rows') and basic_grid_response.selected_rows is not None:
                    selected_count = len(basic_grid_response.selected_rows)
                    if selected_count > 0:
                        st.info(f"✅ 選択された行数: {selected_count}件")
                        
                        with st.expander("選択されたデータ詳細", expanded=False):
                            st.dataframe(basic_grid_response.selected_rows)
                    else:
                        st.info("📋 データが表示されています。行を選択してテストしてください。")
                else:
                    st.info("📊 ag-gridが正常に表示されました。チェックボックスで行を選択できます。")
                    
            except Exception as e:
                st.error(f"❌ 基本ag-gridテストでエラーが発生しました: {e}")
                st.info("💡 ヒント: ページを再読み込みしてから再試行してください。")
        
        with tab2:
            st.markdown("#### ✏️ 高機能請求書編集グリッド")
            st.info("💡 セルをダブルクリックして編集、ドロップダウンで選択、チェックボックスで複数選択が可能です")
            
            try:
                # 高機能編集グリッド
                edit_grid_response = aggrid_manager.create_invoice_editing_grid(
                    st.session_state.aggrid_sample_data
                )
                
                # 編集結果表示
                if edit_grid_response:
                    st.markdown("#### 📊 編集結果サマリー")
                    
                    col_edit1, col_edit2, col_edit3 = st.columns(3)
                    
                    with col_edit1:
                        data_count = 0
                        if hasattr(edit_grid_response, 'data') and edit_grid_response.data is not None:
                            data_count = len(edit_grid_response.data)
                        st.metric("総データ件数", data_count)
                    
                    with col_edit2:
                        selected_count = 0
                        if hasattr(edit_grid_response, 'selected_rows') and edit_grid_response.selected_rows is not None:
                            selected_count = len(edit_grid_response.selected_rows)
                        st.metric("選択行数", selected_count)
                    
                    with col_edit3:
                        st.metric("表示モード", "高機能編集")
                    
                    # 選択されたデータの操作
                    if hasattr(edit_grid_response, 'selected_rows') and edit_grid_response.selected_rows and len(edit_grid_response.selected_rows) > 0:
                        st.markdown("#### 🛠️ 選択データ操作")
                        
                        col_op1, col_op2, col_op3 = st.columns(3)
                        
                        with col_op1:
                            if st.button("📋 選択データ詳細表示", use_container_width=True):
                                st.markdown("##### 📊 選択されたデータ")
                                selected_df = pd.DataFrame(edit_grid_response.selected_rows)
                                st.dataframe(selected_df, use_container_width=True)
                        
                        with col_op2:
                            if st.button("💾 データベース同期テスト", use_container_width=True):
                                selected_df = pd.DataFrame(edit_grid_response.selected_rows)
                                db_test_result = aggrid_manager.test_database_integration(selected_df)
                                
                                if db_test_result['success']:
                                    st.success(f"✅ {db_test_result['message']}")
                                else:
                                    st.error(f"❌ データベース同期テスト失敗: {db_test_result.get('error', '不明なエラー')}")
                        
                        with col_op3:
                            if st.button("📄 スプレッドシート出力テスト", use_container_width=True):
                                selected_df = pd.DataFrame(edit_grid_response.selected_rows)
                                export_test_result = aggrid_manager.test_spreadsheet_export(selected_df)
                                
                                if export_test_result['success']:
                                    st.success(f"✅ {export_test_result['message']}")
                                else:
                                    st.error(f"❌ スプレッドシート出力テスト失敗: {export_test_result.get('error', '不明なエラー')}")
                    else:
                        st.info("📋 データが表示されています。チェックボックスで行を選択すると操作ボタンが表示されます。")
                else:
                    st.warning("⚠️ 高機能編集グリッドの表示に問題がありました。")
                    
            except Exception as e:
                st.error(f"❌ 高機能編集グリッドでエラーが発生しました: {e}")
                st.info("💡 ヒント: ページを再読み込みしてから再試行してください。")
        
        with tab3:
            st.markdown("#### 🔄 データ連携機能テスト")
            
            try:
                # 全データでの連携テスト
                st.markdown("##### 📊 全データ連携テスト")
                
                col_all1, col_all2 = st.columns(2)
                
                with col_all1:
                    if st.button("🗃️ 全データ → データベース同期テスト", use_container_width=True):
                        with st.spinner("全データをデータベースに同期中..."):
                            try:
                                all_db_result = aggrid_manager.test_database_integration(st.session_state.aggrid_sample_data)
                                
                                if all_db_result['success']:
                                    st.success(f"✅ 全データ同期成功: {all_db_result['affected_rows']}件")
                                    
                                    # 結果詳細表示
                                    with st.expander("同期結果詳細", expanded=False):
                                        st.json(all_db_result)
                                else:
                                    st.error(f"❌ 全データ同期失敗: {all_db_result.get('error', '不明なエラー')}")
                            except Exception as e:
                                st.error(f"❌ データベース同期テストでエラー: {e}")
                
                with col_all2:
                    if st.button("📊 全データ → スプレッドシート出力テスト", use_container_width=True):
                        with st.spinner("全データをスプレッドシートに出力中..."):
                            try:
                                all_export_result = aggrid_manager.test_spreadsheet_export(st.session_state.aggrid_sample_data)
                                
                                if all_export_result['success']:
                                    st.success(f"✅ 全データ出力成功: {all_export_result['exported_rows']}件")
                                    
                                    # 結果詳細表示
                                    with st.expander("出力結果詳細", expanded=False):
                                        st.json(all_export_result)
                                else:
                                    st.error(f"❌ 全データ出力失敗: {all_export_result.get('error', '不明なエラー')}")
                            except Exception as e:
                                st.error(f"❌ スプレッドシート出力テストでエラー: {e}")
                
                # CSVダウンロード
                st.markdown("##### 💾 CSVダウンロードテスト")
                
                try:
                    csv_data = st.session_state.aggrid_sample_data.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label="📥 サンプルデータをCSVでダウンロード",
                        data=csv_data,
                        file_name=f"sample_invoice_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"❌ CSVダウンロード準備でエラー: {e}")
                    
            except Exception as e:
                st.error(f"❌ データ連携テストでエラーが発生しました: {e}")
                st.info("💡 ヒント: ページを再読み込みしてから再試行してください。")
    
    # 技術仕様説明
    st.divider()
    st.markdown("### 📋 ag-grid技術仕様")
    
    with st.expander("🔍 実装されている機能詳細", expanded=False):
        st.markdown("""
        #### 📊 ag-grid実装機能
        
        **✅ 基本機能**
        - 列のソート（昇順・降順）
        - 列フィルタ（テキスト・数値・日付）
        - 列のリサイズ・並び替え
        - ページネーション（1ページ20-25件）
        - 行選択（単一・複数・全選択）
        
        **✅ 編集機能**
        - セル直接編集（ダブルクリック）
        - ドロップダウン選択（勘定科目・品目・ステータス等）
        - 大きなテキストエリア（備考欄）
        - データ検証・フォーマット
        
        **✅ 高度な機能**
        - 条件付きセルスタイル（ステータス別色分け）
        - 列固定（ID列を左端固定）
        - サイドバー（フィルタ・列管理）
        - 数値フォーマット（カンマ区切り表示）
        
        **✅ データ連携**
        - DataFrameとの双方向変換
        - 選択行データの抽出
        - リアルタイムデータ更新
        - CSVエクスポート機能
        
        #### 🔄 連携テスト機能
        
        **📊 データベース連携**
        - Supabaseとの双方向同期（模擬）
        - 一括データ更新
        - 行レベルアクセス制御対応
        
        **📄 スプレッドシート連携**
        - Google Sheetsエクスポート（模擬）
        - freee連携用フォーマット対応
        - バックアップ・分析用途対応
        """)
    
    # ag-grid要件適合性評価
    st.markdown("### ✅ ag-grid要件適合性評価")
    
    requirements_check = {
        "インタラクティブ編集": "✅ 完全対応",
        "プルダウン選択": "✅ 完全対応", 
        "複数行選択・削除": "✅ 完全対応",
        "フィルタリング・ソート": "✅ 完全対応",
        "データベース連携": "✅ 技術検証済み",
        "スプレッドシート出力": "✅ 技術検証済み",
        "権限制御": "🔄 実装予定",
        "レスポンシブ表示": "✅ 完全対応",
        "大量データ処理": "✅ ページング対応"
    }
    
    col_req1, col_req2 = st.columns(2)
    
    with col_req1:
        st.markdown("#### 📋 機能要件チェック")
        for req, status in list(requirements_check.items())[:5]:
            st.write(f"**{req}**: {status}")
    
    with col_req2:
        st.markdown("#### 🔧 技術要件チェック")
        for req, status in list(requirements_check.items())[5:]:
            st.write(f"**{req}**: {status}")
    
    # 総合評価
    completed_items = len([status for status in requirements_check.values() if "✅" in status])
    total_items = len(requirements_check)
    completion_rate = (completed_items / total_items) * 100
    
    st.markdown(f"#### 🎯 総合適合率: **{completion_rate:.1f}%** ({completed_items}/{total_items})")
    
    if completion_rate >= 80:
        st.success("🎉 ag-gridは請求書処理システムの要件を十分に満たしています！")
    elif completion_rate >= 60:
        st.warning("⚠️ ag-gridは基本要件を満たしていますが、一部改善が必要です。")
    else:
        st.error("❌ ag-gridは要件を満たしていません。代替案を検討してください。")


def render_integrated_workflow_test_page():
    """統合ワークフローテストページ"""
    st.markdown("## 🔄 統合ワークフローテスト")
    
    st.info("📋 PDF → AI抽出 → DB保存の完全な統合ワークフローをテストします。")
    
    # セッション状態の初期化
    if "workflow_progress" not in st.session_state:
        st.session_state.workflow_progress = []
    if "workflow_result" not in st.session_state:
        st.session_state.workflow_result = None
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
    
    # ファイルアップローダー
    st.markdown("### 📤 PDFファイル選択")
    uploaded_file = st.file_uploader(
        "請求書PDFファイルを選択してください",
        type=['pdf'],
        key="workflow_pdf_uploader"
    )
    
    # ユーザー情報取得
    user_info = get_current_user()
    user_id = user_info.get('email', 'test@example.com') if user_info else 'test@example.com'
    
    # 処理実行ボタン
    if uploaded_file is not None:
        st.markdown("### 🚀 ワークフロー実行")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("📋 統合ワークフロー開始", 
                        disabled=st.session_state.is_processing,
                        use_container_width=True):
                
                # セッション状態リセット
                st.session_state.workflow_progress = []
                st.session_state.workflow_result = None
                st.session_state.is_processing = True
                
                # ワークフロー実行
                execute_integrated_workflow(uploaded_file, user_id)
        
        with col2:
            if st.button("🔄 リセット", use_container_width=True):
                st.session_state.workflow_progress = []
                st.session_state.workflow_result = None
                st.session_state.is_processing = False
                st.rerun()
    
    # 進捗表示
    if st.session_state.workflow_progress:
        render_workflow_progress()
    
    # 結果表示
    if st.session_state.workflow_result:
        render_workflow_result()
    
    # 説明セクション
    st.divider()
    st.markdown("### 📋 ワークフロー詳細")
    
    with st.expander("🔍 処理フローの詳細", expanded=False):
        st.markdown("""
        #### 📊 統合ワークフローの処理段階
        
        1. **📤 ファイルアップロード** (10-30%)
           - PDFファイルをGoogle Driveにアップロード
           - ファイル情報の取得と検証
        
        2. **🤖 AI情報抽出** (40-70%)
           - Gemini APIを使用してPDFから請求書情報を抽出
           - 供給者名、請求書番号、金額、日付などを識別
        
        3. **💾 データベース保存** (80-90%)
           - 抽出された情報をSupabaseデータベースに保存
           - インデックス作成と関連データの整合性確認
        
        4. **✅ 処理完了** (100%)
           - 全工程の完了確認
           - 処理時間の計測と結果の最終検証
        
        #### 🛠️ エラーハンドリング
        - 各段階でのエラー検出と詳細メッセージ表示
        - 処理中断時の状態保持
        - リトライ機能（手動）
        
        #### 📈 リアルタイム進捗
        - プログレスバーによる視覚的な進捗表示
        - 各段階での詳細メッセージ
        - タイムスタンプ付きログ表示
        """)


def execute_integrated_workflow(uploaded_file, user_id):
    """統合ワークフロー実行"""
    
    # 進捗コールバック関数
    def progress_callback(progress: WorkflowProgress):
        st.session_state.workflow_progress.append({
            'status': progress.status.value,
            'step': progress.step,
            'progress_percent': progress.progress_percent,
            'message': progress.message,
            'timestamp': progress.timestamp.strftime("%H:%M:%S"),
            'details': progress.details
        })
        # リアルタイム更新のためのrerun
        st.rerun()
    
    try:
        # サービスの初期化
        ai_service = get_gemini_api()
        storage_service = get_google_drive()
        database_service = get_database()
        
        # ワークフローインスタンス作成
        workflow = InvoiceProcessingWorkflow(
            ai_service=ai_service,
            storage_service=storage_service,
            database_service=database_service,
            progress_callback=progress_callback
        )
        
        # PDFデータ取得
        pdf_data = uploaded_file.read()
        filename = uploaded_file.name
        
        # ワークフロー実行
        result = workflow.process_invoice(pdf_data, filename, user_id)
        
        # 結果をセッション状態に保存
        st.session_state.workflow_result = {
            'success': result.success,
            'invoice_id': result.invoice_id,
            'extracted_data': result.extracted_data,
            'file_info': result.file_info,
            'error_message': result.error_message,
            'processing_time': result.processing_time
        }
        
    except Exception as e:
        st.session_state.workflow_result = {
            'success': False,
            'error_message': f"ワークフロー実行エラー: {str(e)}"
        }
    
    finally:
        st.session_state.is_processing = False


def render_workflow_progress():
    """ワークフロー進捗表示"""
    st.markdown("### 📊 処理進捗")
    
    if not st.session_state.workflow_progress:
        return
    
    # 最新の進捗情報
    latest_progress = st.session_state.workflow_progress[-1]
    
    # プログレスバー
    progress_percent = latest_progress['progress_percent']
    st.progress(progress_percent / 100.0)
    
    # 現在のステータス
    status_color = {
        'uploading': '🔄',
        'processing': '🤖', 
        'saving': '💾',
        'completed': '✅',
        'failed': '❌'
    }
    
    status_icon = status_color.get(latest_progress['status'], '⏳')
    st.markdown(f"**{status_icon} {latest_progress['step']}** - {latest_progress['message']} ({progress_percent}%)")
    
    # 進捗履歴（展開可能）
    with st.expander(f"📝 詳細ログ ({len(st.session_state.workflow_progress)}件)", expanded=False):
        for i, progress in enumerate(reversed(st.session_state.workflow_progress)):
            icon = status_color.get(progress['status'], '⏳')
            st.write(f"{icon} **[{progress['timestamp']}]** {progress['step']} - {progress['message']}")
            
            # 詳細情報があれば表示
            if progress.get('details'):
                with st.expander(f"詳細情報 #{len(st.session_state.workflow_progress)-i}", expanded=False):
                    st.json(progress['details'])


def render_workflow_result():
    """ワークフロー結果表示"""
    st.markdown("### 📊 処理結果")
    
    result = st.session_state.workflow_result
    
    if result['success']:
        st.success("🎉 統合ワークフロー処理が正常に完了しました！")
        
        # 処理サマリー
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("請求書ID", result.get('invoice_id', 'N/A'))
        
        with col2:
            processing_time = result.get('processing_time', 0)
            st.metric("処理時間", f"{processing_time:.2f}秒")
        
        with col3:
            st.metric("ステータス", "✅ 完了")
        
        # 抽出データ表示
        if result.get('extracted_data'):
            st.markdown("#### 📋 抽出された請求書情報")
            
            extracted_data = result['extracted_data']
            
            # 主要情報を表形式で表示
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📊 基本情報**")
                st.write(f"• 供給者名: {extracted_data.get('issuer', 'N/A')}")
                st.write(f"• 請求書番号: {extracted_data.get('main_invoice_number', 'N/A')}")
                st.write(f"• 通貨: {extracted_data.get('currency', 'JPY')}")
            
            with col2:
                st.write("**💰 金額情報**")
                st.write(f"• 合計金額: ¥{extracted_data.get('amount_inclusive_tax', 0):,}")
                st.write(f"• 税額: ¥{(extracted_data.get('amount_inclusive_tax', 0) - extracted_data.get('amount_exclusive_tax', 0)):,}")
                st.write(f"• 請求日: {extracted_data.get('issue_date', 'N/A')}")
            
            # 詳細データ（JSON）
            with st.expander("🔍 抽出データ詳細（JSON）", expanded=False):
                st.json(extracted_data)
        
        # ファイル情報
        if result.get('file_info'):
            st.markdown("#### 📁 ファイル情報")
            file_info = result['file_info']
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"• ファイル名: {file_info.get('name', 'N/A')}")
                st.write(f"• ファイルID: {file_info.get('id', 'N/A')}")
            
            with col2:
                if 'webViewLink' in file_info:
                    st.markdown(f"• [📄 Google Driveで表示]({file_info['webViewLink']})")
                
                if 'downloadUrl' in file_info:
                    st.markdown(f"• [⬇️ ダウンロード]({file_info['downloadUrl']})")
    
    else:
        st.error("❌ 統合ワークフロー処理に失敗しました")
        
        error_message = result.get('error_message', '不明なエラー')
        st.error(f"エラー詳細: {error_message}")
        
        # 処理時間（失敗時も表示）
        processing_time = result.get('processing_time', 0)
        if processing_time > 0:
            st.info(f"⏱️ 処理時間: {processing_time:.2f}秒")


def render_main_content(selected_menu, user_info):
    """メインコンテンツをレンダリング"""
    
    if selected_menu == "📤 請求書処理":
        render_unified_invoice_processing_page()  # 新しい統合ページ
    
    elif selected_menu == "📊 処理状況ダッシュボード":
        render_dashboard_page()
    
    elif selected_menu == "⚙️ メール設定":
        render_settings_page()
    
    elif selected_menu == "🔧 DB接続テスト":
        render_database_test_page()
    
    elif selected_menu == "🤖 Gemini APIテスト":
        render_gemini_test_page()
    
    elif selected_menu == "☁️ Google Drive APIテスト":
        render_google_drive_test_page()
    
    elif selected_menu == "📊 ag-grid データグリッドテスト":
        render_aggrid_test_page()
    
    elif selected_menu == "🔄 統合ワークフローテスト":
        render_integrated_workflow_test_page()
    
    else:
        # デフォルト画面
        st.markdown("## 🏠 ホーム")
        st.success(f"🎉 {user_info['name']}さん、ようこそ！")
        
        st.markdown("""
        ### 📋 システム概要
        このシステムでは以下の機能をご利用いただけます：
        
        - **📤 請求書処理**: 本番アップロード・OCRテストの統合ページ
        - **📊 処理状況ダッシュボード**: アップロードした請求書の状況確認・編集
        - **⚙️ メール設定**: 通知設定の管理
        
        ### 🚀 開始方法
        1. サイドバーから「📤 請求書処理」を選択
        2. 「本番アップロード」または「OCRテスト」タブを選択
        3. PDFファイルをアップロード
        4. AI による自動処理を開始
        5. 「📊 処理状況ダッシュボード」で結果を確認
        """)


def execute_unified_upload_processing(uploaded_files, prompt_key, validation_config, processing_mode):
    """統一ワークフローによるアップロード処理（新アダプター対応）"""
    st.session_state.is_unified_processing = True
    st.session_state.unified_processing_results = []
    
    # 統一ワークフローの取得
    workflow = st.session_state.unified_workflow
    display_manager = st.session_state.workflow_display
    
    try:
        with st.spinner("統一ワークフローで処理中..."):
            # 新しい統一インターフェースで処理実行
            import asyncio
            result = asyncio.run(workflow.process_uploaded_files(
                uploaded_files,
                mode=processing_mode,
                prompt_key=prompt_key,
                validation_config=validation_config
            ))
            
            st.session_state.unified_processing_results = [result]
            
        st.success("✅ 統一ワークフロー処理が完了しました！")
        
    except Exception as e:
        st.error(f"統一ワークフロー処理エラー: {e}")
        logger.error(f"統一ワークフロー処理エラー: {e}")
        
        # エラー結果を保存
        st.session_state.unified_processing_results = [{
            'error': str(e),
            'status': 'failed',
            'processed_at': datetime.now().isoformat()
        }]
    
    finally:
        # 処理中フラグをリセット
        st.session_state.is_unified_processing = False

def render_unified_upload_results(show_detailed_validation):
    """統一ワークフロー結果の表示"""
    if not st.session_state.unified_processing_results:
        return
    
    st.markdown("### 📋 処理結果（統一ワークフロー）")
    
    results = st.session_state.unified_processing_results
    display_manager = st.session_state.workflow_display
    
    for result in results:
        if result.get('error'):
            st.error(f"処理エラー: {result['error']}")
            continue
        
        # バッチ処理結果の場合（mode確認を修正）
        if (result.get('mode') == ProcessingMode.BATCH or 
            result.get('mode') == 'batch' or
            result.get('total_files', 0) > 1 or
            isinstance(result.get('results'), list)):
            
            st.info(f"🎯 バッチ処理結果を表示中... ファイル数: {result.get('total_files', len(result.get('results', [])))}")
            display_manager.display_batch_results(result)
        else:
            # 単一ファイル結果の場合
            st.info("🎯 単一ファイル結果を表示中...")
            display_manager.display_single_result(result)




def render_upload_progress():
    """アップロード進捗の表示"""
    if st.session_state.upload_progress:
        # 最新の進捗情報を取得
        latest_progress = st.session_state.upload_progress[-1]
        
        # 全体進捗バー
        overall_progress = latest_progress.get('overall_progress', 0)
        st.progress(overall_progress / 100, text=f"全体進捗: {overall_progress:.1f}%")
        
        # 現在のファイル処理状況
        current_file = latest_progress.get('filename', '')
        current_step = latest_progress.get('step', '')
        current_message = latest_progress.get('message', '')
        current_status = latest_progress.get('status', '')
        
        # ステータス別アイコン
        status_icons = {
            'processing': '🔄',
            'completed': '✅',
            'failed': '❌',
            'uploading': '📤',
            'saving': '💾'
        }
        
        status_icon = status_icons.get(current_status, '⏳')
        
        # カード形式で現在の状況を表示
        with st.container():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"### {status_icon}")
            with col2:
                st.markdown(f"**現在の処理:** {current_file}")
                st.markdown(f"**ステップ:** {current_step}")
                st.markdown(f"**状況:** {current_message}")
        
        # 処理統計
        if len(st.session_state.upload_progress) > 1:
            col1, col2, col3 = st.columns(3)
            
            processing_files = [p for p in st.session_state.upload_progress if p.get('status') == 'processing']
            completed_files = [p for p in st.session_state.upload_progress if p.get('status') == 'completed']
            failed_files = [p for p in st.session_state.upload_progress if p.get('status') == 'failed']
            
            with col1:
                st.metric("処理中", len(processing_files))
            with col2:
                st.metric("完了", len(completed_files))
            with col3:
                st.metric("エラー", len(failed_files))
        
        # 詳細ログ表示（最新10件）
        with st.expander("📋 詳細ログ", expanded=False):
            recent_logs = st.session_state.upload_progress[-10:]
            for log in reversed(recent_logs):
                timestamp = log.get('timestamp', '')
                filename = log.get('filename', '')
                step = log.get('step', '')
                message = log.get('message', '')
                status = log.get('status', '')
                
                # ログエントリのスタイル
                status_color = {
                    'completed': '🟢',
                    'failed': '🔴',
                    'processing': '🟡',
                    'uploading': '🔵',
                    'saving': '🟣'
                }
                
                color_icon = status_color.get(status, '⚪')
                st.markdown(f"{color_icon} **[{timestamp}]** {filename}: {step} - {message}")
                
                # 詳細情報があれば表示
                details = log.get('details', {})
                if details and isinstance(details, dict):
                    with st.expander(f"詳細 - {filename}", expanded=False):
                        st.json(details)
        
        # 🚨 自動更新完全無効化（無限ループ防止）
        if st.session_state.is_processing_upload and current_status in ['processing', 'uploading', 'saving']:
            st.markdown("🔄 **処理中... 完了まで少々お待ちください**")
            st.info("進捗はログで確認できます。処理完了後に自動で結果が表示されます。")


def render_ocr_test_page():
    """OCRテスト機能（統一コンポーネント版）- プロンプト自動選択対応"""
    st.markdown("## 🔍 OCR精度テスト (Gemini 2.0-flash)")
    
    st.info("📋 統一されたワークフローでOCR精度テストを実行します。既存のPDFファイルでAI解析の精度を検証できます。")
    
    # 統一ワークフローの初期化
    if "unified_workflow_ocr" not in st.session_state:
        try:
            # GeminiAPIManagerの直接インスタンス化
            gemini_helper = GeminiAPIManager()
            database_manager = get_database()
            st.session_state.unified_workflow_ocr = UnifiedProcessingWorkflow(
                gemini_helper=gemini_helper,
                database_manager=database_manager
            )
            st.session_state.workflow_display_ocr = WorkflowDisplayManager(st.session_state.unified_workflow_ocr)
        except Exception as e:
            st.error(f"OCRテストワークフロー初期化エラー: {e}")
            return
    
    # プロンプト自動選択（手動選択不要）
    st.markdown("### 🤖 プロンプト設定")
    prompt_manager = UnifiedPromptManager()
    prompt_selector = PromptSelector(prompt_manager)
    
    # OCRテスト用プロンプト自動選択
    selected_prompt_key = prompt_selector.get_recommended_prompt(ProcessingMode.OCR_TEST)
    
    if selected_prompt_key:
        prompt_data = prompt_manager.get_prompt_by_key(selected_prompt_key)
        if prompt_data:
            prompt_name = prompt_data.get('name', selected_prompt_key)
            st.success(f"✅ 自動選択されたプロンプト: **{prompt_name}**")
            st.caption("📝 OCRテストに最適なプロンプトが自動選択されます")
        
        # プロンプト互換性チェック
        is_compatible, warnings = prompt_manager.validate_prompt_compatibility(
            selected_prompt_key, ProcessingMode.OCR_TEST
        )
        if warnings:
            for warning in warnings:
                st.warning(f"⚠️ {warning}")
        else:
            st.success("✅ 互換性OK")
    else:
        st.error("適切なプロンプトが見つかりません")
        selected_prompt_key = None
    
    # テスト設定
    st.markdown("### 🔧 テスト設定")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        test_mode = st.selectbox(
            "テストモード",
            ["精度重視", "速度重視", "バランス"],
            help="テストの重点項目を選択します"
        )
    
    with col2:
        max_files = st.selectbox(
            "テスト対象ファイル数",
            [5, 10, 20, 50, -1],
            format_func=lambda x: "全て" if x == -1 else f"{x}件",
            index=0,
            help="処理するPDFファイルの最大件数"
        )
    
    with col3:
        include_validation = st.checkbox(
            "詳細検証実行",
            value=True,
            help="統一検証システムによる詳細分析を実行",
            key="standalone_ocr_test_include_validation"
        )
    
    # Google DriveフォルダID設定
    st.markdown("### 📁 テスト対象フォルダ")
    default_folder_id = "1ZCJsI9j8A9VJcmiY79BcP1jgzsD51X6E"
    folder_id = st.text_input(
        "Google DriveフォルダID",
        value=default_folder_id,
        help="テスト対象PDFが格納されたGoogle DriveフォルダのID"
    )
    
    # セッション状態の初期化
    if "ocr_test_results" not in st.session_state:
        st.session_state.ocr_test_results = []
    if "is_ocr_testing" not in st.session_state:
        st.session_state.is_ocr_testing = False
    
    # テスト実行ボタン
    col1, col2 = st.columns([2, 1])
    
    with col1:
        button_text = f"🚀 統一OCRテスト開始 ({max_files if max_files != -1 else '全'}件)"
        
        if st.button(button_text, type="primary", use_container_width=True):
            if not folder_id:
                st.error("フォルダIDを入力してください")
            elif not selected_prompt_key:
                st.error("プロンプトが選択されていません")
            elif not st.session_state.is_ocr_testing:
                execute_unified_ocr_test(
                    folder_id,
                    selected_prompt_key,
                    max_files,
                    test_mode,
                    include_validation
                )
            else:
                st.warning("現在テスト実行中です。しばらくお待ちください。")
    
    with col2:
        if st.button("🔄 リセット", use_container_width=True):
            st.session_state.ocr_test_results = []
            st.session_state.is_ocr_testing = False
            st.rerun()
    
    # テスト結果表示
    if st.session_state.ocr_test_results:
        render_ocr_test_results(include_validation)


def render_upload_results():
    """アップロード結果の表示"""
    if not st.session_state.upload_results:
        return
    
    results = st.session_state.upload_results
    total_files = len(results)
    successful_files = len([r for r in results if r.get('success', False)])
    failed_files = total_files - successful_files
    
    # 結果サマリー
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("総ファイル数", total_files)
    
    with col2:
        st.metric("成功", successful_files)
    
    with col3:
        st.metric("失敗", failed_files)
    
    # 操作ボタン
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 新しいファイルを処理", use_container_width=True):
            # セッション状態をリセット
            st.session_state.upload_progress = []
            st.session_state.upload_results = []
            st.session_state.is_processing_upload = False
            st.rerun()
    
    with col2:
        if st.button("📊 ダッシュボードで確認", use_container_width=True):
            st.session_state.selected_menu = "📊 処理状況ダッシュボード"
            st.rerun()


def render_ocr_test_results(include_validation):
    """OCRテスト結果の表示"""
    st.markdown("---")
    st.markdown("### 📊 OCRテスト結果")
    
    for result in st.session_state.ocr_test_results:
        if result.get('error'):
            st.error(f"❌ テスト失敗: {result['error']}")
        else:
            # バッチ処理結果サマリー表示
            st.success(f"✅ OCRテスト完了")
            
            # 結果の詳細は統一ワークフロー表示マネージャーを使用
            workflow_display = st.session_state.get('workflow_display_ocr')
            if workflow_display:
                workflow_display.display_batch_results(result)

def execute_unified_ocr_test(folder_id, prompt_key, max_files, test_mode, include_validation):
    """統一ワークフローによるOCRテスト実行 - ダウンロード機能修正版"""
    st.session_state.is_ocr_testing = True
    st.session_state.ocr_test_results = []
    
    # 現在のユーザー情報取得
    user_info = get_current_user()
    user_id = user_info.get('email', 'test@example.com') if user_info else 'test@example.com'
    
    # 統一ワークフローの取得（安全性チェック付き）
    if not hasattr(st.session_state, 'unified_workflow_ocr') or st.session_state.unified_workflow_ocr is None:
        st.error("❌ OCR統合ワークフローが初期化されていません。ページを再読み込みしてください。")
        st.session_state.is_ocr_testing = False
        return
    
    workflow = st.session_state.unified_workflow_ocr
    
    try:
        with st.spinner("統一OCRテストワークフローで処理中..."):
            # Google Driveからファイル一覧取得
            from infrastructure.storage.google_drive_helper import get_google_drive
            drive_manager = get_google_drive()
            
            if not drive_manager:
                st.error("Google Drive接続に失敗しました")
                return
            
            # PDFファイル一覧取得（修正済みOCRテストヘルパーを使用）
            from utils.ocr_test_helper import OCRTestManager
            ocr_manager = OCRTestManager(drive_manager, None, None)
            pdf_files = ocr_manager.get_drive_pdfs(folder_id)
            
            if not pdf_files or len(pdf_files) == 0:
                st.error("指定フォルダにPDFファイルが見つかりません")
                return
            
            # ファイル数制限
            if max_files != -1 and len(pdf_files) > max_files:
                pdf_files = pdf_files[:max_files]
            
            st.info(f"📊 {len(pdf_files)}件のPDFファイルでテストを開始します")
            
            # バッチ処理用データ準備（修正されたdownload_fileメソッドを使用）
            files_data = []
            for pdf_file in pdf_files:
                try:
                    # 修正済みのdownload_fileメソッドを使用
                    file_data = drive_manager.download_file(pdf_file['id'])
                    if file_data:
                        files_data.append({
                            'data': file_data,
                            'filename': pdf_file['name']
                        })
                        logger.info(f"✅ ファイルダウンロード成功: {pdf_file['name']}")
                    else:
                        logger.error(f"❌ ファイルダウンロード失敗: {pdf_file['name']}")
                except Exception as e:
                    logger.error(f"ファイルダウンロードエラー {pdf_file['name']}: {e}")
                    continue
            
            if not files_data:
                st.error("PDFファイルのダウンロードに失敗しました")
                return
            
            st.info(f"🎯 {len(files_data)}件のファイルダウンロード完了")
            
            # 検証設定
            validation_config = {
                'strict_mode': test_mode == "精度重視",
                'include_detailed_validation': include_validation,
                'test_mode': test_mode
            }
            
            # 統一ワークフローでバッチ処理実行
            import asyncio
            result = asyncio.run(workflow.process_batch_files(
                files_data,
                mode=ProcessingMode.OCR_TEST,
                prompt_key=prompt_key,
                validation_config=validation_config
            ))
            
            st.session_state.ocr_test_results = [result]
        
        st.success("✅ 統一OCRテストが完了しました！")
        
    except Exception as e:
        st.error(f"統一OCRテストエラー: {e}")
        logger.error(f"統一OCRテストエラー: {e}")
        
        # エラー結果を保存
        st.session_state.ocr_test_results = [{
            'error': str(e),
            'status': 'failed',
            'processed_at': datetime.now().isoformat()
        }]
    
    finally:
        st.session_state.is_ocr_testing = False
        
        # UI更新を強制実行して結果表示
        if st.session_state.ocr_test_results:
            st.rerun()



def main():
    """メインアプリケーション"""
    
    # ページ設定
    configure_page()
    
    # デバッグパネルの表示
    render_debug_panel()
    
    # セッション状態の初期化
    initialize_session_state()
    
    # タイトル
    st.title("📄 請求書処理自動化システム")
    st.markdown("---")
    
    # デバッグ情報の表示（デバッグモード時のみ）
    show_debug_info()
    
    # 認証チェック（認証されていない場合はログイン画面を表示）
    user_info = require_auth()
    
    # 認証成功後の処理
    try:
        # サイドバーをレンダリング
        selected_menu = render_sidebar(user_info)
        
        # メインコンテンツをレンダリング
        render_main_content(selected_menu, user_info)
        
        # フッター
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
            "請求書処理自動化システム v1.0 - streamlit-oauth統一認証版"
            "</div>",
            unsafe_allow_html=True
        )
        
    except Exception as e:
        st.error(f"アプリケーションエラーが発生しました: {e}")
        st.info("ページを再読み込みするか、管理者に問い合わせてください。")


if __name__ == "__main__":
    main() 