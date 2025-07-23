"""
統一された請求書データ検証モジュール

OCRテスト機能の詳細な検証ロジックをベースに、
請求書アップロード機能でも使用可能な共通検証システムを提供します。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class InvoiceValidator:
    """請求書データの統一検証システム"""
    
    def __init__(self):
        """検証システムの初期化"""
        self.validation_rules = {
            'data_format': True,     # データ型・フォーマット検証
            'amounts': True,         # 金額検証（外貨対応）
            'dates': True,          # 日付検証
            'foreign_currency': True, # 外貨取引検証
            'line_items': True      # 明細整合性検証
        }
    
    def validate_invoice_data(self, result: Dict[str, Any], 
                            strict_mode: bool = False) -> Dict[str, Any]:
        """
        請求書データの統合検証
        
        Args:
            result: 検証対象の請求書データ
            strict_mode: 厳格モード（警告もエラーとして扱う）
            
        Returns:
            検証結果辞書
        """
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "error_categories": {
                "required_fields": [],
                "data_format": [],
                "business_logic": []
            },
            "validation_summary": {
                "total_issues": 0,
                "critical_issues": 0,
                "warnings": 0
            }
        }
        
        try:
            # 各検証ルールを実行
            if self.validation_rules['data_format']:
                self._validate_data_formats(result, validation)
            
            if self.validation_rules['amounts']:
                self._validate_amounts(result, validation)
            
            if self.validation_rules['dates']:
                self._validate_dates(result, validation)
            
            if self.validation_rules['foreign_currency']:
                self._validate_foreign_currency(result, validation)
            
            if self.validation_rules['line_items']:
                self._validate_line_items(result, validation)
            
            # 必須フィールド検証
            self._validate_required_fields(result, validation)
            
            # 厳格モードの場合、警告もエラーとして扱う
            if strict_mode and validation["warnings"]:
                validation["errors"].extend(validation["warnings"])
                validation["warnings"] = []
                validation["is_valid"] = False
            
            # サマリー計算
            validation["validation_summary"]["total_issues"] = (
                len(validation["errors"]) + len(validation["warnings"])
            )
            validation["validation_summary"]["critical_issues"] = len(validation["errors"])
            validation["validation_summary"]["warnings"] = len(validation["warnings"])
            
            logger.info(f"検証完了: エラー{len(validation['errors'])}件, 警告{len(validation['warnings'])}件")
            
        except Exception as e:
            logger.error(f"検証中にエラーが発生しました: {e}")
            validation["errors"].append(f"検証システムエラー: {str(e)}")
            validation["is_valid"] = False
        
        return validation
    
    def _validate_required_fields(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """必須フィールド検証"""
        required_fields = {
            "issuer": "請求元企業名",
            "amount_inclusive_tax": "税込金額", 
            "issue_date": "発行日"
        }
        
        for field, field_name in required_fields.items():
            if not result.get(field):
                error_msg = f"必須フィールドが不足しています: {field_name}"
                validation["errors"].append(error_msg)
                validation["error_categories"]["required_fields"].append(error_msg)
                validation["is_valid"] = False
    
    def _validate_data_formats(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """データ型・フォーマット検証"""
        
        # 通貨コード正規化・検証
        currency = result.get("currency")
        if currency:
            # 通貨コード正規化
            normalized_currency = self._normalize_currency_code(currency)
            
            # 正規化後の通貨コードで結果を更新
            if normalized_currency != currency:
                result["currency"] = normalized_currency
                # 正規化されたことを記録（ログ用）
                logger.info(f"通貨コード正規化: {currency} -> {normalized_currency}")
            
            # 対応通貨コードチェック
            valid_currencies = ["JPY", "USD", "EUR", "GBP", "AUD", "CAD", "CHF"]
            if normalized_currency not in valid_currencies:
                error_msg = f"未対応の通貨コードです: {normalized_currency}（元: {currency}）"
                validation["warnings"].append(error_msg)
                validation["error_categories"]["data_format"].append(error_msg)
        
        # 金額データ型チェック（JSONプロンプト対応）
        for amount_field in ["amount_inclusive_tax", "amount_exclusive_tax"]:
            amount = result.get(amount_field)
            if amount is not None and not isinstance(amount, (int, float)):
                try:
                    float(amount)
                except (ValueError, TypeError):
                    error_msg = f"金額フィールド '{amount_field}' のフォーマットが不正です: {amount}"
                    validation["errors"].append(error_msg)
                    validation["error_categories"]["data_format"].append(error_msg)
                    validation["is_valid"] = False
        
        # 企業名の長さチェック（JSONプロンプト対応）
        issuer = result.get("issuer")
        if issuer and len(str(issuer)) > 100:
            warning_msg = f"請求元企業名が長すぎます（{len(str(issuer))}文字）"
            validation["warnings"].append(warning_msg)
            validation["error_categories"]["data_format"].append(warning_msg)
    
    def _normalize_currency_code(self, currency: str) -> str:
        """
        通貨コードの正規化
        
        Args:
            currency: 元の通貨コード
            
        Returns:
            正規化された通貨コード（ISO 4217準拠）
        """
        if not currency:
            return currency
        
        currency_str = str(currency).strip()
        
        # 円の正規化
        yen_patterns = ["円", "￥", "¥", "JPY", "jpy", "Yen", "yen", "YEN"]
        if currency_str in yen_patterns:
            return "JPY"
        
        # ドルの正規化
        dollar_patterns = ["ドル", "＄", "$", "USD", "usd", "Dollar", "dollar", "DOLLAR", "US$", "US Dollar"]
        if currency_str in dollar_patterns:
            return "USD"
        
        # ユーロの正規化
        euro_patterns = ["€", "EUR", "eur", "Euro", "euro", "EURO"]
        if currency_str in euro_patterns:
            return "EUR"
        
        # ポンドの正規化
        pound_patterns = ["£", "GBP", "gbp", "Pound", "pound", "POUND", "Sterling"]
        if currency_str in pound_patterns:
            return "GBP"
        
        # オーストラリアドルの正規化
        aud_patterns = ["AUD", "aud", "A$", "AU$", "Australian Dollar"]
        if currency_str in aud_patterns:
            return "AUD"
        
        # カナダドルの正規化
        cad_patterns = ["CAD", "cad", "C$", "CA$", "Canadian Dollar"]
        if currency_str in cad_patterns:
            return "CAD"
        
        # スイスフランの正規化
        chf_patterns = ["CHF", "chf", "Swiss Franc", "Fr", "SFr"]
        if currency_str in chf_patterns:
            return "CHF"
        
        # 正規化できない場合は大文字にして返す
        return currency_str.upper()
    
    def _validate_amounts(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """金額検証（外貨取引対応・JSONプロンプト対応）"""
        tax_included = result.get("amount_inclusive_tax")
        tax_excluded = result.get("amount_exclusive_tax")
        currency = result.get("currency", "JPY")
        
        # 外貨取引判定
        is_foreign_currency = currency and currency.upper() != "JPY"
        
        # 数値変換試行
        try:
            if tax_included is not None:
                tax_included = float(tax_included)
            if tax_excluded is not None:
                tax_excluded = float(tax_excluded)
        except (ValueError, TypeError):
            return  # フォーマットエラーは別の検証で処理済み
        
        # 負の金額チェック
        if tax_included is not None and tax_included < 0:
            warning_msg = f"税込金額が負の値です: {tax_included}（返金・調整の可能性）"
            validation["warnings"].append(warning_msg)
            validation["error_categories"]["business_logic"].append(warning_msg)
        
        # 異常に大きな金額チェック
        if tax_included is not None and tax_included > 10000000:  # 1000万円超
            warning_msg = f"税込金額が異常に高額です: {tax_included:,.0f}円"
            validation["warnings"].append(warning_msg)
            validation["error_categories"]["business_logic"].append(warning_msg)
        
        # 税込・税抜金額の整合性チェック（外貨取引対応）
        if (tax_included is not None and tax_excluded is not None and 
            tax_included > 0 and tax_excluded > 0):
            
            if is_foreign_currency:
                # 外貨取引では税込=税抜が正常（海外事業者は非課税）
                if tax_included == tax_excluded:
                    # 正常なパターンなので警告は出さない
                    pass
                elif tax_included < tax_excluded:
                    # 税込 < 税抜は明らかに異常
                    warning_msg = f"外貨取引で税込金額({tax_included:,.0f})が税抜金額({tax_excluded:,.0f})を下回っています"
                    validation["warnings"].append(warning_msg)
                    validation["error_categories"]["business_logic"].append(warning_msg)
                # 税込 > 税抜の場合は税率計算へ進む
            else:
                # 国内取引（JPY）の場合は従来通りの判定
                if tax_included <= tax_excluded:
                    warning_msg = f"税込金額({tax_included:,.0f})が税抜金額({tax_excluded:,.0f})以下です"
                    validation["warnings"].append(warning_msg)
                    validation["error_categories"]["business_logic"].append(warning_msg)
            
            # 税率計算（外貨取引対応）
            if tax_excluded > 0:
                tax_rate = ((tax_included - tax_excluded) / tax_excluded) * 100
                
                if is_foreign_currency:
                    # 外貨取引では税率0%（税込=税抜）が正常
                    if abs(tax_rate) < 0.1:  # 0%前後（計算誤差考慮）
                        # 正常なパターンなので警告は出さない
                        pass
                    elif tax_rate < 0:
                        # 負の税率は明らかに異常
                        warning_msg = f"外貨取引で計算された税率が負の値です: {tax_rate:.1f}%"
                        validation["warnings"].append(warning_msg)
                        validation["error_categories"]["business_logic"].append(warning_msg)
                    elif tax_rate > 15:
                        # 異常に高い税率
                        warning_msg = f"外貨取引で計算された税率が異常に高いです: {tax_rate:.1f}%"
                        validation["warnings"].append(warning_msg)
                        validation["error_categories"]["business_logic"].append(warning_msg)
                else:
                    # 国内取引（JPY）の場合は従来通りの判定
                    if tax_rate < 5 or tax_rate > 15:  # 消費税率の妥当性チェック
                        warning_msg = f"計算された税率が異常です: {tax_rate:.1f}%"
                        validation["warnings"].append(warning_msg)
                        validation["error_categories"]["business_logic"].append(warning_msg)
    
    def _validate_dates(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """日付検証"""
        issue_date = result.get("issue_date")
        due_date = result.get("due_date")
        
        # 日付フォーマットチェック
        parsed_issue_date = None
        parsed_due_date = None
        
        if issue_date:
            try:
                parsed_issue_date = datetime.fromisoformat(str(issue_date))
            except ValueError:
                warning_msg = f"発行日のフォーマットが不正です: {issue_date}"
                validation["warnings"].append(warning_msg)
                validation["error_categories"]["data_format"].append(warning_msg)
        
        if due_date:
            try:
                parsed_due_date = datetime.fromisoformat(str(due_date))
            except ValueError:
                warning_msg = f"支払期日のフォーマットが不正です: {due_date}"
                validation["warnings"].append(warning_msg)
                validation["error_categories"]["data_format"].append(warning_msg)
        
        # 日付の論理チェック（境界値対応）
        if parsed_issue_date and parsed_due_date:
            if parsed_due_date < parsed_issue_date:
                warning_msg = "支払期日が発行日より前になっています"
                validation["warnings"].append(warning_msg)
                validation["error_categories"]["business_logic"].append(warning_msg)
            # 同一日の場合は正常（即日支払いもビジネス上有効）
        
        # 異常に古い/新しい日付チェック
        current_date = datetime.now()
        if parsed_issue_date:
            if parsed_issue_date > current_date + timedelta(days=30):
                warning_msg = "発行日が未来すぎます"
                validation["warnings"].append(warning_msg)
                validation["error_categories"]["business_logic"].append(warning_msg)
            
            if parsed_issue_date < current_date - timedelta(days=1095):  # 3年前
                warning_msg = "発行日が3年以上前です"
                validation["warnings"].append(warning_msg)
                validation["error_categories"]["business_logic"].append(warning_msg)
    
    def _validate_foreign_currency(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """外貨取引チェック（JSONプロンプト対応）"""
        currency = result.get("currency")
        issuer = result.get("issuer", "")
        
        if currency and currency != "JPY":
            # 外貨取引の基本警告
            warning_msg = f"外貨取引のため為替レート確認が必要です（{currency}）"
            validation["warnings"].append(warning_msg)
            validation["error_categories"]["business_logic"].append(warning_msg)
            
            # 海外事業者チェック（簡易判定）
            foreign_keywords = ["LLC", "Ltd", "Inc", "Corp", "GmbH", "Limited", "Ireland", "Singapore"]
            if any(keyword in issuer for keyword in foreign_keywords):
                warning_msg = "海外事業者のため消費税処理を確認してください"
                validation["warnings"].append(warning_msg)
                validation["error_categories"]["business_logic"].append(warning_msg)
    
    def _validate_line_items(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """明細整合性チェック"""
        line_items = result.get("line_items", [])
        
        if line_items and isinstance(line_items, list):
            # 明細合計の計算
            line_total = 0
            invalid_items = 0
            
            for i, item in enumerate(line_items):
                if not isinstance(item, dict):
                    continue
                
                amount = item.get("amount")
                if amount is not None:
                    try:
                        line_total += float(amount)
                    except (ValueError, TypeError):
                        invalid_items += 1
                        warning_msg = f"明細{i+1}の金額フォーマットが不正です: {amount}"
                        validation["warnings"].append(warning_msg)
                        validation["error_categories"]["data_format"].append(warning_msg)
            
            # 請求金額との突合（JSONプロンプト対応）
            invoice_total = result.get("amount_exclusive_tax")
            if (invoice_total is not None and isinstance(invoice_total, (int, float)) and 
                invoice_total > 0 and line_total > 0):
                
                difference_rate = abs(line_total - invoice_total) / invoice_total
                if difference_rate > 0.1:  # 10%以上の差異
                    warning_msg = f"明細合計({line_total:,.0f})と請求金額({invoice_total:,.0f})に{difference_rate*100:.1f}%の差異があります"
                    validation["warnings"].append(warning_msg)
                    validation["error_categories"]["business_logic"].append(warning_msg)
        
        elif line_items is not None and not isinstance(line_items, list):
            warning_msg = "明細情報のフォーマットが不正です"
            validation["warnings"].append(warning_msg)
            validation["error_categories"]["data_format"].append(warning_msg)

    def get_validation_summary_text(self, validation: Dict[str, Any]) -> str:
        """検証結果のサマリーテキストを生成"""
        summary = validation["validation_summary"]
        
        if summary["total_issues"] == 0:
            return "✅ 検証完了：問題なし"
        
        parts = []
        if summary["critical_issues"] > 0:
            parts.append(f"❌ エラー: {summary['critical_issues']}件")
        if summary["warnings"] > 0:
            parts.append(f"⚠️ 警告: {summary['warnings']}件")
        
        return " / ".join(parts) 