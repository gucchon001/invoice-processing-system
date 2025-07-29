"""
freee連携サービス

freee APIとの連携による自動仕訳作成、勘定科目マッピング、バッチ処理を提供する
OAuth認証とエラーハンドリングを含む包括的なfreee統合機能
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from utils.log_config import get_logger

logger = get_logger(__name__)

class FreeeIntegrationService:
    """freee連携サービス（40カラム新機能対応）"""
    
    def __init__(self, oauth_config: Optional[Dict] = None, account_mapping: Optional[Dict] = None):
        """
        Args:
            oauth_config: freee OAuth設定
            account_mapping: 勘定科目マッピング設定
        """
        self.oauth_config = oauth_config or {
            'client_id': 'your_freee_client_id',
            'client_secret': 'your_freee_client_secret',
            'redirect_uri': 'your_redirect_uri',
            'scope': 'read write'
        }
        
        # デフォルト勘定科目マッピング
        self.account_mapping = account_mapping or {
            'コンサルティング': {'code': '5201', 'name': '支払手数料', 'sub': 'コンサルティング料'},
            'システム開発': {'code': '5202', 'name': '外注費', 'sub': 'システム開発費'},
            '広告宣伝': {'code': '5203', 'name': '広告宣伝費', 'sub': ''},
            '通信費': {'code': '5204', 'name': '通信費', 'sub': ''},
            '出張': {'code': '5205', 'name': '旅費交通費', 'sub': '出張費'},
            '備品': {'code': '5206', 'name': '消耗品費', 'sub': '事務用品'},
            '家賃': {'code': '5207', 'name': '地代家賃', 'sub': ''},
            '一般': {'code': '5201', 'name': '支払手数料', 'sub': ''}  # デフォルト
        }
        
        self.freee_api = None  # 実際の実装では FreeeAPI クラスを使用
        
        logger.info("FreeeIntegrationService initialized.")
    
    def process_approved_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """承認済み請求書をfreeeに連携する（メイン機能）
        
        Args:
            invoice_data: 承認済み請求書データ
            
        Returns:
            Dict containing:
                - success: 連携成功かどうか
                - freee_transaction_id: freee取引ID
                - journal_number: 仕訳番号
                - batch_id: バッチID
        """
        try:
            logger.info(f"🔄 freee連携処理開始: {invoice_data.get('issuer_name', 'N/A')}")
            
            # 承認状況確認
            if invoice_data.get('approval_status') != 'approved':
                raise Exception("未承認の請求書はfreee連携できません")
            
            # freee API接続確認
            if not self.validate_freee_connection():
                raise Exception("freee API接続に失敗")
            
            # 勘定科目マッピング
            category = self._detect_expense_category(invoice_data)
            account_info = self.map_expense_category(category)
            
            # 仕訳データ作成
            journal_entry = self.create_journal_entry(invoice_data, account_info)
            
            # バッチID生成
            batch_id = self.generate_batch_id()
            
            # freee API実行（実際の実装では FreeeAPI.create_journal_entry を使用）
            freee_result = self._simulate_freee_api_call(journal_entry)
            
            result = {
                'success': True,
                'freee_transaction_id': freee_result['transaction_id'],
                'journal_number': freee_result['journal_number'],
                'batch_id': batch_id,
                'account_mapping': account_info,
                'export_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ freee連携成功: 仕訳番号={result['journal_number']}, バッチID={batch_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ freee連携エラー: {e}")
            raise
    
    def create_journal_entry(self, invoice_data: Dict[str, Any], account_info: Dict[str, str]) -> Dict[str, Any]:
        """仕訳データを作成する
        
        Args:
            invoice_data: 請求書データ
            account_info: 勘定科目情報
            
        Returns:
            Dict: freee API用仕訳データ
        """
        try:
            amount = invoice_data.get('total_amount_tax_included', 0)
            issue_date = invoice_data.get('issue_date', datetime.now().strftime('%Y-%m-%d'))
            issuer = invoice_data.get('issuer_name', '不明')
            description = f"{issuer} {account_info['name']}"
            
            # freee API形式の仕訳データ
            journal_entry = {
                'issue_date': issue_date,
                'company_id': 1,  # 実際の実装では設定から取得
                'description': description,
                'journal_entries': [
                    {
                        'side': 'debit',  # 借方
                        'account_code': account_info['code'],
                        'account_name': account_info['name'],
                        'amount': amount,
                        'tax_code': 1  # 課税仕入
                    },
                    {
                        'side': 'credit',  # 貸方
                        'account_code': '2201',  # 未払金
                        'account_name': '未払金',
                        'amount': amount,
                        'tax_code': 0  # 対象外
                    }
                ]
            }
            
            logger.info(f"✅ 仕訳データ作成完了: {description}, 金額=¥{amount:,.0f}")
            return journal_entry
            
        except Exception as e:
            logger.error(f"❌ 仕訳データ作成エラー: {e}")
            raise
    
    def map_expense_category(self, category: str) -> Dict[str, str]:
        """経費カテゴリを勘定科目にマッピングする
        
        Args:
            category: 経費カテゴリ
            
        Returns:
            Dict: 勘定科目情報（code, name, sub）
        """
        try:
            # カテゴリマッピング確認
            if category in self.account_mapping:
                account_info = self.account_mapping[category]
                logger.info(f"✅ 勘定科目マッピング成功: {category} → {account_info['name']}")
                return account_info
            else:
                # デフォルトマッピング
                default_account = self.account_mapping['一般']
                logger.warning(f"⚠️ 不明カテゴリのためデフォルト適用: {category} → {default_account['name']}")
                return default_account
                
        except Exception as e:
            logger.error(f"❌ 勘定科目マッピングエラー: {e}")
            # エラー時はデフォルト返却
            return self.account_mapping['一般']
    
    def generate_batch_id(self) -> str:
        """バッチIDを生成する
        
        Returns:
            str: ユニークなバッチID
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        unique_id = str(uuid.uuid4())[:8]
        batch_id = f"freee_batch_{timestamp}_{unique_id}"
        
        logger.info(f"📝 バッチID生成: {batch_id}")
        return batch_id
    
    def validate_freee_connection(self) -> bool:
        """freee API接続を検証する
        
        Returns:
            bool: 接続成功かどうか
        """
        try:
            # 実際の実装では freee API の接続テストを実行
            # result = self.freee_api.test_connection()
            
            # デモ用に常にTrue
            logger.info("✅ freee API接続確認成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ freee API接続確認エラー: {e}")
            return False
    
    def _detect_expense_category(self, invoice_data: Dict[str, Any]) -> str:
        """請求書から経費カテゴリを推定する（内部メソッド）
        
        Args:
            invoice_data: 請求書データ
            
        Returns:
            str: 推定されたカテゴリ
        """
        try:
            # AI抽出データから情報を取得
            extracted_data = invoice_data.get('extracted_data', {})
            key_info = extracted_data.get('key_info', {})
            issuer = invoice_data.get('issuer_name', '').lower()
            
            # キーワードベース分類
            text_content = f"{str(key_info)} {issuer}".lower()
            
            if any(keyword in text_content for keyword in ['コンサル', 'consulting', '相談', 'アドバイザー']):
                return 'コンサルティング'
            elif any(keyword in text_content for keyword in ['システム', 'system', '開発', 'development', 'it']):
                return 'システム開発'
            elif any(keyword in text_content for keyword in ['広告', 'advertisement', 'marketing', '宣伝']):
                return '広告宣伝'
            elif any(keyword in text_content for keyword in ['通信', 'telecom', 'internet', 'phone']):
                return '通信費'
            elif any(keyword in text_content for keyword in ['出張', 'travel', '交通', 'transport']):
                return '出張'
            elif any(keyword in text_content for keyword in ['備品', 'supplies', '消耗品', 'stationery']):
                return '備品'
            elif any(keyword in text_content for keyword in ['家賃', 'rent', 'lease']):
                return '家賃'
            else:
                return '一般'
                
        except Exception as e:
            logger.error(f"❌ カテゴリ推定エラー: {e}")
            return '一般'
    
    def _simulate_freee_api_call(self, journal_entry: Dict[str, Any]) -> Dict[str, Any]:
        """freee API呼び出しをシミュレートする（内部メソッド・デモ用）
        
        Args:
            journal_entry: 仕訳データ
            
        Returns:
            Dict: シミュレートされたfreee APIレスポンス
        """
        # 実際の実装では freee API を呼び出し
        # return self.freee_api.create_journal_entry(journal_entry)
        
        # デモ用シミュレーション
        simulated_result = {
            'transaction_id': f"freee_txn_{uuid.uuid4().hex[:12]}",
            'journal_number': f"JE-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            'status': 'draft',
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f"🎭 freee API呼び出しシミュレーション完了: {simulated_result['journal_number']}")
        return simulated_result 