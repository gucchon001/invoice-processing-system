"""
ログ設定モジュール

settings.iniからログ設定を読み込み、統一されたログ設定を提供します。
"""

import logging
import logging.handlers
import configparser
import os
import sys
from pathlib import Path
from datetime import datetime


class LogConfig:
    """ログ設定クラス"""
    
    def __init__(self, config_path: str = None):
        """
        ログ設定の初期化
        
        Args:
            config_path (str, optional): 設定ファイルのパス
        """
        self.config_path = config_path or self._get_config_path()
        self.config = configparser.ConfigParser()
        self._load_config()
        self._setup_logging()
        
    def _get_config_path(self) -> str:
        """設定ファイルのパスを取得"""
        # プロジェクトルートのconfig/settings.iniを取得
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # src/utils/log_config.py -> project_root
        config_path = project_root / "config" / "settings.ini"
        return str(config_path)
        
    def _load_config(self):
        """設定ファイルを読み込み"""
        try:
            if os.path.exists(self.config_path):
                self.config.read(self.config_path, encoding='utf-8')
            else:
                # デフォルト設定
                self._create_default_config()
        except Exception as e:
            print(f"設定ファイル読み込みエラー: {e}")
            self._create_default_config()
            
    def _create_default_config(self):
        """デフォルト設定を作成"""
        self.config['logging'] = {
            'log_level': 'INFO',
            'enable_file_logging': 'true',
            'log_file_path': 'logs/app.log',
            'max_log_file_size': '10',
            'log_backup_count': '5',
            'enable_console_logging': 'true',
            'detailed_logging': 'false'
        }
        self.config['debug'] = {
            'debug_mode': 'false'
        }
        
    def _setup_logging(self):
        """ログ設定をセットアップ"""
        # ログレベルの設定
        log_level = self.config.get('logging', 'log_level', fallback='INFO')
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # 既存のハンドラーをクリア
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # フォーマッターの設定
        detailed_logging = self.config.getboolean('logging', 'detailed_logging', fallback=False)
        if detailed_logging:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
        # コンソールハンドラーの設定
        if self.config.getboolean('logging', 'enable_console_logging', fallback=True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            
        # ファイルハンドラーの設定
        if self.config.getboolean('logging', 'enable_file_logging', fallback=True):
            log_file_path = self.config.get('logging', 'log_file_path', fallback='logs/app.log')
            
            # ログディレクトリを作成
            log_dir = Path(log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # ローテーティングファイルハンドラーの設定
            max_bytes = int(self.config.get('logging', 'max_log_file_size', fallback='10')) * 1024 * 1024
            backup_count = int(self.config.get('logging', 'log_backup_count', fallback='5'))
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path, 
                maxBytes=max_bytes, 
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
    def get_logger(self, name: str = None) -> logging.Logger:
        """ロガーを取得"""
        return logging.getLogger(name)
        
    def is_debug_mode(self) -> bool:
        """デバッグモードかどうかを判定"""
        return self.config.getboolean('debug', 'debug_mode', fallback=False)
        
    def is_debug_enabled(self, category: str) -> bool:
        """特定のカテゴリのデバッグが有効かどうかを判定"""
        debug_key = f"{category}_debug"
        return self.config.getboolean('debug', debug_key, fallback=False)
        
    def get_environment(self) -> str:
        """実行環境を取得"""
        return self.config.get('system', 'environment', fallback='development')
        
    def is_security_logging_enabled(self) -> bool:
        """セキュリティログが有効かどうかを判定"""
        return self.config.getboolean('security', 'security_logging', fallback=True)
        
    def is_auth_logging_enabled(self) -> bool:
        """認証ログが有効かどうかを判定"""
        return self.config.getboolean('security', 'auth_logging', fallback=True)


# グローバルインスタンス
_log_config = None


def get_log_config() -> LogConfig:
    """ログ設定のシングルトンインスタンスを取得"""
    global _log_config
    if _log_config is None:
        _log_config = LogConfig()
    return _log_config


def get_logger(name: str = None) -> logging.Logger:
    """設定済みロガーを取得"""
    config = get_log_config()
    return config.get_logger(name)


def setup_logging(config_path: str = None):
    """ログ設定を初期化"""
    global _log_config
    _log_config = LogConfig(config_path)


def debug_log(logger: logging.Logger, message: str, category: str = 'general'):
    """デバッグログの出力（カテゴリ別制御）"""
    config = get_log_config()
    if config.is_debug_mode() or config.is_debug_enabled(category):
        logger.debug(f"[{category.upper()}] {message}")


# 起動時の自動設定
if __name__ != "__main__":
    try:
        get_log_config()
    except Exception as e:
        print(f"ログ設定の初期化に失敗しました: {e}") 