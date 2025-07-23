"""
請求書処理ページ - 本番アップロード・OCRテスト統合ページ
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any
import time

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent  # src/ ディレクトリ
sys.path.insert(0, str(project_root))

try:
    from infrastructure.auth.oauth_handler import get_current_user
    from infrastructure.database.database import get_database
    from infrastructure.ai.gemini_helper import GeminiAPIManager
    from infrastructure.storage.google_drive_helper import get_google_drive
    from core.workflows.unified_processing import UnifiedProcessingWorkflow, ProcessingMode
    from core.services.unified_prompt_manager import UnifiedPromptManager
    from core.services.prompt_selector import PromptSelector
    from utils.log_config import get_logger
    
    logger = get_logger(__name__)
    
except ImportError as e:
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.stop()


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
    # プロンプト自動選択（本番アップロードモード）
    prompt_selector = st.session_state.prompt_selector
    selected_prompt_key = prompt_selector.get_recommended_prompt(ProcessingMode.PRODUCTION)
    
    if selected_prompt_key:
        prompt_data = st.session_state.prompt_manager.get_prompt_by_key(selected_prompt_key)
        if prompt_data:
            prompt_name = prompt_data.get('name', selected_prompt_key)
            st.success(f"✅ 自動選択されたプロンプト: **{prompt_name}**")
            st.caption("📝 本番処理に最適なプロンプトが自動選択されます")
        
        # プロンプト互換性チェック
        is_compatible, warnings = st.session_state.prompt_manager.validate_prompt_compatibility(
            selected_prompt_key, ProcessingMode.PRODUCTION
        )
        if warnings:
            for warning in warnings:
                st.warning(f"⚠️ {warning}")
        else:
            st.success("✅ 互換性OK")
    else:
        st.error("適切なプロンプトが見つかりません")
        return
    
    # アップロード設定
    st.markdown("### 📤 ファイルアップロード")
    uploaded_files = st.file_uploader(
        "請求書PDFファイルを選択してください（複数選択可）",
        type=['pdf'],
        accept_multiple_files=True,
        key="production_upload_files"
    )
    
    if uploaded_files:
        st.info(f"📄 {len(uploaded_files)}件のファイルがアップロードされました")
        
        # 処理オプション
        col1, col2 = st.columns(2)
        
        with col1:
            include_validation = st.checkbox(
                "詳細検証実行",
                value=True,
                help="統一検証システムによる詳細分析を実行",
                key="production_include_validation"
            )
        
        with col2:
            save_to_db = st.checkbox(
                "データベース保存",
                value=True,
                help="処理結果をデータベースに保存",
                key="production_save_to_db"
            )
        
        # 処理実行ボタン
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🚀 統一ワークフロー処理開始", type="primary", use_container_width=True):
                if not selected_prompt_key:
                    st.error("プロンプトが選択されていません")
                else:
                    execute_unified_upload_processing(
                        uploaded_files,
                        selected_prompt_key,
                        include_validation,
                        save_to_db
                    )
        
        with col2:
            if st.button("🔄 リセット", use_container_width=True):
                # セッション状態をクリア
                st.session_state.unified_processing_results = []
                st.rerun()
    
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
    
    # OCRテスト結果表示
    if st.session_state.ocr_test_results:
        render_ocr_test_results(include_validation)


def execute_unified_upload_processing(uploaded_files, prompt_key, include_validation, save_to_db):
    """統一ワークフローによる本番アップロード処理"""
    # 現在のユーザー情報取得
    user_info = get_current_user()
    user_id = user_info.get('email', 'test@example.com') if user_info else 'test@example.com'
    
    # 統一ワークフローの取得
    workflow = st.session_state.unified_workflow
    
    try:
        with st.spinner("統一ワークフローで処理中..."):
            # バッチ処理用データ準備
            files_data = []
            for uploaded_file in uploaded_files:
                pdf_data = uploaded_file.read()
                files_data.append({
                    'filename': uploaded_file.name,
                    'data': pdf_data,
                    'user_id': user_id
                })
            
            # 統一バッチ処理実行
            batch_result = workflow.process_batch(
                files_data,
                mode=ProcessingMode.PRODUCTION,
                prompt_key=prompt_key,
                include_validation=include_validation,
                save_to_database=save_to_db
            )
            
            # 結果をセッション状態に保存
            st.session_state.unified_processing_results = batch_result
            
        st.success("✅ 統一アップロード処理が完了しました！")
        
    except Exception as e:
        logger.error(f"統一アップロード処理エラー: {e}")
        st.error(f"処理中にエラーが発生しました: {e}")
        
    finally:
        # 進捗状態をリセット
        st.session_state.upload_progress = []


def execute_unified_ocr_test(folder_id, prompt_key, max_files, test_mode, include_validation):
    """統一ワークフローによるOCRテスト実行"""
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
            drive_manager = get_google_drive()
            
            if not drive_manager:
                st.error("Google Drive接続に失敗しました")
                return
            
            # PDFファイル一覧取得
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
            
            # バッチ処理用データ準備
            files_data = []
            for file_info in pdf_files:
                try:
                    # ファイルダウンロード
                    file_data = drive_manager.download_file(file_info['id'])
                    if file_data:
                        files_data.append({
                            'filename': file_info['filename'],
                            'data': file_data,
                            'user_id': user_id
                        })
                        logger.info(f"✅ ファイルダウンロード成功: {file_info['filename']}")
                    else:
                        logger.warning(f"⚠️ ファイルダウンロード失敗: {file_info['filename']}")
                except Exception as e:
                    logger.error(f"❌ ファイル処理エラー: {file_info['filename']} - {e}")
            
            if not files_data:
                st.error("処理可能なファイルがありませんでした")
                return
            
            # 統一バッチ処理実行
            batch_result = workflow.process_batch(
                files_data,
                mode=ProcessingMode.OCR_TEST,
                prompt_key=prompt_key,
                include_validation=include_validation,
                save_to_database=False  # OCRテストではDBに保存しない
            )
            
            # 結果をセッション状態に保存
            st.session_state.ocr_test_results = batch_result
            
        st.success("✅ 統一OCRテストが完了しました！")
        
    except Exception as e:
        logger.error(f"統一OCRテストエラー: {e}")
        st.error(f"OCRテスト中にエラーが発生しました: {e}")
        
    finally:
        st.session_state.is_ocr_testing = False
        
        # UI更新を強制実行して結果表示
        if st.session_state.ocr_test_results:
            st.rerun()


def render_unified_upload_results(include_validation):
    """統一アップロード結果表示"""
    if not st.session_state.unified_processing_results:
        return
    
    # ワークフロー表示マネージャーを使用して結果表示
    if hasattr(st.session_state, 'workflow_display') and st.session_state.workflow_display:
        st.session_state.workflow_display.display_batch_results(st.session_state.unified_processing_results)
    else:
        st.error("❌ ワークフロー表示マネージャーが初期化されていません")


def render_ocr_test_results(include_validation):
    """OCRテスト結果表示"""
    if not st.session_state.ocr_test_results:
        return
    
    # ワークフロー表示マネージャーを使用して結果表示
    if hasattr(st.session_state, 'workflow_display_ocr') and st.session_state.workflow_display_ocr:
        st.session_state.workflow_display_ocr.display_batch_results(st.session_state.ocr_test_results)
    else:
        st.error("❌ OCRワークフロー表示マネージャーが初期化されていません") 