"""
請求書処理自動化システム - OAuth認証ハンドラー
streamlit-oauth統一認証方式

このモジュールは開発環境・本番環境の両方で同一のOAuth認証を提供します。
"""

import streamlit as st
import requests
from streamlit_oauth import OAuth2Component
from typing import Optional, Dict, Any
import logging

# ロガー設定
logger = logging.getLogger(__name__)


class OAuthHandler:
    """OAuth認証の統一ハンドラークラス"""
    
    def __init__(self):
        """OAuth設定を初期化"""
        try:
            self.client_id = st.secrets["auth"]["client_id"]
            self.client_secret = st.secrets["auth"]["client_secret"]
            self.redirect_uri = st.secrets["auth"]["redirect_uri"]
            self.cookie_secret = st.secrets["auth"]["cookie_secret"]
            
            # OAuth2Componentの初期化
            self.oauth2 = OAuth2Component(
                client_id=self.client_id,
                client_secret=self.client_secret,
                authorize_endpoint="https://accounts.google.com/o/oauth2/auth",
                token_endpoint="https://oauth2.googleapis.com/token",
                refresh_token_endpoint="https://oauth2.googleapis.com/token",
                revoke_token_endpoint="https://oauth2.googleapis.com/revoke",
            )
            
            logger.info("OAuth認証システム初期化完了")
            
        except KeyError as e:
            logger.error(f"OAuth設定が不完全です: {e}")
            st.error(f"認証設定エラー: {e}")
            st.stop()
    
    def is_authenticated(self) -> bool:
        """認証状態をチェック"""
        return 'auth_token' in st.session_state and st.session_state['auth_token'] is not None
    
    def get_user_info(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        アクセストークンを使用してGoogleからユーザー情報を取得
        
        Args:
            token: OAuth認証で取得したトークン情報
            
        Returns:
            ユーザー情報辞書（name, email, picture等）
        """
        try:
            headers = {'Authorization': f'Bearer {token["access_token"]}'}
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"ユーザー情報取得成功: {user_info.get('email', 'unknown')}")
                return user_info
            else:
                logger.error(f"ユーザー情報取得失敗: HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"ユーザー情報取得でネットワークエラー: {e}")
            return None
        except Exception as e:
            logger.error(f"ユーザー情報取得で予期せぬエラー: {e}")
            return None
    
    def login(self) -> bool:
        """
        ログイン処理を実行
        
        Returns:
            ログイン成功時True、失敗または未完了時False
        """
        if self.is_authenticated():
            return True
            
        # ログインUI表示
        st.info("🔐 Googleアカウントでログインしてください")
        
        try:
            # OAuth認証ボタン
            result = self.oauth2.authorize_button(
                "Googleでログイン",
                redirect_uri=self.redirect_uri,
                scope="openid email profile",
                key="google_oauth"
            )
            
            if result and 'token' in result:
                # トークン取得成功
                token = result['token']
                user_info = self.get_user_info(token)
                
                if user_info:
                    # セッションに保存
                    st.session_state['auth_token'] = token
                    st.session_state['user_info'] = user_info
                    
                    # 成功メッセージ
                    st.success(f"ログインしました！ようこそ、{user_info['name']}さん")
                    logger.info(f"ログイン成功: {user_info['email']}")
                    
                    # ページリロード
                    st.rerun()
                    return True
                else:
                    st.error("ユーザー情報の取得に失敗しました")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"ログイン処理でエラー: {e}")
            st.error(f"ログインエラーが発生しました: {e}")
            return False
    
    def logout(self):
        """ログアウト処理を実行"""
        try:
            # セッション情報をクリア
            if 'auth_token' in st.session_state:
                del st.session_state['auth_token']
            if 'user_info' in st.session_state:
                user_email = st.session_state['user_info'].get('email', 'unknown')
                del st.session_state['user_info']
                logger.info(f"ログアウト: {user_email}")
            
            # その他のセッション情報もクリア
            keys_to_clear = [key for key in st.session_state.keys() 
                           if key.startswith(('auth_', 'user_', 'session_'))]
            for key in keys_to_clear:
                del st.session_state[key]
            
            st.success("ログアウトしました")
            st.rerun()
            
        except Exception as e:
            logger.error(f"ログアウト処理でエラー: {e}")
            st.error(f"ログアウトエラー: {e}")
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        現在のログインユーザー情報を取得
        
        Returns:
            ユーザー情報辞書またはNone
        """
        if self.is_authenticated() and 'user_info' in st.session_state:
            return st.session_state['user_info']
        return None
    
    def require_auth(self) -> Dict[str, Any]:
        """
        認証を必須とする場合のデコレーター的機能
        認証されていない場合はログイン画面を表示し、処理を停止
        
        Returns:
            認証済みの場合はユーザー情報を返す
        """
        if not self.is_authenticated():
            self.login()
            st.stop()
        
        user_info = self.get_current_user()
        if not user_info:
            st.error("ユーザー情報が取得できません。再度ログインしてください。")
            self.logout()
            st.stop()
        
        return user_info


# シングルトンパターンでインスタンスを作成
_oauth_handler = None

def get_oauth_handler() -> OAuthHandler:
    """OAuthHandlerのシングルトンインスタンスを取得"""
    global _oauth_handler
    if _oauth_handler is None:
        _oauth_handler = OAuthHandler()
    return _oauth_handler


# 便利関数
def is_authenticated() -> bool:
    """認証状態を確認する便利関数"""
    return get_oauth_handler().is_authenticated()

def get_current_user() -> Optional[Dict[str, Any]]:
    """現在のユーザー情報を取得する便利関数"""
    return get_oauth_handler().get_current_user()

def require_auth() -> Dict[str, Any]:
    """認証を必須とする便利関数"""
    return get_oauth_handler().require_auth()

def login() -> bool:
    """ログインする便利関数"""
    return get_oauth_handler().login()

def logout():
    """ログアウトする便利関数"""
    get_oauth_handler().logout() 