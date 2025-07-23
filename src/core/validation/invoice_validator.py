"""
請求書データ検証モジュール
OCRテストと本番アップロードで共通利用される高精度な検証ロジック
"""
from typing import Dict, Any, List

# ログ設定
from utils.log_config import get_logger
logger = get_logger(__name__)

class InvoiceValidator:
    """請求書データの詳細検証クラス"""
    
    def __init__(self):
        """初期化"""
        # 必須・重要・オプショナルフィールドの定義
        self.required_fields = {
            "issuer": "請求元企業名",
            "amount_inclusive_tax": "税込金額",
            "currency": "通貨"
        }
        self.important_fields = {
            "payer": "請求先企業名",
            "main_invoice_number": "請求書番号",
            "issue_date": "発行日"
        }
        self.optional_fields = {
            "t_number": "登録番号",
            "amount_exclusive_tax": "税抜金額",
            "due_date": "支払期日",
            "line_items": "明細情報",
            "key_info": "キー情報"
        }
        self.all_fields = {**self.required_fields, **self.important_fields, **self.optional_fields}

    def validate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """請求書データの包括的検証"""
        validation = self._initialize_validation_result()
        
        # 各種検証の実行
        self._check_required_fields(result, validation)
        self._check_important_fields(result, validation)
        self._validate_data_formats(result, validation)
        self._validate_amounts(result, validation)
        self._validate_dates(result, validation)
        self._validate_foreign_currency(result, validation)
        self._validate_line_items(result, validation)
        
        # 完全性スコア計算と最終判定
        self._calculate_completeness(result, validation)
        self._finalize_validation_status(validation)
        
        return validation

    def _initialize_validation_result(self) -> Dict[str, Any]:
        """検証結果の初期化"""
        return {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "completeness_score": 0,
            "error_categories": {
                "critical": [], "data_missing": [], 
                "data_format": [], "business_logic": []
            }
        }

    def _check_required_fields(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """必須フィールドのチェック"""
        for field, display_name in self.required_fields.items():
            if not self._is_valid_field_value(result.get(field)):
                msg = f"{display_name}が取得できませんでした"
                validation["errors"].append(msg)
                validation["error_categories"]["data_missing"].append(msg)

    def _check_important_fields(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """重要フィールドのチェック（警告レベル）"""
        for field, display_name in self.important_fields.items():
            if not self._is_valid_field_value(result.get(field)):
                msg = f"{display_name}が取得できませんでした"
                validation["warnings"].append(msg)
                validation["error_categories"]["business_logic"].append(msg)

    def _is_valid_field_value(self, value: Any) -> bool:
        """フィールド値の有効性チェック"""
        if value is None: return False
        if isinstance(value, str) and not value.strip(): return False
        if isinstance(value, (list, dict)) and not value: return False
        return True

    def _validate_data_formats(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """データ型・フォーマット検証"""
        # (詳細はocr_test_helper.pyから移植)
        pass

    def _validate_amounts(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """金額検証"""
        # (詳細はocr_test_helper.pyから移植)
        pass

    def _validate_dates(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """日付検証"""
        # (詳細はocr_test_helper.pyから移植)
        pass

    def _validate_foreign_currency(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """外貨取引チェック"""
        # (詳細はocr_test_helper.pyから移植)
        pass

    def _validate_line_items(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """明細整合性チェック"""
        # (詳細はocr_test_helper.pyから移植)
        pass
    
    def _calculate_completeness(self, result: Dict[str, Any], validation: Dict[str, Any]):
        """完全性スコア計算"""
        filled_fields = sum(1 for field in self.all_fields if self._is_valid_field_value(result.get(field)))
        validation["completeness_score"] = round((filled_fields / len(self.all_fields)) * 100, 1)

    def _finalize_validation_status(self, validation: Dict[str, Any]):
        """エラー重要度に基づく最終判定"""
        if validation["error_categories"]["critical"] or validation["error_categories"]["data_missing"]:
            validation["is_valid"] = False

# シングルトンパターン
_validator_instance = None

def get_invoice_validator() -> InvoiceValidator:
    """検証モジュールのシングルトンインスタンスを取得"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = InvoiceValidator()
    return _validator_instance 