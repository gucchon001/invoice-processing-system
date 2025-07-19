"""
請求書処理自動化システム - 認証モジュール
streamlit-oauth統一認証パッケージ
"""

from .oauth_handler import (
    OAuthHandler,
    get_oauth_handler,
    is_authenticated,
    get_current_user,
    require_auth,
    login,
    logout
)

__version__ = "1.0.0"
__author__ = "請求書処理システム開発チーム"

__all__ = [
    "OAuthHandler",
    "get_oauth_handler", 
    "is_authenticated",
    "get_current_user",
    "require_auth",
    "login",
    "logout"
] 