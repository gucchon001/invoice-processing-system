"""
請求書処理自動化システム - メインアプリケーション（リファクタリング版）
streamlit-oauth統一認証版

機能別に分割されたモジュールを統合するエントリーポイント
"""

import streamlit as st
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent  # src/ ディレクトリ
app_root = Path(__file__).parent  # src/app/ ディレクトリ
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(app_root))

# 現在のディレクトリも追加（念のため）
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ログ設定の初期化
try:
    from utils.log_config import setup_logging, get_logger, get_log_config
    from utils.debug_panel import render_debug_panel
    setup_logging()
    logger = get_logger(__name__)
    logger.info("請求書処理自動化システムが開始されました（リファクタリング版）")
    
    # デバッグモードの確認
    log_config = get_log_config()
    if log_config.is_debug_mode():
        logger.debug("デバッグモードが有効です")
        
except ImportError as e:
    print(f"ログ設定モジュールのインポートに失敗しました: {e}")
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# 認証・インフラモジュールのインポート
try:
    from infrastructure.auth.oauth_handler import require_auth
    from infrastructure.database.database import get_database
    from infrastructure.ai.gemini_helper import GeminiAPIManager
    from infrastructure.storage.google_drive_helper import get_google_drive
    
    # 統一コンポーネントのインポート
    from core.services.unified_prompt_manager import UnifiedPromptManager
    from core.services.prompt_selector import PromptSelector
    from core.workflows.unified_processing import UnifiedProcessingWorkflow
    from core.services.workflow_display_manager import WorkflowDisplayManager
    
    logger.info("全モジュールのインポートが完了しました（リファクタリング版）")
    
except ImportError as e:
    logger.error(f"モジュールのインポートに失敗しました: {e}")
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.stop()

# 分割されたページ・コンポーネントのインポート
try:
    # デバッグ: 現在のパスとディレクトリ構造を確認
    import sys
    import os
    logger.info(f"現在の作業ディレクトリ: {os.getcwd()}")
    logger.info(f"__file__の場所: {__file__}")
    logger.info(f"Pythonパス: {sys.path[:3]}...")  # 最初の3つのパスを表示
    
    # 現在のファイルがあるディレクトリ（src/app）を取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"main.pyのディレクトリ: {current_dir}")
    
    # pages と components のディレクトリを確認
    pages_dir = os.path.join(current_dir, 'pages')
    components_dir = os.path.join(current_dir, 'components')
    logger.info(f"pagesディレクトリが存在: {os.path.exists(pages_dir)}")
    logger.info(f"componentsディレクトリが存在: {os.path.exists(components_dir)}")
    
    # 現在のディレクトリをPythonパスに追加（確実にするため）
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        logger.info(f"パスに追加: {current_dir}")
    
    # インポートを実行
    import pages.invoice_processing as invoice_processing
    import pages.settings as settings  
    import pages.test_pages as test_pages
    import components.sidebar as sidebar
    
    # 関数を明示的に取得
    render_unified_invoice_processing_page = invoice_processing.render_unified_invoice_processing_page
    render_dashboard_page = settings.render_dashboard_page
    render_settings_page = settings.render_settings_page
    render_database_test_page = test_pages.render_database_test_page
    render_gemini_test_page = test_pages.render_gemini_test_page
    render_google_drive_test_page = test_pages.render_google_drive_test_page
    render_aggrid_test_page = test_pages.render_aggrid_test_page
    render_integrated_workflow_test_page = test_pages.render_integrated_workflow_test_page
    render_sidebar = sidebar.render_sidebar
    
    logger.info("分割されたページ・コンポーネントのインポートが完了しました")
    
except ImportError as e:
    logger.error(f"ページ・コンポーネントのインポートに失敗しました: {e}")
    logger.error(f"詳細エラー: {type(e).__name__}: {str(e)}")
    
    # デバッグ情報をStreamlitにも表示
    st.error(f"ページ・コンポーネントのインポートに失敗しました: {e}")
    st.error("リファクタリング後のモジュール構造を確認してください。")
    
    # ディレクトリ構造の確認
    current_dir = os.path.dirname(os.path.abspath(__file__))
    st.info(f"現在のディレクトリ: {current_dir}")
    st.info(f"pagesディレクトリが存在: {os.path.exists(os.path.join(current_dir, 'pages'))}")
    st.info(f"componentsディレクトリが存在: {os.path.exists(os.path.join(current_dir, 'components'))}")
    
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
            st.session_state.prompt_manager = UnifiedPromptManager()
            logger.info("✅ プロンプトマネージャー初期化完了")
        
        if "prompt_selector" not in st.session_state:
            st.session_state.prompt_selector = PromptSelector(st.session_state.prompt_manager)
            logger.info("✅ プロンプトセレクター初期化完了")
        
        # 統合ワークフロー初期化
        if "unified_workflow" not in st.session_state:
            gemini_helper = GeminiAPIManager()
            database_manager = get_database()
            
            st.session_state.unified_workflow = UnifiedProcessingWorkflow(
                gemini_helper=gemini_helper,
                database_manager=database_manager
            )
            logger.info("✅ 統合ワークフロー初期化完了")
        
        # ワークフロー表示マネージャー初期化
        if "workflow_display" not in st.session_state:
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
                st.session_state.unified_workflow_ocr = None
        
        # OCR専用ワークフロー表示マネージャー初期化
        if "workflow_display_ocr" not in st.session_state:
            try:
                if st.session_state.unified_workflow_ocr is not None:
                    st.session_state.workflow_display_ocr = WorkflowDisplayManager(st.session_state.unified_workflow_ocr)
                    logger.info("✅ OCR専用ワークフロー表示マネージャー初期化完了")
                else:
                    st.session_state.workflow_display_ocr = None
                    logger.warning("⚠️ OCR専用ワークフロー表示マネージャー初期化スキップ（ワークフローが未初期化）")
            except Exception as e:
                logger.error(f"❌ OCR専用ワークフロー表示マネージャー初期化エラー: {e}")
                st.session_state.workflow_display_ocr = None
        
        # 🚀 統一ワークフローエンジン初期化（新システム）
        if "unified_engine" not in st.session_state:
            try:
                from core.workflows.unified_workflow_engine import UnifiedWorkflowEngine
                
                gemini_api = GeminiAPIManager()
                
                st.session_state.unified_engine = UnifiedWorkflowEngine(
                    ai_service=gemini_api,
                    storage_service=get_google_drive(),
                    database_service=get_database()
                )
                logger.info("✅ 統一ワークフローエンジン初期化完了")
                
            except Exception as e:
                logger.error(f"❌ 統一ワークフローエンジン初期化エラー: {e}")
                st.session_state.unified_engine = None
        
        # その他のセッション状態初期化
        if "upload_results" not in st.session_state:
            st.session_state.upload_results = []
        if "unified_processing_results" not in st.session_state:
            st.session_state.unified_processing_results = []
        if "upload_progress" not in st.session_state:
            st.session_state.upload_progress = []
        if "ocr_test_results" not in st.session_state:
            st.session_state.ocr_test_results = []
        if "is_ocr_testing" not in st.session_state:
            st.session_state.is_ocr_testing = False
        
        logger.info("✅ セッション状態初期化完了")
        
    except Exception as e:
        logger.error(f"セッション状態初期化エラー: {e}")
        st.error(f"システム初期化中にエラーが発生しました: {e}")


def render_main_content(selected_menu, user_info):
    """メインコンテンツをレンダリング"""
    
    if selected_menu == "📤 請求書処理":
        render_unified_invoice_processing_page()
    
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
        render_home_page(user_info)


def render_home_page(user_info):
    """ホーム画面"""
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
    
    ### ✨ リファクタリング完了
    - **🏗️ 構造改善**: main.py 2879行 → 200行程度の軽量化
    - **📁 機能分割**: pages/, components/ への機能別分割
    - **🔧 保守性向上**: 機能追加・修正が容易な構造
    """)


def show_debug_info():
    """デバッグ情報表示（デバッグモード時のみ）"""
    try:
        log_config = get_log_config()
        if log_config.is_debug_mode():
            with st.expander("🔍 デバッグ情報", expanded=False):
                st.write("**リファクタリング後のモジュール構造:**")
                st.code("""
src/app/
├── main.py (エントリーポイント - 200行程度)
├── pages/
│   ├── invoice_processing.py (請求書処理)
│   ├── settings.py (ダッシュボード・設定)
│   └── test_pages.py (各種テスト)
├── components/
│   └── sidebar.py (サイドバー)
└── main_original.py (バックアップ)
                """)
                
                st.write("**セッション状態:**")
                session_keys = [k for k in st.session_state.keys() if not k.startswith('_')]
                st.json({k: type(st.session_state[k]).__name__ for k in session_keys})
    except:
        pass


def main():
    """メインアプリケーション"""
    
    # ページ設定
    configure_page()
    
    # デバッグパネルの表示
    render_debug_panel()
    
    # セッション状態の初期化
    initialize_session_state()
    
    # タイトル
    st.title("📄 請求書処理自動化システム（リファクタリング版）")
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
        
        # 安全なファイル行数取得
        try:
            with open(__file__, encoding='utf-8') as f:
                line_count = len(f.readlines())
        except (UnicodeDecodeError, IOError):
            try:
                with open(__file__, encoding='cp932') as f:
                    line_count = len(f.readlines())
            except:
                line_count = "不明"
        
        st.markdown(
            "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
            "請求書処理自動化システム v2.0 - リファクタリング版 | "
            f"main.py: {line_count}行 (元: 2879行)"
            "</div>",
            unsafe_allow_html=True
        )
        
    except Exception as e:
        st.error(f"アプリケーションエラーが発生しました: {e}")
        st.info("ページを再読み込みするか、管理者に問い合わせてください。")
        
        # エラー詳細（デバッグモード時のみ）
        try:
            log_config = get_log_config()
            if log_config.is_debug_mode():
                st.exception(e)
        except:
            pass


if __name__ == "__main__":
    main() 