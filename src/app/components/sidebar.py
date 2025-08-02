"""
サイドバーコンポーネント - ユーザー情報、メニュー表示
"""

import streamlit as st
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent  # src/ ディレクトリ
sys.path.insert(0, str(project_root))

try:
    from infrastructure.auth.oauth_handler import logout
    from utils.log_config import get_logger
    
    logger = get_logger(__name__)
    
except ImportError as e:
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.stop()


def render_sidebar(user_info):
    """サイドバーをレンダリング"""
    with st.sidebar:
        # メニュー表示（ユーザー情報の前に）
        selected_menu = render_menu()
        
        st.divider()
        
        # ユーザー情報表示
        render_user_info(user_info)
        
        return selected_menu


def render_user_info(user_info):
    """ユーザー情報セクション"""
    st.markdown("### 👤 ユーザー情報")
    
    # プロフィール画像があれば表示
    if 'picture' in user_info:
        st.image(user_info['picture'], width=80)
    
    st.write(f"**{user_info['name']}**")
    st.write(f"📧 {user_info['email']}")
    
    # ログアウトボタン
    if st.button("🚪 ログアウト", use_container_width=True):
        logout()


def render_menu():
    """メニューセクション"""
    st.markdown("### 📋 メニュー")
    st.markdown("機能を選択してください")
    
    # メニューオプション定義
    menu_options = get_menu_options()
    
    # メニュー選択（ラジオボタン）
    selected_menu = st.radio(
        "",  # ラベルを空にして、上で表示
        menu_options,
        key="main_menu"
    )
    
    return selected_menu


def get_menu_options():
    """メニューオプションを取得"""
    # 基本メニュー
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
    
    # 将来的な管理者メニュー実装用
    # TODO: ユーザーの役割に応じてメニューを切り替え
    # if is_admin_user(user_info['email']):
    #     menu_options.extend([
    #         "---",
    #         "[管理] 全データ閲覧",
    #         "[管理] 支払マスタ管理",
    #         "[管理] カード明細アップロード",
    #         "[管理] システムログ閲覧"
    #     ])
    
    return menu_options


def get_selected_menu():
    """現在選択されているメニューを取得"""
    return st.session_state.get("main_menu", "📤 請求書処理")


def set_selected_menu(menu_name):
    """メニュー選択を設定"""
    st.session_state.main_menu = menu_name 