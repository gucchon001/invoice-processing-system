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
    from core.services.unified_prompt_manager import UnifiedPromptManager, PromptSelector
    from utils.log_config import get_logger
    from utils.ocr_test_helper import OCRTestManager
    
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
            # セッション状態から統一ワークフローエンジンを取得
            if 'unified_engine' not in st.session_state:
                st.error("❌ 統一ワークフローエンジンが初期化されていません")
                return
            
            engine = st.session_state.unified_engine
            
            # 進捗コールバックを設定
            engine.progress_callback = progress_callback
            
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
            # セッション状態から統一ワークフローエンジンを取得
            if 'unified_engine' not in st.session_state:
                st.error("❌ 統一ワークフローエンジンが初期化されていません")
                return
            
            engine = st.session_state.unified_engine
            
            # 進捗コールバックを設定
            engine.progress_callback = progress_callback

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
    """統一アップロード結果表示（WorkflowDisplayManager統合版）"""
    if not st.session_state.unified_processing_results:
        return
    
    # 統一ワークフローエンジンの結果を直接表示
    try:
        batch_result = st.session_state.unified_processing_results
        
        st.markdown("### 📊 バッチ処理結果")
        
        # サマリー表示
        total_files = batch_result.get('total_files', 0)
        successful_files = batch_result.get('successful_files', 0)
        failed_files = total_files - successful_files
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 総ファイル数", total_files)
        
        with col2:
            st.metric("✅ 成功", successful_files)
        
        with col3:
            st.metric("❌ 失敗", failed_files)
        
        with col4:
            processing_time = batch_result.get('total_processing_time', 0)
            st.metric("⏱️ 処理時間", f"{processing_time:.2f}秒")
        
        # 成功率表示
        if total_files > 0:
            success_rate = (successful_files / total_files) * 100
            if success_rate >= 90:
                st.success(f"🎉 成功率: {success_rate:.1f}%")
            elif success_rate >= 70:
                st.warning(f"⚠️ 成功率: {success_rate:.1f}%")
            else:
                st.error(f"⚠️ 成功率: {success_rate:.1f}%")
        
        # 詳細結果表示
        results = batch_result.get('results', [])
        if results:
            st.markdown("### 📋 ファイル別詳細結果")
            
            for i, result in enumerate(results, 1):
                filename = result.get('filename', f'ファイル{i}')
                success = result.get('success', False)
                
                if success:
                    with st.expander(f"✅ {filename} - 処理成功", expanded=False):
                        # 拡張プレビュー機能付きタブ表示（本番アップロード用）
                        render_enhanced_result_tabs(result, filename)
                else:
                    with st.expander(f"❌ {filename} - 処理失敗", expanded=False):
                        _display_error_result(result)
                        
    except Exception as e:
        logger.error(f"バッチ結果表示エラー: {e}")
        st.error(f"結果表示エラー: {e}")


def _display_success_result(result: Dict[str, Any]):
    """成功結果の表示（WorkflowDisplayManager統合版）"""
    st.success("✅ 処理成功")
    
    filename = result.get('filename', 'N/A')
    st.write(f"**ファイル名:** {filename}")
    
    processing_time = result.get('processing_time', 0)
    st.write(f"**処理時間:** {processing_time:.2f}秒")
    
    # 抽出データ表示
    extracted_data = result.get('extracted_data', {})
    if extracted_data:
        st.markdown("**📄 抽出された主要情報:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"• 供給者名: {extracted_data.get('issuer', 'N/A')}")
            st.write(f"• 請求書番号: {extracted_data.get('main_invoice_number', 'N/A')}")
            st.write(f"• 受領書番号: {extracted_data.get('receipt_number', 'N/A')}")
            st.write(f"• T番号: {extracted_data.get('t_number', 'N/A')}")
            st.write(f"• 通貨: {extracted_data.get('currency', 'JPY')}")
            
        with col2:
            st.write(f"• 請求先: {extracted_data.get('payer', 'N/A')}")
            st.write(f"• 税込金額: {extracted_data.get('amount_inclusive_tax', 'N/A')}")
            st.write(f"• 請求日: {extracted_data.get('issue_date', 'N/A')}")
            # キー情報の簡易表示
            key_info = extracted_data.get('key_info', {})
            if key_info:
                st.write(f"• キー情報: 有り（{len(key_info)}項目）")
            else:
                st.write(f"• キー情報: なし")
    
    # 検証結果表示
    validation_result = result.get('validation_result')
    if validation_result:
        _display_validation_result(validation_result)


def _display_error_result(result: Dict[str, Any]):
    """エラー結果の表示（WorkflowDisplayManager統合版）"""
    st.error("❌ 処理失敗")
    
    filename = result.get('filename', 'N/A')
    st.write(f"**ファイル名:** {filename}")
    
    # 複数の可能性があるエラーメッセージキーをチェック
    error_message = (result.get('error_message') or 
                    result.get('error') or 
                    result.get('error_details') or 
                    '詳細不明')
    st.error(f"エラー内容: {error_message}")
    
    # エラー詳細がある場合
    error_details = result.get('error_details')
    if error_details:
        with st.expander("エラー詳細"):
            st.code(str(error_details))


def _display_validation_result(validation_result: Dict[str, Any]):
    """検証結果の表示（WorkflowDisplayManager統合版）"""
    st.markdown("**🔍 検証結果:**")
    
    is_valid = validation_result.get('is_valid', False)
    
    if is_valid:
        st.success("✅ 検証: 合格")
    else:
        st.warning("⚠️ 検証: 注意が必要")
    
    # 警告・エラー表示
    warnings = validation_result.get('warnings', [])
    errors = validation_result.get('errors', [])
    
    if warnings:
        st.markdown("**⚠️ 警告:**")
        for warning in warnings:
            st.warning(f"• {warning}")
    
    if errors:
        st.markdown("**❌ エラー:**")
        for error in errors:
            st.error(f"• {error}")
    
    # スコア表示
    score = validation_result.get('score', 0)
    if score > 0:
        st.write(f"**📊 品質スコア:** {score:.1f}/100")


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
                    # 詳細プレビュー機能付きタブ表示
                    render_enhanced_result_tabs(result, filename)
                
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


def render_enhanced_result_tabs(result: Dict[str, Any], filename: str):
    """拡張プレビュー機能付き結果表示（タブ分割）"""
    tab1, tab2, tab3, tab4 = st.tabs(["📋 基本情報", "📊 明細", "🔍 JSON", "📄 PDF"])
    
    extracted_data = result.get('extracted_data', {})
    
    with tab1:
        # 基本情報表示（統一化フィールド対応）
        render_basic_info_enhanced(extracted_data)
    
    with tab2:
        # 明細情報表示
        render_line_items_enhanced(extracted_data)
    
    with tab3:
        # JSON詳細表示
        render_json_preview_enhanced(result, extracted_data)
    
    with tab4:
        # PDF プレビュー
        render_pdf_preview_enhanced(result, filename)


def render_basic_info_enhanced(extracted_data: Dict[str, Any]):
    """拡張基本情報表示"""
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
        
        st.write(f"• 税込金額: ¥{amount_inc:,}" if amount_inc else "• 税込金額: N/A")
        st.write(f"• 税抜金額: ¥{amount_exc:,}" if amount_exc else "• 税抜金額: N/A")
        st.write(f"• 消費税額: ¥{tax_amount:,}" if tax_amount else "• 消費税額: N/A")
        st.write(f"• 通貨: {extracted_data.get('currency', 'JPY')}")
        st.write(f"• 請求日: {extracted_data.get('issue_date', 'N/A')}")
    
    # キー情報の表示
    key_info = extracted_data.get('key_info', {})
    if key_info:
        st.markdown("**🔑 キー情報**")
        if isinstance(key_info, dict) and key_info:
            st.write(f"• 項目数: {len(key_info)}項目")
            with st.expander("詳細を表示", expanded=False):
                for key, value in key_info.items():
                    st.write(f"  - {key}: {value}")
        else:
            st.write("• キー情報: なし")


def render_line_items_enhanced(extracted_data: Dict[str, Any]):
    """拡張明細表示"""
    line_items = extracted_data.get('line_items', [])
    
    if line_items:
        st.markdown(f"**📊 明細情報 ({len(line_items)}件)**")
        
        # DataFrameに変換
        import pandas as pd
        line_items_df = pd.DataFrame([
            {
                "No.": i+1,
                "商品・サービス名": item.get("item_description", item.get("description", "")),
                "数量": item.get("quantity", ""),
                "単価": item.get("unit_price", ""),
                "金額": item.get("amount", ""),
                "税率": item.get("tax_rate", "")
            }
            for i, item in enumerate(line_items)
        ])
        
        # ag-gridで表示
        try:
            from infrastructure.ui.aggrid_helper import get_aggrid_manager
            aggrid_manager = get_aggrid_manager()
            aggrid_manager.create_data_grid(
                line_items_df,
                editable=False,
                fit_columns_on_grid_load=True,
                height=300
            )
        except ImportError:
            # ag-gridが利用できない場合は標準表示
            st.dataframe(line_items_df, use_container_width=True)
        except Exception as e:
            st.warning(f"ag-grid表示エラー: {str(e)}")
            st.dataframe(line_items_df, use_container_width=True)
    else:
        st.info("📋 このファイルには明細データがありません")


def render_json_preview_enhanced(result: Dict[str, Any], extracted_data: Dict[str, Any]):
    """拡張JSON表示"""
    st.markdown("**🔍 抽出データ詳細**")
    
    # JSON表示オプション
    col1, col2 = st.columns(2)
    with col1:
        show_extracted = st.checkbox("抽出データ", value=True, key=f"show_extracted_{id(result)}")
    with col2:
        show_raw = st.checkbox("生レスポンス", value=False, key=f"show_raw_{id(result)}")
    
    if show_extracted:
        st.markdown("**📋 構造化抽出データ**")
        st.json(extracted_data)
    
    if show_raw:
        raw_response = result.get('raw_response', {})
        if raw_response:
            st.markdown("**🔧 AI生レスポンス**")
            st.json(raw_response)
        else:
            st.info("生レスポンスデータがありません")
    
    # 検証結果があれば表示
    validation_result = result.get('validation_result', {})
    if validation_result:
        st.markdown("**✅ 検証結果**")
        st.json(validation_result)


def render_pdf_preview_enhanced(result: Dict[str, Any], filename: str):
    """拡張PDFプレビュー"""
    st.markdown("**📄 PDF原本プレビュー**")
    
    # ファイル情報表示
    file_info = result.get('file_info', {})
    if file_info:
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**ファイル名**: {filename}")
            file_size = file_info.get('file_size', 0)
            if file_size:
                st.write(f"**ファイルサイズ**: {file_size:,} bytes")
        with col2:
            file_id = file_info.get('file_id', '')
            if file_id:
                st.write(f"**ファイルID**: {file_id}")
    
    # PDF表示の試行
    if st.button(f"📄 {filename} を表示", key=f"show_pdf_{id(result)}"):
        try:
            # Google Driveからファイル取得を試行
            google_drive = get_google_drive()
            if google_drive and file_info.get('file_id'):
                with st.spinner("PDFを読み込み中..."):
                    # ファイルをダウンロード
                    pdf_content = google_drive.download_file(file_info['file_id'])
                    
                    if pdf_content:
                        # ダウンロードボタン
                        st.download_button(
                            label="📥 PDFをダウンロード",
                            data=pdf_content,
                            file_name=filename,
                            mime="application/pdf",
                            key=f"download_{id(result)}"
                        )
                        
                        # PDFビューアー
                        import base64
                        base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
                        pdf_display = f'''
                        <div style="border: 1px solid #ccc; border-radius: 5px; margin: 10px 0;">
                            <iframe 
                                src="data:application/pdf;base64,{base64_pdf}" 
                                width="100%" 
                                height="600px" 
                                style="border: none;">
                                <p>PDFを表示できません。ダウンロードしてご確認ください。</p>
                            </iframe>
                        </div>
                        '''
                        st.markdown(pdf_display, unsafe_allow_html=True)
                        st.success("✅ PDF表示完了")
                    else:
                        st.error("📥 PDFファイルの取得に失敗しました")
            else:
                st.warning("🔧 Google Driveマネージャーまたはファイル情報が利用できません")
                st.info("OCRテスト時のファイル情報が不足している可能性があります")
        
        except Exception as e:
            st.error(f"PDF表示エラー: {str(e)}")
            logger.error(f"PDF表示エラー: {e}") 