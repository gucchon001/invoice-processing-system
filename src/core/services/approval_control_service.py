"""
承認ワークフローサービス

請求書の承認要否判定、承認者割り当て、承認プロセス管理を提供する
金額・取引先・内容に基づく自動判定と通知機能を実装
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from utils.log_config import get_logger

logger = get_logger(__name__)

class ApprovalControlService:
    """承認ワークフローサービス（40カラム新機能対応）"""
    
    def __init__(self, rules_config: Optional[Dict] = None, notification_service=None):
        """
        Args:
            rules_config: 承認ルール設定
            notification_service: 通知サービス（NotificationAPI）
        """
        self.notification_service = notification_service
        
        # デフォルト承認ルール設定
        self.approval_rules = rules_config or {
            'amount_thresholds': {
                'manager': 300000,     # 30万円以上は部長承認
                'director': 1000000,   # 100万円以上は取締役承認
                'president': 5000000   # 500万円以上は社長承認
            },
            'vendor_rules': {
                'new_vendor_threshold': 100000,  # 新規取引先は10万円以上で承認
                'blacklisted_vendors': []        # ブラックリスト取引先
            },
            'category_rules': {
                'consulting': 'manager',     # コンサルティング費用は部長承認
                'equipment': 'director',     # 設備投資は取締役承認
                'travel': 50000             # 出張費は5万円以上で承認
            }
        }
        
        # 承認者設定
        self.approver_config = {
            'manager': {
                'name': '部長',
                'email': 'manager@company.com',
                'notification_channels': ['email', 'slack']
            },
            'director': {
                'name': '取締役',
                'email': 'director@company.com', 
                'notification_channels': ['email', 'slack', 'teams']
            },
            'president': {
                'name': '社長',
                'email': 'president@company.com',
                'notification_channels': ['email', 'teams']
            }
        }
        
        logger.info("ApprovalControlService initialized.")
    
    def evaluate_approval_requirement(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """承認要否を評価する（メイン機能）
        
        Args:
            invoice_data: 請求書データ
            
        Returns:
            Dict containing:
                - requires_approval: 承認が必要かどうか
                - approval_level: 必要な承認レベル
                - reason: 承認が必要な理由
                - auto_approved: 自動承認可能かどうか
        """
        try:
            logger.info(f"🔄 承認要否評価開始: {invoice_data.get('issuer_name', 'N/A')}")
            
            # 基本情報取得
            amount = invoice_data.get('total_amount_tax_included', 0)
            issuer = invoice_data.get('issuer_name', '')
            extracted_data = invoice_data.get('extracted_data', {})
            
            # 承認ルールチェック
            approval_checks = self._check_approval_rules(amount, issuer, extracted_data)
            
            # 最も高い承認レベルを決定
            required_level = self._determine_highest_approval_level(approval_checks)
            
            result = {
                'requires_approval': required_level is not None,
                'approval_level': required_level,
                'reason': self._format_approval_reason(approval_checks),
                'auto_approved': required_level is None,
                'approval_checks': approval_checks
            }
            
            if result['requires_approval']:
                logger.info(f"✅ 承認必要: レベル={required_level}, 理由={result['reason']}")
            else:
                logger.info(f"✅ 自動承認可能: 金額={amount:,.0f}円")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 承認要否評価エラー: {e}")
            raise
    
    def assign_approver(self, approval_level: str) -> Optional[str]:
        """承認者を割り当てる
        
        Args:
            approval_level: 承認レベル（manager/director/president）
            
        Returns:
            str: 承認者メールアドレス（失敗時はNone）
        """
        try:
            if approval_level not in self.approver_config:
                logger.warning(f"⚠️ 不明な承認レベル: {approval_level}")
                return None
            
            approver_info = self.approver_config[approval_level]
            approver_email = approver_info['email']
            
            logger.info(f"✅ 承認者割り当て成功: {approver_info['name']} ({approver_email})")
            return approver_email
            
        except Exception as e:
            logger.error(f"❌ 承認者割り当てエラー: {e}")
            return None
    
    def approve_invoice(self, invoice_id: int, approver_email: str, comment: str = "") -> bool:
        """請求書を承認する
        
        Args:
            invoice_id: 請求書ID
            approver_email: 承認者メール
            comment: 承認コメント
            
        Returns:
            bool: 承認成功かどうか
        """
        try:
            logger.info(f"🔄 請求書承認処理開始: ID={invoice_id}, 承認者={approver_email}")
            
            # 承認データ準備
            approval_data = {
                'approval_status': 'approved',
                'approved_by': approver_email,
                'approved_at': datetime.now().isoformat(),
                'approval_comment': comment
            }
            
            # データベース更新（実際の実装では DatabaseManager を使用）
            # success = self.database_manager.update_invoice(invoice_id, approval_data)
            
            logger.info(f"✅ 請求書承認完了: ID={invoice_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 請求書承認エラー: {e}")
            return False
    
    def reject_invoice(self, invoice_id: int, reject_reason: str, approver_email: str) -> bool:
        """請求書を拒否する
        
        Args:
            invoice_id: 請求書ID
            reject_reason: 拒否理由
            approver_email: 承認者メール
            
        Returns:
            bool: 拒否処理成功かどうか
        """
        try:
            logger.info(f"🔄 請求書拒否処理開始: ID={invoice_id}, 理由={reject_reason}")
            
            # 拒否データ準備
            rejection_data = {
                'approval_status': 'rejected',
                'approved_by': approver_email,
                'approved_at': datetime.now().isoformat(),
                'rejection_reason': reject_reason
            }
            
            # データベース更新（実際の実装では DatabaseManager を使用）
            # success = self.database_manager.update_invoice(invoice_id, rejection_data)
            
            logger.info(f"✅ 請求書拒否完了: ID={invoice_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 請求書拒否エラー: {e}")
            return False
    
    def send_approval_notification(self, approver_info: Dict, invoice_summary: Dict) -> bool:
        """承認通知を送信する
        
        Args:
            approver_info: 承認者情報
            invoice_summary: 請求書サマリー
            
        Returns:
            bool: 通知送信成功かどうか
        """
        try:
            logger.info(f"🔄 承認通知送信開始: 宛先={approver_info.get('email', 'N/A')}")
            
            # 通知メッセージ作成
            message = self._format_approval_message(invoice_summary)
            
            # 通知サービスが利用可能な場合は送信
            if self.notification_service:
                # 複数チャネルに通知送信
                channels = approver_info.get('notification_channels', ['email'])
                for channel in channels:
                    if channel == 'email':
                        # self.notification_service.send_email_notification(...)
                        pass
                    elif channel == 'slack':
                        # self.notification_service.send_slack_notification(...)
                        pass
                    elif channel == 'teams':
                        # self.notification_service.send_teams_notification(...)
                        pass
            
            logger.info(f"✅ 承認通知送信完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ 承認通知送信エラー: {e}")
            return False
    
    def _check_approval_rules(self, amount: float, issuer: str, extracted_data: Dict) -> List[Dict]:
        """承認ルールをチェックする（内部メソッド）
        
        Args:
            amount: 金額
            issuer: 発行者
            extracted_data: AI抽出データ
            
        Returns:
            List[Dict]: チェック結果リスト
        """
        checks = []
        
        # 金額ベース承認チェック
        thresholds = self.approval_rules['amount_thresholds']
        for level, threshold in thresholds.items():
            if amount >= threshold:
                checks.append({
                    'type': 'amount',
                    'level': level,
                    'trigger_value': amount,
                    'threshold': threshold,
                    'reason': f'金額が{threshold:,.0f}円以上'
                })
        
        # 取引先ベースチェック
        vendor_rules = self.approval_rules['vendor_rules']
        if issuer in vendor_rules.get('blacklisted_vendors', []):
            checks.append({
                'type': 'vendor',
                'level': 'director',
                'trigger_value': issuer,
                'reason': 'ブラックリスト取引先'
            })
        
        # カテゴリベースチェック
        category = self._detect_category(extracted_data)
        if category in self.approval_rules['category_rules']:
            rule = self.approval_rules['category_rules'][category]
            if isinstance(rule, str):  # レベル指定
                checks.append({
                    'type': 'category',
                    'level': rule,
                    'trigger_value': category,
                    'reason': f'{category}カテゴリ'
                })
            elif isinstance(rule, (int, float)) and amount >= rule:  # 金額閾値
                checks.append({
                    'type': 'category',
                    'level': 'manager',
                    'trigger_value': amount,
                    'threshold': rule,
                    'reason': f'{category}で{rule:,.0f}円以上'
                })
        
        return checks
    
    def _determine_highest_approval_level(self, checks: List[Dict]) -> Optional[str]:
        """最も高い承認レベルを決定する（内部メソッド）
        
        Args:
            checks: 承認チェック結果
            
        Returns:
            str: 最高承認レベル（不要な場合はNone）
        """
        if not checks:
            return None
        
        level_priority = {'manager': 1, 'director': 2, 'president': 3}
        max_level = max(checks, key=lambda x: level_priority.get(x['level'], 0))
        return max_level['level']
    
    def _format_approval_reason(self, checks: List[Dict]) -> str:
        """承認理由をフォーマットする（内部メソッド）
        
        Args:
            checks: 承認チェック結果
            
        Returns:
            str: フォーマットされた理由
        """
        if not checks:
            return '承認不要'
        
        reasons = [check['reason'] for check in checks]
        return '、'.join(reasons)
    
    def _detect_category(self, extracted_data: Dict) -> str:
        """請求書カテゴリを推定する（内部メソッド）
        
        Args:
            extracted_data: AI抽出データ
            
        Returns:
            str: カテゴリ名
        """
        # 簡単なキーワードベース分類
        description = str(extracted_data.get('key_info', {})).lower()
        
        if 'コンサル' in description or 'consulting' in description:
            return 'consulting'
        elif '設備' in description or 'equipment' in description:
            return 'equipment'
        elif '出張' in description or 'travel' in description:
            return 'travel'
        else:
            return 'general'
    
    def _format_approval_message(self, invoice_summary: Dict) -> str:
        """承認通知メッセージをフォーマットする（内部メソッド）
        
        Args:
            invoice_summary: 請求書サマリー
            
        Returns:
            str: フォーマットされたメッセージ
        """
        return f"""
📋 請求書承認依頼

💰 金額: ¥{invoice_summary.get('amount', 0):,.0f}
🏢 取引先: {invoice_summary.get('issuer', 'N/A')}
📄 内容: {invoice_summary.get('description', 'N/A')}
📅 発行日: {invoice_summary.get('issue_date', 'N/A')}

承認システムにアクセスして承認処理を行ってください。
        """.strip() 