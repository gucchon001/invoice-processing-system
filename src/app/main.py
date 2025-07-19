"""
請求書処理自動化システム - メインアプリケーション
streamlit-oauth統一認証版

開発・本番環境で統一されたOAuth認証システムを使用した
請求書処理自動化システムのメインアプリケーション
"""

import streamlit as st
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加（新しい構造対応）
project_root = Path(__file__).parent.parent  # src/ ディレクトリ
sys.path.insert(0, str(project_root))

# 新しい構造でのモジュールインポート
try:
    from infrastructure.auth.oauth_handler import require_auth, get_current_user, logout, is_authenticated
    from infrastructure.database.database import get_database, test_database_connection
    from infrastructure.ai.gemini_helper import get_gemini_api, test_gemini_connection, generate_text_simple, extract_pdf_invoice_data
    from infrastructure.storage.google_drive_helper import get_google_drive, test_google_drive_connection, upload_pdf_to_drive, get_drive_files_list
except ImportError as e:
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
            "⚙️ メール設定",
            "🔧 DB接続テスト",
            "🤖 Gemini APIテスト",
            "☁️ Google Drive APIテスト"
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
        
        # 処理開始ボタン
        if st.button("🚀 AI処理を開始", type="primary", use_container_width=True):
            with st.spinner("ファイルを処理中..."):
                # TODO: 実際の処理ロジックを実装
                st.success("✅ アップロードと処理を開始しました！")
                st.info("📊 処理状況は「処理状況ダッシュボード」で確認できます。")


def render_dashboard_page():
    """処理状況ダッシュボード画面"""
    st.markdown("## 📊 処理状況ダッシュボード")
    
    st.info("📋 アップロードした請求書の処理状況を確認・編集できます。")
    
    # サンプルデータ（TODO: 実際のデータベースから取得）
    import pandas as pd
    
    sample_data = pd.DataFrame({
        'ID': [1, 2, 3],
        'ファイル名': ['invoice_001.pdf', 'invoice_002.pdf', 'invoice_003.pdf'],
        '請求元': ['株式会社Example', 'Google LLC', 'Microsoft Corporation'],
        '金額': [100000, 50000, 75000],
        'ステータス': ['AI提案済み', '処理中', '要確認'],
        'アップロード日時': ['2025-01-15 10:00', '2025-01-15 11:30', '2025-01-15 14:15']
    })
    
    # データ表示（将来はst.data_editorを使用予定）
    st.dataframe(
        sample_data,
        use_container_width=True,
        hide_index=True
    )
    
    # 機能ボタン
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 データ更新", use_container_width=True):
            st.success("データを更新しました")
    
    with col2:
        if st.button("📄 PDFを確認", use_container_width=True):
            st.info("PDF確認機能は実装予定です")
    
    with col3:
        if st.button("💾 変更を保存", use_container_width=True):
            st.success("変更を保存しました")


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
                    
                    if df_data:
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


def main():
    """メインアプリケーション"""
    
    # ページ設定
    configure_page()
    
    # タイトル
    st.title("📄 請求書処理自動化システム")
    st.markdown("---")
    
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