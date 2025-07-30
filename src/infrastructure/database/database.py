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
from utils.config_helper import get_gemini_model

# ロガー設定
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Supabaseデータベース管理クラス"""
    
    def __init__(self):
        """Supabase接続を初期化"""
        try:
            self.url = st.secrets["database"]["supabase_url"]
            
            # 🔍 詳細デバッグ: secrets.toml読み込み状況確認 ★DEBUG★
            logger.info(f"🔍 DEBUG - supabase_url: {self.url}")
            logger.info(f"🔍 DEBUG - secrets keys: {list(st.secrets['database'].keys())}")
            
            # 🔧 認証方式選択: Service Role Key優先、Anon Keyフォールバック ★RLS FIX★
            service_role_key = None
            
            # 新しいキー名を優先、古いキー名も互換性対応 ★COMPATIBILITY★
            if "supabase_service_role_key" in st.secrets["database"]:
                service_role_key = st.secrets["database"]["supabase_service_role_key"]
                logger.info("🔑 新形式Service Role Key検出: supabase_service_role_key")
            elif "supabase_service_key" in st.secrets["database"]:
                service_role_key = st.secrets["database"]["supabase_service_key"]
                logger.info("🔑 旧形式Service Role Key検出: supabase_service_key")
            
            if service_role_key:
                self.key = service_role_key
                
                # 🔍 詳細デバッグ: Service Role Key内容確認 ★DEBUG★
                key_start = self.key[:20] if len(self.key) > 20 else self.key
                key_end = self.key[-10:] if len(self.key) > 30 else "***"
                logger.info(f"🔍 DEBUG - Service Role Key読み込み成功")
                logger.info(f"🔍 DEBUG - Key開始部分: {key_start}...")
                logger.info(f"🔍 DEBUG - Key終了部分: ...{key_end}")
                logger.info(f"🔍 DEBUG - Key長: {len(self.key)} 文字")
                
                # Service Role Keyの形式確認
                if "service_role" in self.key:
                    logger.info("✅ Service Role Key形式確認: service_role含有")
                else:
                    logger.warning("⚠️ Service Role Key形式警告: service_role未含有")
                
                logger.info("🔑 Service Role Key使用 - RLS管理者権限で接続")
            else:
                self.key = st.secrets["database"]["supabase_anon_key"]
                logger.warning("⚠️ Anonymous Key使用 - RLS制限あり（Service Role Key推奨）")
            
            # 🔍 詳細デバッグ: Supabaseクライアント作成前確認 ★DEBUG★
            logger.info(f"🔍 DEBUG - クライアント作成開始")
            logger.info(f"🔍 DEBUG - URL: {self.url}")
            logger.info(f"🔍 DEBUG - 使用キー種別: {'Service Role' if 'supabase_service_role_key' in st.secrets['database'] else 'Anonymous'}")
            
            self.supabase: Client = create_client(self.url, self.key)
            
            # 🔍 詳細デバッグ: クライアント作成後確認 ★DEBUG★
            logger.info(f"🔍 DEBUG - クライアント作成完了")
            logger.info(f"🔍 DEBUG - クライアント情報: {type(self.supabase)}")
            
            # Supabaseクライアントの内部設定確認
            if hasattr(self.supabase, 'auth'):
                logger.info(f"🔍 DEBUG - auth属性存在: {hasattr(self.supabase.auth, 'get_session')}")
            if hasattr(self.supabase, 'rest'):
                logger.info(f"🔍 DEBUG - rest属性存在: {type(self.supabase.rest)}")
                
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
    
    def check_tables_exist(self) -> bool:
        """必要なテーブルの存在確認"""
        try:
            tables_to_check = [
                'users',
                'invoices', 
                'payment_masters',
                'card_statements',
                'user_preferences'
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table in tables_to_check:
                try:
                    result = self.supabase.table(table).select('*').limit(1).execute()
                    existing_tables.append(table)
                    logger.info(f"✅ テーブル '{table}' 存在確認済み")
                except Exception as e:
                    missing_tables.append(table)
                    logger.warning(f"❌ テーブル '{table}' が存在しません: {e}")
            
            # 結果をStreamlitに表示
            if existing_tables:
                st.success(f"✅ 存在するテーブル: {', '.join(existing_tables)}")
            
            if missing_tables:
                st.warning(f"⚠️ 不足しているテーブル: {', '.join(missing_tables)}")
                st.info("不足しているテーブルはSupabase Web UIで手動作成してください。")
            
            # すべてのテーブルが存在する場合のみTrue
            return len(missing_tables) == 0
        except Exception as e:
            logger.error(f"テーブル存在確認でエラー: {e}")
            st.error(f"テーブル確認中にエラーが発生しました: {e}")
            return False
    
    def get_sample_data(self) -> List[Dict[str, Any]]:
        """サンプルデータを取得（テスト用）"""
        try:
            # 各テーブルから少量のサンプルデータを取得
            sample_data = []
            
            # invoicesテーブルからサンプル取得
            try:
                invoices_result = self.supabase.table('invoices').select('id,file_name,issuer_name,created_at').limit(3).execute()
                invoices_data = invoices_result.data if invoices_result.data else []
                
                for invoice in invoices_data:
                    sample_data.append({
                        'table': 'invoices',
                        'id': invoice.get('id'),
                        'description': f"請求書: {invoice.get('file_name', 'N/A')} (発行者: {invoice.get('issuer_name', 'N/A')})",
                        'created_at': invoice.get('created_at', 'N/A')
                    })
            except Exception as e:
                logger.warning(f"invoicesテーブルのサンプル取得に失敗: {e}")
            
            # usersテーブルからサンプル取得
            try:
                users_result = self.supabase.table('users').select('email,name,role,created_at').limit(3).execute()
                users_data = users_result.data if users_result.data else []
                
                for user in users_data:
                    sample_data.append({
                        'table': 'users',
                        'id': user.get('email'),
                        'description': f"ユーザー: {user.get('name', 'N/A')} ({user.get('role', 'N/A')})",
                        'created_at': user.get('created_at', 'N/A')
                    })
            except Exception as e:
                logger.warning(f"usersテーブルのサンプル取得に失敗: {e}")
            
            # payment_mastersテーブルからサンプル取得
            try:
                masters_result = self.supabase.table('payment_masters').select('id,company_name,approval_status,created_at').limit(3).execute()
                masters_data = masters_result.data if masters_result.data else []
                
                for master in masters_data:
                    sample_data.append({
                        'table': 'payment_masters',
                        'id': master.get('id'),
                        'description': f"支払マスタ: {master.get('company_name', 'N/A')} (ステータス: {master.get('approval_status', 'N/A')})",
                        'created_at': master.get('created_at', 'N/A')
                    })
            except Exception as e:
                logger.warning(f"payment_mastersテーブルのサンプル取得に失敗: {e}")
            
            logger.info(f"サンプルデータ取得成功: {len(sample_data)}件")
            return sample_data
            
        except Exception as e:
            logger.error(f"サンプルデータ取得でエラー: {e}")
            return []

    def create_tables(self) -> bool:
        """必要なテーブルを作成する"""
        try:
            # SQL文でテーブル作成
            # 注意: Supabaseではテーブル作成はWeb UIで行うのが一般的
            # ここではテーブル存在確認のみ行う
            return self.check_tables_exist()
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
    
# create_invoice() メソッドは重複のため削除されました
    # 代わりに insert_invoice() を使用してください
    
    def insert_invoice(self, invoice_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """統合ワークフロー用請求書データ挿入（40カラム完全対応・JST時間対応）"""
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
            
            # 🔍 RLS対応デバッグログ ★DEBUG★
            user_email_from_data = invoice_data.get('user_email')
            created_by_from_data = invoice_data.get('created_by')
            final_user_email = user_email_from_data or created_by_from_data or ''
            
            logger.info(f"🔍 RLS Debug - invoice_data user_email: {user_email_from_data}")
            logger.info(f"🔍 RLS Debug - invoice_data created_by: {created_by_from_data}")
            logger.info(f"🔍 RLS Debug - final user_email: {final_user_email}")
            
            # 🚨 RLS要件チェック: user_emailが空の場合はエラー ★RLS VALIDATION★
            if not final_user_email or final_user_email.strip() == '':
                error_msg = "RLS要件エラー: user_emailが設定されていません。認証済みユーザーの情報が必要です。"
                logger.error(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            # 40カラム完全対応データマッピング（新機能13カラム対応）
            insert_data = {
                # 🔑 基本管理（6カラム）
                'user_email': final_user_email,  # デバッグ用に明示的に設定
                'status': 'extracted',  # シンプルなステータス
                'uploaded_at': jst_now,
                'created_at': jst_now,
                'updated_at': jst_now,
                
                # 📁 ファイル管理（7カラム） - 🆕 新機能4カラム追加
                'file_name': invoice_data.get('file_name', ''),
                'gdrive_file_id': invoice_data.get('file_id', ''),    # Google Drive ID
                'file_path': invoice_data.get('file_path', ''),       # ファイルパス
                'source_type': invoice_data.get('source_type', 'local'),  # 🆕 ファイルソース
                'gmail_message_id': invoice_data.get('gmail_message_id'),  # 🆕 Gmailメッセージ
                'attachment_id': invoice_data.get('attachment_id'),        # 🆕 添付ファイルID
                'sender_email': invoice_data.get('sender_email'),          # 🆕 送信者メール
                
                # 📄 請求書基本情報（7カラム）
                'issuer_name': extracted_data.get('issuer', '')[:255] if extracted_data.get('issuer') else None,
                'recipient_name': extracted_data.get('payer', '')[:255] if extracted_data.get('payer') else None,
                'main_invoice_number': extracted_data.get('main_invoice_number', '')[:255] if extracted_data.get('main_invoice_number') else None,
                'receipt_number': extracted_data.get('receipt_number', '')[:255] if extracted_data.get('receipt_number') else None,
                't_number': extracted_data.get('t_number', '')[:50] if extracted_data.get('t_number') else None,
                'issue_date': parse_date(extracted_data.get('issue_date')),
                'due_date': parse_date(extracted_data.get('due_date')),
                
                # 💰 金額・通貨情報（6カラム） - 🆕 新機能3カラム追加
                'currency': extracted_data.get('currency', 'JPY')[:10] if extracted_data.get('currency') else 'JPY',
                'total_amount_tax_included': safe_decimal(extracted_data.get('amount_inclusive_tax')),
                'total_amount_tax_excluded': safe_decimal(extracted_data.get('amount_exclusive_tax')),
                'exchange_rate': safe_decimal(invoice_data.get('exchange_rate')),     # 🆕 為替レート
                'jpy_amount': safe_decimal(invoice_data.get('jpy_amount')),           # 🆕 円換算金額
                'card_statement_id': invoice_data.get('card_statement_id'),          # 🆕 カード明細ID
                
                # 🤖 AI処理・検証結果（8カラム）
                'extracted_data': extracted_data,  # 完全なAI抽出データ
                'raw_response': invoice_data.get('raw_ai_response', extracted_data),  # AI生レスポンス
                'key_info': extracted_data.get('key_info', {}),  # 統一化フィールド復活
                'is_valid': True,  # 基本的に抽出成功時はTrue
                'validation_errors': invoice_data.get('validation_errors', []),
                'validation_warnings': invoice_data.get('validation_warnings', []),
                'completeness_score': self._calculate_completeness_score(extracted_data),
                'processing_time': invoice_data.get('processing_time'),
                
                # ✅ 承認ワークフロー（3カラム） - 🆕 新機能3カラム追加
                'approval_status': 'approved' if invoice_data.get('approval_status') == 'auto_approved' else invoice_data.get('approval_status', 'pending'),  # 🆕 承認状況（制約適合）
                'approved_by': invoice_data.get('approved_by'),                       # 🆕 承認者
                'approved_at': invoice_data.get('approved_at'),                       # 🆕 承認日時
                
                # 📊 freee連携（3カラム） - 🆕 新機能3カラム追加
                'exported_to_freee': invoice_data.get('exported_to_freee', False),   # 🆕 freee連携済み
                'export_date': invoice_data.get('export_date'),                       # 🆕 連携日時
                'freee_batch_id': invoice_data.get('freee_batch_id'),                 # 🆕 freeeバッチID
            }
            
            # Noneや空文字列のフィールドを除去（Supabaseエラー回避）
            clean_data = {k: v for k, v in insert_data.items() if v is not None and v != ''}
            
            logger.info(f"✅ 40カラム挿入データ準備完了 - カラム数: {len(clean_data)}")
            logger.debug(f"🔧 主要フィールド: issuer={clean_data.get('issuer_name')}, amount={clean_data.get('total_amount_tax_included')}, source={clean_data.get('source_type')}")
            
            # 🔍 RLS最終確認デバッグログ ★DEBUG★
            final_user_email_in_clean = clean_data.get('user_email', 'NOT_SET')
            logger.info(f"🔍 RLS Final Debug - clean_data user_email: '{final_user_email_in_clean}'")
            logger.info(f"🔍 RLS Final Debug - clean_data keys: {sorted(clean_data.keys())}")
            
            # 🔍 Supabaseクライアント詳細デバッグ ★DEBUG★
            logger.info(f"🔍 DEBUG - Supabaseクライアント状態確認開始")
            logger.info(f"🔍 DEBUG - self.url: {self.url}")
            
            # 使用中のキーの詳細確認
            key_type = "Service Role" if "service_role" in self.key else "Anonymous"
            key_start = self.key[:20] if len(self.key) > 20 else self.key
            key_end = self.key[-10:] if len(self.key) > 30 else "***"
            logger.info(f"🔍 DEBUG - 実際使用キー種別: {key_type}")
            logger.info(f"🔍 DEBUG - 実際使用キー開始: {key_start}...")
            logger.info(f"🔍 DEBUG - 実際使用キー終了: ...{key_end}")
            
            # Supabaseクライアントの内部認証確認
            if hasattr(self.supabase, '_api_key'):
                logger.info(f"🔍 DEBUG - クライアント内部API Key設定確認済み")
            else:
                logger.warning(f"⚠️ DEBUG - クライアント内部API Key設定未確認")
                
            # HTTPリクエスト実行直前ログ
            logger.info(f"🔍 DEBUG - データベース挿入実行開始")
            logger.info(f"🔍 DEBUG - テーブル: invoices")
            logger.info(f"🔍 DEBUG - データサイズ: {len(str(clean_data))} 文字")
            
            # データベースに挿入
            result = self.supabase.table('invoices').insert(clean_data).execute()
            
            # 🔍 HTTPレスポンス詳細デバッグ ★DEBUG★
            logger.info(f"🔍 DEBUG - HTTPリクエスト完了")
            logger.info(f"🔍 DEBUG - レスポンス型: {type(result)}")
            if hasattr(result, 'data'):
                logger.info(f"🔍 DEBUG - レスポンスデータ: {result.data}")
            if hasattr(result, 'count'):
                logger.info(f"🔍 DEBUG - レスポンス件数: {result.count}")
            if hasattr(result, 'status_code'):
                logger.info(f"🔍 DEBUG - ステータスコード: {result.status_code}")
            else:
                logger.info(f"🔍 DEBUG - ステータスコード属性なし")
            
            # レスポンス処理
            data = result.data if result.data else []
            if hasattr(data, 'to_dict'):
                data = data.to_dict('records')
            elif not isinstance(data, list):
                data = []
            
            if len(data) > 0:
                invoice_id = data[0].get('id')
                logger.info(f"🎉 40カラム請求書挿入成功: ID={invoice_id}, 企業={clean_data.get('issuer_name', 'N/A')}, ソース={clean_data.get('source_type', 'N/A')}")
                return data[0]
            else:
                raise Exception("データベースへの挿入に失敗しました")
                
        except Exception as e:
            logger.error(f"❌ 40カラム請求書挿入エラー: {str(e)[:200]}")
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

 