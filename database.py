"""
請求書処理自動化システム - Supabaseデータベースヘルパー

このモジュールはSupabaseデータベースへの接続、テーブル作成、
基本的なCRUD操作を提供します。
"""

import streamlit as st
from supabase import create_client, Client
import logging
from typing import Dict, List, Any, Optional
import pandas as pd

# ロガー設定
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Supabaseデータベース管理クラス"""
    
    def __init__(self):
        """Supabase接続を初期化"""
        try:
            self.url = st.secrets["database"]["supabase_url"]
            self.key = st.secrets["database"]["supabase_anon_key"]
            self.supabase: Client = create_client(self.url, self.key)
            logger.info("Supabaseデータベース接続初期化完了")
        except KeyError as e:
            logger.error(f"Supabase設定が不完全です: {e}")
            st.error(f"データベース設定エラー: {e}")
            raise
        except Exception as e:
            logger.error(f"Supabase接続でエラー: {e}")
            st.error(f"データベース接続エラー: {e}")
            raise
    
    def test_connection(self) -> bool:
        """データベース接続をテストする"""
        try:
            # テーブル一覧取得でテスト
            result = self.supabase.table('users').select('*').limit(1).execute()
            logger.info("Supabaseデータベース接続テスト成功")
            return True
        except Exception as e:
            logger.error(f"データベース接続テストでエラー: {e}")
            return False
    
    def create_tables(self) -> bool:
        """必要なテーブルを作成する"""
        try:
            # SQL文でテーブル作成
            # 注意: Supabaseではテーブル作成はWeb UIで行うのが一般的
            # ここではテーブル存在確認のみ行う
            tables_to_check = [
                'users',
                'invoices', 
                'payment_masters',
                'card_statements',
                'user_preferences'
            ]
            
            for table in tables_to_check:
                try:
                    result = self.supabase.table(table).select('*').limit(1).execute()
                    logger.info(f"テーブル '{table}' 存在確認済み")
                except Exception as e:
                    logger.warning(f"テーブル '{table}' が存在しません: {e}")
                    st.warning(f"テーブル '{table}' を手動で作成する必要があります")
            
            return True
        except Exception as e:
            logger.error(f"テーブル作成チェックでエラー: {e}")
            return False
    
    # ユーザー管理
    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """ユーザー情報を取得"""
        try:
            result = self.supabase.table('users').select('*').eq('email', email).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"ユーザー取得でエラー: {e}")
            return None
    
    def create_user(self, email: str, name: str, role: str = 'user') -> bool:
        """新規ユーザーを作成"""
        try:
            data = {
                'email': email,
                'name': name,
                'role': role
            }
            result = self.supabase.table('users').insert(data).execute()
            logger.info(f"ユーザー作成成功: {email}")
            return True
        except Exception as e:
            logger.error(f"ユーザー作成でエラー: {e}")
            return False
    
    # 請求書データ管理
    def get_invoices(self, user_email: str = None) -> List[Dict[str, Any]]:
        """請求書一覧を取得"""
        try:
            query = self.supabase.table('invoices').select('*')
            if user_email:
                query = query.eq('user_email', user_email)
            result = query.order('uploaded_at', desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"請求書取得でエラー: {e}")
            return []
    
    def create_invoice(self, invoice_data: Dict[str, Any]) -> Optional[int]:
        """新規請求書データを作成"""
        try:
            result = self.supabase.table('invoices').insert(invoice_data).execute()
            if result.data:
                logger.info(f"請求書作成成功: {result.data[0]['id']}")
                return result.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"請求書作成でエラー: {e}")
            return None
    
    def update_invoice(self, invoice_id: int, update_data: Dict[str, Any]) -> bool:
        """請求書データを更新"""
        try:
            result = self.supabase.table('invoices').update(update_data).eq('id', invoice_id).execute()
            logger.info(f"請求書更新成功: {invoice_id}")
            return True
        except Exception as e:
            logger.error(f"請求書更新でエラー: {e}")
            return False
    
    # 支払マスタ管理
    def get_payment_masters(self, approval_status: str = None) -> List[Dict[str, Any]]:
        """支払マスタ一覧を取得"""
        try:
            query = self.supabase.table('payment_masters').select('*')
            if approval_status:
                query = query.eq('approval_status', approval_status)
            result = query.order('id').execute()
            return result.data
        except Exception as e:
            logger.error(f"支払マスタ取得でエラー: {e}")
            return []
    
    def create_payment_master(self, master_data: Dict[str, Any]) -> bool:
        """新規支払マスタを作成"""
        try:
            result = self.supabase.table('payment_masters').insert(master_data).execute()
            logger.info(f"支払マスタ作成成功")
            return True
        except Exception as e:
            logger.error(f"支払マスタ作成でエラー: {e}")
            return False
    
    # ユーザー設定管理
    def get_user_preferences(self, user_email: str) -> Optional[Dict[str, Any]]:
        """ユーザー設定を取得"""
        try:
            result = self.supabase.table('user_preferences').select('*').eq('user_email', user_email).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"ユーザー設定取得でエラー: {e}")
            return None
    
    def update_user_preferences(self, user_email: str, preferences: Dict[str, Any]) -> bool:
        """ユーザー設定を更新"""
        try:
            # upsert（存在すればupdate、なければinsert）
            preferences['user_email'] = user_email
            result = self.supabase.table('user_preferences').upsert(preferences).execute()
            logger.info(f"ユーザー設定更新成功: {user_email}")
            return True
        except Exception as e:
            logger.error(f"ユーザー設定更新でエラー: {e}")
            return False


# シングルトンパターンでインスタンスを作成
_db_manager = None

def get_database() -> DatabaseManager:
    """DatabaseManagerのシングルトンインスタンスを取得"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


# 便利関数
def test_database_connection() -> bool:
    """データベース接続をテストする便利関数"""
    return get_database().test_connection()

def ensure_user_exists(email: str, name: str, role: str = 'user') -> bool:
    """ユーザーが存在することを確認し、なければ作成する"""
    db = get_database()
    user = db.get_user(email)
    if not user:
        return db.create_user(email, name, role)
    return True 