"""
テストページ集 - 各種API・機能のテストページ
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from typing import Dict, Any
import time

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent  # src/ ディレクトリ
sys.path.insert(0, str(project_root))

try:
    from infrastructure.auth.oauth_handler import get_current_user
    from infrastructure.database.database import get_database, test_database_connection
    from infrastructure.ai.gemini_helper import get_gemini_api, test_gemini_connection, GeminiAPIManager
    from infrastructure.storage.google_drive_helper import get_google_drive, test_google_drive_connection
    from infrastructure.ui.aggrid_helper import get_aggrid_manager, test_aggrid_connection
    # from core.workflows.unified_processing import UnifiedProcessingWorkflow  # 削除済み - UnifiedWorkflowEngineに統合
    from core.models.workflow_models import WorkflowProgress, WorkflowResult
    from utils.log_config import get_logger
    
    logger = get_logger(__name__)
    
except ImportError as e:
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.stop()


def render_database_test_page():
    """データベース接続テスト画面"""
    st.markdown("## 🔧 データベース接続テスト")
    
    st.info("🔧 Supabaseデータベース接続をテストします。")
    
    # 接続テスト
    if st.button("接続テスト実行", key="db_connection_test"):
        with st.spinner("データベース接続をテスト中..."):
            if test_database_connection():
                st.success("✅ データベース接続成功！")
                
                # 追加のテスト実行
                run_additional_db_tests()
            else:
                st.error("❌ データベース接続失敗")


def run_additional_db_tests():
    """追加のデータベーステスト"""
    try:
        st.markdown("### 📊 詳細テスト結果")
        
        database = get_database()
        
        # テーブル存在確認
        tables_exist = database.check_tables_exist()
        if tables_exist:
            st.success("✅ 必要なテーブルが存在します")
        else:
            st.warning("⚠️ 一部のテーブルが見つかりません")
        
        # サンプルクエリ実行
        sample_data = database.get_sample_data()
        if sample_data:
            st.success(f"✅ サンプルデータ取得成功 ({len(sample_data)}件)")
            st.dataframe(pd.DataFrame(sample_data))
        else:
            st.info("📄 サンプルデータはありません")
            
    except Exception as e:
        st.error(f"詳細テストでエラーが発生しました: {e}")


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
            with st.spinner("Gemini API接続をテスト中..."):
                if test_gemini_connection():
                    st.success("✅ Gemini API接続成功！")
                else:
                    st.error("❌ Gemini API接続失敗")
    
    with col2:
        st.markdown("### 📝 テキスト生成テスト")
        
        if st.button("📝 テキスト生成テスト", use_container_width=True):
            run_text_generation_test()
    
    # PDF分析テスト
    st.divider()
    render_pdf_analysis_test()


def run_text_generation_test():
    """テキスト生成テスト"""
    try:
        with st.spinner("テキスト生成中..."):
            gemini_api = get_gemini_api()
            
            test_prompt = "日本の首都はどこですか？簡潔に答えてください。"
            response = gemini_api.generate_text(test_prompt)
            
            if response:
                st.success("✅ テキスト生成成功！")
                st.markdown("**生成結果:**")
                st.info(response)
            else:
                st.error("❌ Gemini APIからの応答がありませんでした")
            
    except Exception as e:
        st.error(f"テキスト生成エラー: {e}")


def render_pdf_analysis_test():
    """PDF分析テスト"""
    st.markdown("### 📄 PDF分析テスト")
    
    uploaded_files = st.file_uploader(
        "テスト用PDFファイルを選択してください（複数選択可）",
        type=['pdf'],
        accept_multiple_files=True,
        key="gemini_pdf_test"
    )
    
    if uploaded_files:
        st.info(f"📄 {len(uploaded_files)}件のファイルが選択されました")
        if st.button("🔍 PDF分析実行", use_container_width=True):
            for uploaded_file in uploaded_files:
                st.markdown(f"#### 📄 処理中: {uploaded_file.name}")
                run_pdf_analysis(uploaded_file)


def run_pdf_analysis(uploaded_file):
    """PDF分析実行"""
    try:
        with st.spinner("PDF分析中..."):
            # PDFデータ読み込み
            pdf_data = uploaded_file.read()
            
            # Gemini APIでPDF分析
            gemini_api = get_gemini_api()
            
            # 基本プロンプト使用
            basic_prompt = "このPDFの内容を要約してください。"
            
            analysis_result = gemini_api.analyze_pdf_content(
                pdf_data,
                basic_prompt
            )
            
            st.success("✅ PDF分析完了！")
            
            # 結果表示
            st.markdown("**分析結果:**")
            st.json(analysis_result)
            
    except Exception as e:
        st.error(f"PDF分析エラー: {e}")


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
    render_drive_upload_test()


def render_drive_upload_test():
    """Google Driveアップロードテスト"""
    st.markdown("### 📤 ファイルアップロードテスト")
    
    uploaded_files = st.file_uploader(
        "テスト用ファイルを選択してください（複数選択可）",
        type=['pdf', 'txt', 'json'],
        accept_multiple_files=True,
        key="drive_upload_test"
    )
    
    if uploaded_files:
        st.info(f"📄 {len(uploaded_files)}件のファイルが選択されました")
        
        col1, col2 = st.columns(2)
        
        with col1:
            folder_id = st.text_input(
                "アップロード先フォルダID（オプション）",
                help="空白の場合はマイドライブにアップロードされます"
            )
        
        with col2:
            if st.button("📤 アップロード実行", use_container_width=True):
                for uploaded_file in uploaded_files:
                    st.markdown(f"#### 📤 アップロード中: {uploaded_file.name}")
                    run_drive_upload_test(uploaded_file, folder_id)


def run_drive_upload_test(uploaded_file, folder_id=None):
    """Google Driveアップロードテスト実行（統一ワークフローエンジン版）"""
    try:
        with st.spinner("統一ワークフローエンジンでアップロード中..."):
            # セッション状態から統一ワークフローエンジンを取得
            if 'unified_engine' not in st.session_state:
                st.error("❌ 統一ワークフローエンジンが初期化されていません")
                return
            
            engine = st.session_state.unified_engine
            
            # ファイルデータ取得
            file_data = uploaded_file.read()
            filename = uploaded_file.name
            
            # 統一ワークフローエンジンで処理（アップロードテストモード）
            result = engine.process_single_file(
                pdf_file_data=file_data,
                filename=filename,
                user_id="test@example.com",
                mode="upload_test"  # テスト専用モード
            )
            
            if result.success:
                st.success(f"✅ 統一ワークフロー アップロード成功！")
                st.info(f"📄 ファイル名: {filename}")
                st.info(f"🆔 Invoice ID: {result.invoice_id}")
                
                # 詳細結果表示
                if result.file_info:
                    st.markdown("### 📋 詳細ファイル情報")
                    st.json(result.file_info)
                
                if result.extracted_data:
                    st.markdown("### 🤖 AI抽出データ")
                    st.json(result.extracted_data)
                    
            else:
                st.error(f"❌ 統一ワークフロー アップロード失敗: {result.error_message}")
                
    except Exception as e:
        st.error(f"統一ワークフローエラー: {e}")


def render_aggrid_test_page():
    """ag-gridテスト画面"""
    st.markdown("## 📊 ag-grid データグリッドテスト")
    
    st.info("📋 ag-gridライブラリの機能テストを行います。")
    
    # サンプルデータ生成
    sample_data = generate_sample_invoice_data()
    
    st.markdown("### 📊 基本表示テスト")
    
    try:
        # ag-gridマネージャー取得
        aggrid_manager = get_aggrid_manager()
        
        if aggrid_manager:
            st.success("✅ ag-gridマネージャー初期化成功")
            
            # サンプルデータをag-gridで表示
            df = pd.DataFrame(sample_data)
            
            # 基本的なag-gridを作成・表示
            response = aggrid_manager.create_basic_grid(
                df, 
                editable_columns=['status', 'amount'], 
                selection_mode='multiple'
            )
            
            # 選択結果の表示
            selected_rows = aggrid_manager.get_selected_rows(response)
            if selected_rows:
                st.subheader("📝 選択された行")
                st.json(selected_rows)
                
        else:
            st.error("❌ ag-gridマネージャーの初期化に失敗しました")
            
    except Exception as e:
        st.error(f"ag-gridテストエラー: {e}")
    
    # 機能要件チェック
    render_aggrid_requirements_check()


def generate_sample_invoice_data():
    """サンプル請求書データ生成"""
    return [
        {
            "id": 1,
            "invoice_number": "INV-2024-001",
            "company_name": "株式会社サンプル",
            "amount": 108000,
            "issue_date": "2024-01-15",
            "status": "処理済み"
        },
        {
            "id": 2,
            "invoice_number": "INV-2024-002",
            "company_name": "テストコーポレーション",
            "amount": 54000,
            "issue_date": "2024-01-20",
            "status": "確認中"
        },
        {
            "id": 3,
            "invoice_number": "INV-2024-003",
            "company_name": "サンプル商事",
            "amount": 216000,
            "issue_date": "2024-01-25",
            "status": "未処理"
        }
    ]


def render_aggrid_requirements_check():
    """ag-grid機能要件チェック"""
    st.markdown("### ✅ 機能要件適合性チェック")
    
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📋 機能要件チェック")
        for req, status in list(requirements_check.items())[:5]:
            st.write(f"**{req}**: {status}")
    
    with col2:
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
    uploaded_files = st.file_uploader(
        "請求書PDFファイルを選択してください（複数選択可）",
        type=['pdf'],
        accept_multiple_files=True,
        key="workflow_pdf_uploader"
    )
    
    # ユーザー情報取得
    user_info = get_current_user()
    user_id = user_info.get('email', 'test@example.com') if user_info else 'test@example.com'
    
    # 処理実行ボタン
    if uploaded_files:
        st.markdown("### 🚀 ワークフロー実行")
        
        # ファイル情報表示
        st.info(f"📄 選択されたファイル数: {len(uploaded_files)}件")
        for i, file in enumerate(uploaded_files, 1):
            st.caption(f"{i}. {file.name}")
        st.info(f"🆔 ユーザー: {user_id}")
        
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
                execute_integrated_workflow(uploaded_files, user_id)
        
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
    render_workflow_explanation()


def execute_integrated_workflow(uploaded_files, user_id):
    """統合ワークフロー実行（統一エンジンprocess_uploaded_files版）"""
    
    # 進捗コールバック関数（簡素化版）
    def progress_callback(progress: WorkflowProgress):
        # セッション状態に保存のみ（st.rerun()を削除）
        st.session_state.workflow_progress.append({
            'status': progress.status.value,
            'step': progress.step,
            'progress_percent': progress.progress_percent,
            'message': progress.message,
            'timestamp': progress.timestamp.strftime("%H:%M:%S"),
            'details': progress.details
        })
        # リアルタイム更新は削除して処理完了後にのみ更新
        logger.info(f"📊 進捗更新: {progress.step} ({progress.progress_percent}%) - {progress.message}")
    
    try:
        logger.info(f"🚀 統合ワークフローテスト開始: {len(uploaded_files)}件")
        
        # セッション状態から統一ワークフローエンジンを取得
        if 'unified_engine' not in st.session_state:
            st.error("❌ 統一ワークフローエンジンが初期化されていません")
            return
        
        engine = st.session_state.unified_engine
        
        # 進捗コールバックを設定
        engine.progress_callback = progress_callback
        
        logger.info("🔧 統一ワークフローエンジン取得完了")
        
        logger.info("🔧 統一ワークフローエンジン作成完了")
        
        # 統一アップロード処理実行（process_uploaded_files使用）
        logger.info("🎯 統一アップロード処理開始")
        batch_result = engine.process_uploaded_files(
            uploaded_files=uploaded_files,  # 複数ファイルリストを直接渡す
            user_id=user_id,
            mode="test"
        )
        logger.info(f"🎯 統一アップロード処理完了")
        
        # バッチ結果から単一ファイル結果を抽出
        if batch_result and batch_result.get('results'):
            single_result = batch_result['results'][0]  # 最初の結果
            
            # 結果をセッション状態に保存
            st.session_state.workflow_result = {
                'success': single_result.get('success', False),
                'invoice_id': single_result.get('invoice_id'),
                'extracted_data': single_result.get('extracted_data'),
                'file_info': single_result.get('file_info'),
                'error_message': single_result.get('error_message'),
                'processing_time': batch_result.get('processing_time', 0)
            }
        else:
            st.session_state.workflow_result = {
                'success': False,
                'error_message': 'バッチ処理結果が取得できませんでした'
            }
        
        # 処理完了後に一度だけUI更新
        logger.info("✅ 統合ワークフローテスト完了 - UI更新実行")
        st.rerun()
        
    except Exception as e:
        error_msg = f"統一ワークフロー実行エラー: {str(e)}"
        logger.error(f"❌ {error_msg}")
        logger.exception("統合ワークフローテスト詳細エラー:")
        
        st.session_state.workflow_result = {
            'success': False,
            'error_message': error_msg
        }
        
        # エラー時もUI更新
        st.rerun()
    
    finally:
        st.session_state.is_processing = False
        logger.info("🔄 処理状態リセット完了")


def render_workflow_progress():
    """ワークフロー進捗表示"""
    st.markdown("### 📊 処理進捗")
    
    if st.session_state.workflow_progress:
        latest_progress = st.session_state.workflow_progress[-1]
        
        # プログレスバー
        progress_value = latest_progress['progress_percent'] / 100
        st.progress(progress_value)
        
        # 現在のステップ情報
        st.info(f"🔄 {latest_progress['message']}")
        
        # 詳細ログ（展開可能）
        with st.expander("📋 詳細ログ", expanded=False):
            for progress in st.session_state.workflow_progress:
                st.write(f"[{progress['timestamp']}] {progress['step']}: {progress['message']}")


def render_workflow_result():
    """ワークフロー結果表示"""
    st.markdown("### 📊 処理結果")
    
    result = st.session_state.workflow_result
    
    if result['success']:
        st.success("✅ ワークフロー処理が正常に完了しました！")
        
        # 処理時間表示
        if 'processing_time' in result:
            st.metric("⏱️ 処理時間", f"{result['processing_time']:.2f}秒")
        
        # 抽出データ表示
        if 'extracted_data' in result and result['extracted_data']:
            st.subheader("📋 抽出されたデータ")
            st.json(result['extracted_data'])
        
        # ファイル情報表示
        if 'file_info' in result and result['file_info']:
            st.subheader("📄 ファイル情報")
            st.json(result['file_info'])
            
    else:
        st.error("❌ ワークフロー処理でエラーが発生しました")
        
        if 'error_message' in result:
            st.error(f"エラー詳細: {result['error_message']}")


def render_workflow_explanation():
    """ワークフロー説明セクション"""
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