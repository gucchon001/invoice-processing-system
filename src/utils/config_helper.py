"""
設定ファイル管理ヘルパー
config/settings.iniから設定値を読み込む
"""
import configparser
import os
from pathlib import Path
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigHelper:
    """設定ファイル管理クラス"""
    
    def __init__(self, config_file: str = "config/settings.ini"):
        """設定ファイルを読み込み"""
        self.config = configparser.ConfigParser()
        self.config_file = Path(config_file)
        
        if self.config_file.exists():
            self.config.read(self.config_file, encoding='utf-8')
            logger.info(f"設定ファイルを読み込みました: {self.config_file}")
        else:
            logger.warning(f"設定ファイルが見つかりません: {self.config_file}")
    
    def get_str(self, section: str, key: str, default: str = "") -> str:
        """文字列設定値を取得"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            logger.debug(f"設定値が見つかりません: [{section}] {key}, デフォルト値を使用: {default}")
            return default
    
    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """整数設定値を取得"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            logger.debug(f"設定値が見つかりません: [{section}] {key}, デフォルト値を使用: {default}")
            return default
    
    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        """浮動小数点設定値を取得"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            logger.debug(f"設定値が見つかりません: [{section}] {key}, デフォルト値を使用: {default}")
            return default
    
    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """真偽値設定値を取得"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            logger.debug(f"設定値が見つかりません: [{section}] {key}, デフォルト値を使用: {default}")
            return default

# グローバル設定インスタンス
_config_helper = None

def get_config() -> ConfigHelper:
    """設定ヘルパーのシングルトンインスタンスを取得"""
    global _config_helper
    if _config_helper is None:
        _config_helper = ConfigHelper()
    return _config_helper

# AI設定の便利関数
def get_gemini_model() -> str:
    """Geminiモデル名を取得"""
    return get_config().get_str("ai", "gemini_model", "gemini-2.5-flash-lite-preview-06-17")

def get_gemini_max_retries() -> int:
    """Gemini最大リトライ回数を取得"""
    return get_config().get_int("ai", "gemini_max_retries", 3)

def get_gemini_retry_delay() -> int:
    """Geminiリトライ遅延時間(秒)を取得"""
    return get_config().get_int("ai", "gemini_retry_delay", 30)

def get_gemini_rate_limit() -> int:
    """Geminiレート制限(requests per minute)を取得"""
    return get_config().get_int("ai", "gemini_rate_limit", 10)

def get_gemini_timeout() -> int:
    """Geminiタイムアウト(秒)を取得"""
    return get_config().get_int("ai", "gemini_timeout", 60)

def get_gemini_temperature() -> float:
    """Gemini温度パラメータを取得"""
    return get_config().get_float("ai", "gemini_temperature", 0.1)

def get_gemini_max_tokens() -> int:
    """Gemini最大出力トークン数を取得"""
    return get_config().get_int("ai", "gemini_max_output_tokens", 8192)

# ログ設定の便利関数
def get_log_level() -> str:
    """ログレベルを取得"""
    return get_config().get_str("logging", "log_level", "INFO")

def is_debug_mode() -> bool:
    """デバッグモードかどうかを取得"""
    return get_config().get_bool("debug", "debug_mode", False)

def is_ai_debug() -> bool:
    """AI処理デバッグモードかどうかを取得"""
    return get_config().get_bool("debug", "ai_debug", False) 