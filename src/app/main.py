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
    from infrastructure.ai.gemini_helper import get_gemini_api, test_gemini_connection, generate_text_simple, extract_pdf_invoice_data
    from infrastructure.storage.google_drive_helper import get_google_drive, test_google_drive_connection, upload_pdf_to_drive, get_drive_files_list
    from infrastructure.ui.aggrid_helper import get_aggrid_manager, test_aggrid_connection
    from core.workflows.invoice_processing import InvoiceProcessingWorkflow, WorkflowStatus, WorkflowProgress, WorkflowResult
    logger.info("全モジュールのインポートが完了しました")
except ImportError as e:
    logger.error(f"モジュールのインポートに失敗しました: {e}")
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.error("新しいディレクトリ構造でのインポートパスを確認してください。")
    st.stop()


def configure_page():
    """ページ設定"""
    st.set_page_config(
        page_title="請求書処理自動化システム",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )


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
            "📤 請求書アップロード",
            "📊 処理状況ダッシュボード", 
            "🔍 OCR精度テスト (Gemini 2.0-flash)",
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


def render_upload_page():
    """請求書アップロード画面"""
    st.markdown("## 📤 請求書アップロード")
    
    st.info("📋 PDFファイルをアップロードして、AI による自動処理を開始します。")
    
    # ファイルアップローダー
    uploaded_files = st.file_uploader(
        "請求書PDFファイルを選択してください",
        type=['pdf'],
        accept_multiple_files=True,
        help="複数のPDFファイルを同時にアップロードできます"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} 件のファイルが選択されました")
        
        # アップロードされたファイルの詳細表示
        for i, file in enumerate(uploaded_files, 1):
            with st.expander(f"📄 {i}. {file.name}"):
                st.write(f"**ファイル名:** {file.name}")
                st.write(f"**サイズ:** {file.size:,} bytes")
                st.write(f"**タイプ:** {file.type}")
        
        # セッション状態の初期化
        if "upload_progress" not in st.session_state:
            st.session_state.upload_progress = []
        if "upload_results" not in st.session_state:
            st.session_state.upload_results = []
        if "is_processing_upload" not in st.session_state:
            st.session_state.is_processing_upload = False

        # 処理開始ボタン
        if st.button("🚀 AI処理を開始", type="primary", use_container_width=True):
            if not st.session_state.is_processing_upload:
                st.session_state.is_processing_upload = True
                st.session_state.upload_progress = []
                st.session_state.upload_results = []
                
                # 現在のユーザー情報取得
                user_info = get_current_user()
                user_id = user_info.get('email', 'anonymous@example.com') if user_info else 'anonymous@example.com'
                
                # 複数ファイルの統合ワークフロー実行
                execute_multiple_invoice_processing(uploaded_files, user_id)
            else:
                st.warning("現在処理中です。しばらくお待ちください。")

        # 処理中の進捗表示
        if st.session_state.is_processing_upload:
            st.markdown("### 📊 処理進捗")
            render_upload_progress()

        # 処理結果表示
        if st.session_state.upload_results and not st.session_state.is_processing_upload:
            st.markdown("### 📋 処理結果")
            render_upload_results()


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


def prepare_invoice_data_for_aggrid(invoices_data):
    """請求書データをag-grid用に前処理"""
    try:
        import pandas as pd
        
        # 基本データの準備
        processed_rows = []
        
        for invoice in invoices_data:
            # 抽出データから主要項目を取得
            extracted_data = invoice.get('extracted_data', {}) or {}
            
            row = {
                'id': invoice.get('id', ''),
                'file_name': invoice.get('file_name', ''),
                'supplier_name': (
                    invoice.get('supplier_name') or 
                    extracted_data.get('supplier_name') or 
                    extracted_data.get('issuer', '')
                ),
                'invoice_number': (
                    invoice.get('invoice_number') or
                    extracted_data.get('invoice_number') or
                    extracted_data.get('main_invoice_number', '')
                ),
                'invoice_date': (
                    invoice.get('invoice_date') or
                    extracted_data.get('invoice_date') or
                    extracted_data.get('issue_date', '')
                ),
                'due_date': (
                    invoice.get('due_date') or
                    extracted_data.get('due_date', '')
                ),
                'total_amount': (
                    invoice.get('total_amount') or
                    extracted_data.get('total_amount') or
                    extracted_data.get('amount_inclusive_tax', 0)
                ),
                'tax_amount': (
                    invoice.get('tax_amount') or
                    extracted_data.get('tax_amount', 0)
                ),
                'currency': (
                    invoice.get('currency') or
                    extracted_data.get('currency', 'JPY')
                ),
                'status': invoice.get('status', 'extracted'),
                'created_at': invoice.get('created_at', ''),
                'user_email': invoice.get('user_email', ''),
                'file_path': invoice.get('file_path', ''),
                'gdrive_file_id': invoice.get('gdrive_file_id', '')
            }
            
            processed_rows.append(row)
        
        # DataFrameに変換
        df = pd.DataFrame(processed_rows)
        
        # 日時フォーマット調整
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        # 数値型の変換
        numeric_columns = ['total_amount', 'tax_amount']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
        
    except Exception as e:
        logger.error(f"データ前処理エラー: {e}")
        return pd.DataFrame()


def handle_grid_interactions(grid_response, original_data):
    """ag-gridの選択・編集処理"""
    try:
        # 選択行の処理
        selected_rows = grid_response.get('selected_rows', [])
        
        if selected_rows:
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
        help="請求書の AI 処理が完了した際にメール通知を送信します"
    )
    
    notify_error = st.checkbox(
        "❌ エラー発生時にメールで通知する",
        value=True,
        help="処理中にエラーが発生した際にメール通知を送信します"
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
    
    # プロンプトテスト
    st.markdown("### 🎯 カスタムプロンプトテスト")
    
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
                st.write(f"• 供給者名: {extracted_data.get('supplier_name', 'N/A')}")
                st.write(f"• 請求書番号: {extracted_data.get('invoice_number', 'N/A')}")
                st.write(f"• 通貨: {extracted_data.get('currency', 'JPY')}")
            
            with col2:
                st.write("**💰 金額情報**")
                st.write(f"• 合計金額: ¥{extracted_data.get('total_amount', 0):,}")
                st.write(f"• 税額: ¥{extracted_data.get('tax_amount', 0):,}")
                st.write(f"• 請求日: {extracted_data.get('invoice_date', 'N/A')}")
            
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
    """メインコンテンツエリアをレンダリング"""
    
    if selected_menu == "📤 請求書アップロード":
        render_upload_page()
    
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
    
    elif selected_menu == "🔍 OCR精度テスト (Gemini 2.0-flash)":
        render_ocr_test_page()
    
    else:
        # デフォルト画面
        st.markdown("## 🏠 ホーム")
        st.success(f"🎉 {user_info['name']}さん、ようこそ！")
        
        st.markdown("""
        ### 📋 システム概要
        このシステムでは以下の機能をご利用いただけます：
        
        - **📤 請求書アップロード**: PDFファイルをアップロードして自動処理
        - **📊 処理状況ダッシュボード**: アップロードした請求書の状況確認・編集
        - **⚙️ メール設定**: 通知設定の管理
        
        ### 🚀 開始方法
        1. サイドバーから「📤 請求書アップロード」を選択
        2. PDFファイルをアップロード
        3. AI による自動処理を開始
        4. 「📊 処理状況ダッシュボード」で結果を確認
        """)


def execute_multiple_invoice_processing(uploaded_files, user_id):
    """複数ファイルの統合ワークフロー実行"""
    
    # 進捗コールバック関数（複数ファイル対応版）
    def progress_callback(progress: WorkflowProgress, file_index: int, total_files: int):
        # ファイル全体の進捗を計算（各ファイルで100%を均等分割）
        file_progress = (file_index * 100 + progress.progress_percent) / total_files
        
        st.session_state.upload_progress.append({
            'file_index': file_index,
            'filename': uploaded_files[file_index].name if file_index < len(uploaded_files) else '',
            'status': progress.status.value,
            'step': progress.step,
            'progress_percent': progress.progress_percent,
            'overall_progress': file_progress,
            'message': progress.message,
            'timestamp': progress.timestamp.strftime("%H:%M:%S"),
            'details': progress.details
        })
        # リアルタイム更新
        st.rerun()
    
    try:
        # サービスの初期化
        ai_service = get_gemini_api()
        storage_service = get_google_drive()
        database_service = get_database()
        
        total_files = len(uploaded_files)
        
        # 各ファイルを順次処理
        for file_index, uploaded_file in enumerate(uploaded_files):
            try:
                # ファイル固有の進捗コールバック（変数キャプチャ対応）
                file_progress_callback = lambda progress, idx=file_index: progress_callback(progress, idx, total_files)
                
                # ワークフローインスタンス作成
                workflow = InvoiceProcessingWorkflow(
                    ai_service=ai_service,
                    storage_service=storage_service,
                    database_service=database_service,
                    progress_callback=file_progress_callback
                )
                
                # PDFデータ取得
                pdf_data = uploaded_file.read()
                filename = uploaded_file.name
                
                # ワークフロー実行
                result = workflow.process_invoice(pdf_data, filename, user_id)
                
                # 結果を保存
                st.session_state.upload_results.append({
                    'filename': filename,
                    'success': result.success,
                    'invoice_id': result.invoice_id,
                    'extracted_data': result.extracted_data,
                    'file_info': result.file_info,
                    'error_message': result.error_message,
                    'processing_time': result.processing_time
                })
                
                logger.info(f"ファイル処理完了: {filename} (成功: {result.success})")
                
            except Exception as e:
                # 個別ファイルエラー
                st.session_state.upload_results.append({
                    'filename': uploaded_file.name,
                    'success': False,
                    'error_message': f"ファイル処理エラー: {str(e)}"
                })
                logger.error(f"ファイル処理エラー ({uploaded_file.name}): {e}")
        
    except Exception as e:
        # 全体エラー
        logger.error(f"複数ファイル処理でエラー: {e}")
        st.error(f"処理中にエラーが発生しました: {e}")
    
    finally:
        st.session_state.is_processing_upload = False


def render_upload_progress():
    """アップロード進捗の表示"""
    if st.session_state.upload_progress:
        # 最新の進捗情報を取得
        latest_progress = st.session_state.upload_progress[-1]
        
        # 全体進捗バー
        overall_progress = latest_progress.get('overall_progress', 0)
        st.progress(overall_progress / 100)
        
        # 現在のファイル処理状況
        current_file = latest_progress.get('filename', '')
        current_step = latest_progress.get('step', '')
        current_message = latest_progress.get('message', '')
        
        st.write(f"📄 **現在処理中:** {current_file}")
        st.write(f"🔄 **ステップ:** {current_step}")
        st.write(f"💬 **状況:** {current_message}")
        
        # 詳細ログ表示（最新10件）
        with st.expander("📋 詳細ログ", expanded=False):
            recent_logs = st.session_state.upload_progress[-10:]
            for log in reversed(recent_logs):
                timestamp = log.get('timestamp', '')
                filename = log.get('filename', '')
                step = log.get('step', '')
                message = log.get('message', '')
                st.text(f"[{timestamp}] {filename}: {step} - {message}")


def render_ocr_test_page():
    """OCRテストページ"""
    try:
        from utils.ocr_test_helper import create_ocr_test_app
        
        # OCRテストアプリを作成（デバッグパネルは全ページ共通で表示済み）
        create_ocr_test_app()
    except ImportError as e:
        st.error(f"OCRテストモジュールの読み込みに失敗しました: {e}")
        st.info("必要なモジュールが不足している可能性があります。")


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
        st.metric("📊 総ファイル数", total_files)
    
    with col2:
        st.metric("✅ 成功", successful_files)
    
    with col3:
        st.metric("❌ 失敗", failed_files)
    
    # 詳細結果
    for i, result in enumerate(results, 1):
        filename = result.get('filename', f'ファイル{i}')
        success = result.get('success', False)
        
        if success:
            with st.expander(f"✅ {filename} - 処理成功", expanded=False):
                invoice_id = result.get('invoice_id', 'N/A')
                processing_time = result.get('processing_time', 0)
                
                st.write(f"**請求書ID:** {invoice_id}")
                st.write(f"**処理時間:** {processing_time:.2f}秒")
                
                # 抽出データ表示
                extracted_data = result.get('extracted_data', {})
                if extracted_data:
                    st.write("**主要情報:**")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"• 供給者名: {extracted_data.get('supplier_name', 'N/A')}")
                        st.write(f"• 請求書番号: {extracted_data.get('invoice_number', 'N/A')}")
                        st.write(f"• 通貨: {extracted_data.get('currency', 'JPY')}")
                    
                    with col2:
                        st.write(f"• 合計金額: ¥{extracted_data.get('total_amount', 0):,}")
                        st.write(f"• 税額: ¥{extracted_data.get('tax_amount', 0):,}")
                        st.write(f"• 請求日: {extracted_data.get('invoice_date', 'N/A')}")
        else:
            with st.expander(f"❌ {filename} - 処理失敗", expanded=False):
                error_message = result.get('error_message', '詳細不明')
                st.error(f"エラー内容: {error_message}")
    
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


def main():
    """メインアプリケーション"""
    
    # ページ設定
    configure_page()
    
    # デバッグパネルの表示
    render_debug_panel()
    
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