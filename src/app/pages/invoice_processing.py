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
    from infrastructure.ai.gemini_helper import get_gemini_api
    from infrastructure.storage.google_drive_helper import get_google_drive
    from core.models.workflow_models import ProcessingMode
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
            if st.button("🚀 統一ワークフロー処理開始", type="primary", use_container_width=True, key="production_start_button"):
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
            if st.button("🔄 リセット", use_container_width=True, key="production_reset_button"):
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
        
        if st.button(button_text, type="primary", use_container_width=True, key="ocr_test_start_button"):
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
        if st.button("🔄 リセット", use_container_width=True, key="ocr_test_reset_button"):
            st.session_state.ocr_test_results = []
            st.session_state.is_ocr_testing = False
            st.rerun()
    
    # OCRテスト結果表示
    if st.session_state.ocr_test_results:
        render_ocr_test_results(include_validation)


def execute_unified_upload_processing(uploaded_files, prompt_key, include_validation, save_to_db):
    """統一ワークフローによる本番アップロード処理（UnifiedWorkflowEngine版）"""
    # 現在のユーザー情報取得
    user_info = get_current_user()
    user_id = user_info.get('email', 'test@example.com') if user_info else 'test@example.com'
    
    # 進捗コールバック関数
    def progress_callback(progress):
        logger.info(f"📊 アップロード進捗: {progress.step} ({progress.progress_percent}%) - {progress.message}")
    
    try:
        with st.spinner("統一ワークフローエンジンで処理中..."):
            # サービスの初期化
            ai_service = get_gemini_api()
            storage_service = get_google_drive()
            database_service = get_database()
            
            # 統一ワークフローエンジン作成
            from core.workflows.unified_workflow_engine import UnifiedWorkflowEngine
            
            engine = UnifiedWorkflowEngine(
                ai_service=ai_service,
                storage_service=storage_service,
                database_service=database_service,
                progress_callback=progress_callback
            )
            
            # 統一アップロード処理実行（Streamlit uploaded files直接処理）
            batch_result = engine.process_uploaded_files(
                uploaded_files=uploaded_files,
                user_id=user_id,
                mode="upload"
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
    """統一ワークフローによるOCRテスト実行（UnifiedWorkflowEngine版）"""
    st.session_state.is_ocr_testing = True
    st.session_state.ocr_test_results = []
    
    # 現在のユーザー情報取得
    user_info = get_current_user()
    user_id = user_info.get('email', 'test@example.com') if user_info else 'test@example.com'
    
    # 進捗コールバック関数
    def progress_callback(progress):
        logger.info(f"📊 OCRテスト進捗: {progress.step} ({progress.progress_percent}%) - {progress.message}")
    
    try:
        with st.spinner("統一ワークフローエンジンでOCRテスト処理中..."):
            # サービスの初期化
            ai_service = get_gemini_api()
            storage_service = get_google_drive()
            database_service = get_database()
            
            # 統一ワークフローエンジン作成
            from core.workflows.unified_workflow_engine import UnifiedWorkflowEngine
            
            engine = UnifiedWorkflowEngine(
                ai_service=ai_service,
                storage_service=storage_service,
                database_service=database_service,
                progress_callback=progress_callback
            )

            st.info(f"📊 Google Driveフォルダ(ID: {folder_id})内の最大{max_files if max_files !=-1 else '全'}件のPDFファイルでテストを開始します")
            
            # 統一エンジンに処理を移管
            batch_result = engine.process_ocr_test_from_drive(
                folder_id=folder_id,
                user_id=user_id,
                max_files=max_files
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
    
    # UnifiedWorkflowEngineの結果表示（統合済み）
    st.markdown("### 📊 OCRテスト結果")
    
    # 基本統計の表示
    total_files = st.session_state.ocr_test_results.get('total_files', 0)
    successful_files = st.session_state.ocr_test_results.get('successful_files', 0)
    failed_files = st.session_state.ocr_test_results.get('failed_files', 0)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総ファイル数", total_files)
    with col2:
        st.metric("成功", successful_files, delta=f"{successful_files}/{total_files}")
    with col3:
        st.metric("失敗", failed_files, delta=f"{failed_files}/{total_files}")
    
    # 詳細結果の表示（簡易版）
    if 'results' in st.session_state.ocr_test_results:
        results = st.session_state.ocr_test_results['results']
        st.markdown("### 📋 処理結果詳細")
        
        for i, result in enumerate(results, 1):
            filename = result.get('filename', f'ファイル{i}')
            success = result.get('success', False)
            status_icon = "✅" if success else "❌"
            
            with st.expander(f"{status_icon} {filename}", expanded=False):
                if result.get('extracted_data'):
                    data = result['extracted_data']
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**請求元**: {data.get('issuer', 'N/A')}")
                        st.write(f"**請求書番号**: {data.get('invoice_number', 'N/A')}")
                    with col2:
                        amount = data.get('amount_inclusive_tax', 0)
                        st.write(f"**税込金額**: ¥{amount:,}" if amount else "**税込金額**: N/A")
                        st.write(f"**通貨**: {data.get('currency', 'JPY')}")
                
                if result.get('error_message'):
                    st.error(f"エラー: {result['error_message']}")
    else:
        st.info("📄 処理結果がありません")


def render_basic_ocr_results(results, include_validation):
    """基本的なOCRテスト結果表示（フォールバック）"""
    st.markdown("### 📊 OCRテスト結果（基本表示）")
    
    if isinstance(results, dict):
        # バッチ結果の場合
        batch_result = results
        total_files = batch_result.get('total_files', 0)
        successful_files = batch_result.get('successful_files', 0)
        failed_files = batch_result.get('failed_files', 0)
        
        # サマリー表示
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総ファイル数", total_files)
        with col2:
            st.metric("成功", successful_files, delta=None if successful_files == 0 else "✅")
        with col3:
            st.metric("失敗", failed_files, delta=None if failed_files == 0 else "❌")
        
        # 個別結果表示
        individual_results = batch_result.get('results', [])
        if individual_results:
            st.markdown("### 📋 ファイル別結果")
            for i, result in enumerate(individual_results, 1):
                filename = result.get('filename', f'ファイル{i}')
                success = result.get('success', False)
                status_icon = "✅" if success else "❌"
                
                with st.expander(f"{status_icon} {filename}", expanded=False):
                    if success:
                        ai_result = result.get('ai_result', {})
                        st.json(ai_result)
                        
                        if include_validation:
                            validation = result.get('validation', {})
                            if validation:
                                st.markdown("**検証結果:**")
                                st.json(validation)
                    else:
                        error = result.get('error', '不明なエラー')
                        st.error(f"エラー: {error}")
        
    elif isinstance(results, list):
        # 個別結果のリストの場合
        for result in results:
            if result.get('error'):
                st.error(f"❌ テスト失敗: {result['error']}")
            else:
                st.success("✅ OCRテスト完了")
                st.json(result) 