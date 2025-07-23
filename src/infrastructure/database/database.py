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
    
    def debug_table_schema(self, table_name: str = 'invoices'):
        """テーブルスキーマをデバッグ出力する"""
        try:
            # 空のSELECTクエリでスキーマ情報を取得
            result = self.supabase.table(table_name).select('*').limit(0).execute()
            logger.error(f"🔍 DEBUG: {table_name}テーブルのスキーマ情報: {result}")
            
            # 実際のデータを1件取得してフィールド確認
            sample_result = self.supabase.table(table_name).select('*').limit(1).execute()
            if sample_result.data:
                logger.error(f"🔍 DEBUG: {table_name}テーブルのサンプルデータ: {sample_result.data[0]}")
                logger.error(f"🔍 DEBUG: {table_name}テーブルの実際のカラム: {list(sample_result.data[0].keys())}")
            else:
                logger.error(f"🔍 DEBUG: {table_name}テーブルにデータがありません")
                
        except Exception as e:
            logger.error(f"🔍 DEBUG: テーブルスキーマ確認でエラー: {e}")
    
    def get_recent_invoices(self, limit: int = 10):
        """最近の請求書データを取得する"""
        try:
            result = self.supabase.table('invoices').select('*').order('uploaded_at', desc=True).limit(limit).execute()
            logger.info(f"📊 最近の請求書データ取得成功: {len(result.data)}件")
            return result.data
        except Exception as e:
            logger.error(f"📊 最近の請求書データ取得でエラー: {e}")
            return []
    
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
            
            # レスポンスデータの安全な処理
            data = result.data if result.data else []
            
            # DataFrameの場合はリストに変換
            if hasattr(data, 'to_dict'):
                data = data.to_dict('records')
            elif not isinstance(data, list):
                data = []
            
            if len(data) > 0:
                return data[0]
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
            
            # レスポンスデータの安全な処理
            data = result.data if result.data else []
            
            # DataFrameの場合はリストに変換
            if hasattr(data, 'to_dict'):
                data = data.to_dict('records')
            elif not isinstance(data, list):
                data = []
            
            return data
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
    
    def insert_invoice(self, invoice_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """統合ワークフロー用請求書データ挿入（完全カラム対応・JST時間対応）"""
        try:
            # 🔍 デバッグ: 挿入前のデータ確認
            logger.info(f"🔄 請求書データ挿入開始 - ファイル: {invoice_data.get('file_name', 'N/A')}")
            
            # AI抽出データの取得
            extracted_data = invoice_data.get('extracted_data', {})
            
            # JST時間の取得
            def get_jst_now():
                from datetime import datetime, timezone, timedelta
                jst = timezone(timedelta(hours=9))  # JST = UTC+9
                return datetime.now(jst).isoformat()
            
            # 日付文字列の処理ヘルパー
            def parse_date(date_str):
                if not date_str:
                    return None
                try:
                    from datetime import datetime
                    if isinstance(date_str, str):
                        # YYYY-MM-DD形式の場合
                        return date_str if len(date_str) == 10 and '-' in date_str else None
                    return None
                except:
                    return None
            
            # 数値の安全な変換
            def safe_decimal(value, default=None):
                if value is None:
                    return default
                try:
                    return float(value) if value != '' else default
                except (ValueError, TypeError):
                    return default
            
            # JST時間を取得
            from datetime import datetime, timezone, timedelta
            jst = timezone(timedelta(hours=9))
            jst_now = datetime.now(jst).isoformat()
            
            # 完全なデータマッピング（新しいカラム構造対応・JST時間対応）
            insert_data = {
                # 基本情報
                'user_email': invoice_data.get('user_email', invoice_data.get('created_by', '')),
                'file_name': invoice_data.get('file_name', ''),
                'file_id': invoice_data.get('file_id', ''),  # 必須項目追加
                'status': 'extracted',  # シンプルなステータス
                
                # JST時間を明示的に設定
                'created_at': jst_now,
                'updated_at': jst_now,
                'uploaded_at': jst_now,
                
                # 請求書基本情報（個別カラム）
                'issuer_name': extracted_data.get('issuer', '')[:255] if extracted_data.get('issuer') else None,
                'recipient_name': extracted_data.get('payer', '')[:255] if extracted_data.get('payer') else None,
                'invoice_number': extracted_data.get('main_invoice_number', '')[:100] if extracted_data.get('main_invoice_number') else None,
                'registration_number': extracted_data.get('t_number', '')[:50] if extracted_data.get('t_number') else None,
                'currency': extracted_data.get('currency', 'JPY')[:10] if extracted_data.get('currency') else 'JPY',
                
                # 金額情報
                'total_amount_tax_included': safe_decimal(extracted_data.get('amount_inclusive_tax')),
                'total_amount_tax_excluded': safe_decimal(extracted_data.get('amount_exclusive_tax')),
                
                # 日付情報
                'issue_date': parse_date(extracted_data.get('issue_date')),
                'due_date': parse_date(extracted_data.get('due_date')),
                
                # JSON形式データ
                'key_info': extracted_data.get('key_info', {}),
                'raw_response': invoice_data.get('raw_ai_response', extracted_data),  # AI生レスポンス
                'extracted_data': extracted_data,  # 完全なAI抽出データ
                
                # 品質管理情報
                'is_valid': True,  # 基本的に抽出成功時はTrue
                'completeness_score': self._calculate_completeness_score(extracted_data),
                'processing_time': invoice_data.get('processing_time'),
                
                # ファイル管理情報
                'gdrive_file_id': invoice_data.get('file_path', ''),  # Google Drive ID
                'file_path': invoice_data.get('gdrive_file_id', ''),
                'file_size': invoice_data.get('file_size'),
                
                # AIモデル情報
                'gemini_model': 'gemini-2.0-flash-exp',
                
                # JST時間の明示的設定
                'created_at': jst_now,
                'updated_at': jst_now
            }
            
            # Noneや空文字列のフィールドを除去（Supabaseエラー回避）
            clean_data = {k: v for k, v in insert_data.items() if v is not None and v != ''}
            
            logger.info(f"✅ 挿入データ準備完了 - カラム数: {len(clean_data)}")
            logger.debug(f"🔧 主要フィールド: issuer={clean_data.get('issuer_name')}, amount={clean_data.get('total_amount_tax_included')}, date={clean_data.get('issue_date')}")
            
            # データベースに挿入
            result = self.supabase.table('invoices').insert(clean_data).execute()
            
            # レスポンス処理
            data = result.data if result.data else []
            if hasattr(data, 'to_dict'):
                data = data.to_dict('records')
            elif not isinstance(data, list):
                data = []
            
            if len(data) > 0:
                invoice_id = data[0].get('id')
                logger.info(f"🎉 請求書挿入成功: ID={invoice_id}, 企業={clean_data.get('issuer_name', 'N/A')}")
                return data[0]
            else:
                raise Exception("データベースへの挿入に失敗しました")
                
        except Exception as e:
            logger.error(f"❌ 請求書挿入エラー: {str(e)[:200]}")
            logger.error(f"🔍 ファイル: {invoice_data.get('file_name', 'N/A')}")
            
            # 詳細エラー情報
            if hasattr(e, 'details'):
                logger.error(f"🔍 詳細: {e.details}")
            
            raise e
    
    def _calculate_completeness_score(self, extracted_data: Dict) -> float:
        """AI抽出データの完全性スコアを計算"""
        try:
            required_fields = ['issuer', 'payer', 'amount_inclusive_tax', 'issue_date']
            optional_fields = ['main_invoice_number', 'due_date', 'currency', 't_number']
            
            # 必須フィールドの完全性（70%）
            required_score = sum(1 for field in required_fields if extracted_data.get(field)) / len(required_fields) * 70
            
            # オプションフィールドの完全性（30%）
            optional_score = sum(1 for field in optional_fields if extracted_data.get(field)) / len(optional_fields) * 30
            
            total_score = required_score + optional_score
            return round(total_score, 1)
            
        except Exception:
            return 50.0  # デフォルトスコア
    
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
            
            # レスポンスデータの安全な処理
            data = result.data if result.data else []
            
            # DataFrameの場合はリストに変換
            if hasattr(data, 'to_dict'):
                data = data.to_dict('records')
            elif not isinstance(data, list):
                data = []
            
            return data
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
            
            # レスポンスデータの安全な処理
            data = result.data if result.data else []
            
            # DataFrameの場合はリストに変換
            if hasattr(data, 'to_dict'):
                data = data.to_dict('records')
            elif not isinstance(data, list):
                data = []
            
            if len(data) > 0:
                return data[0]
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

 