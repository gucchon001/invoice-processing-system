"""
請求書照合サービス - JSONプロンプト対応版

企業名照合（master_matcher）と統合照合（integrated_matcher）機能を提供
JSONベースプロンプト管理による動的な照合処理を実現
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from infrastructure.ai.gemini_helper import GeminiAPIManager
from core.services.unified_prompt_manager import UnifiedPromptManager

logger = logging.getLogger(__name__)

class InvoiceMatcherService:
    """請求書照合統合サービス"""
    
    def __init__(self):
        """照合サービスを初期化"""
        self.gemini_manager = GeminiAPIManager()
        self.prompt_manager = UnifiedPromptManager()
        logger.info("InvoiceMatcherService初期化完了")
    
    def match_company_name(self, issuer_name: str, master_company_list: List[str]) -> Optional[Dict[str, Any]]:
        """
        企業名照合機能（master_matcher）- 強化版対応
        
        Args:
            issuer_name: 請求書の請求元名
            master_company_list: 支払マスタの企業名リスト
            
        Returns:
            照合結果辞書またはNone
        """
        try:
            logger.info(f"企業名照合開始: {issuer_name} vs {len(master_company_list)}件のマスタ")
            
            # 1. 強化版照合（辞書ベース）を最初に試行
            enhanced_result = self._try_enhanced_matching(issuer_name, master_company_list)
            
            if enhanced_result and enhanced_result.get("confidence_score", 0) >= 0.85:
                logger.info("強化版照合成功")
                return enhanced_result
            
            # 2. 従来のプロンプトベース照合にフォールバック
            logger.info("強化版照合失敗、プロンプトベース照合にフォールバック")
            return self._match_with_prompt(issuer_name, master_company_list)
            
        except Exception as e:
            logger.error(f"企業名照合でエラー: {e}")
            return None
    
    def _match_with_prompt(self, issuer_name: str, master_company_list: List[str]) -> Optional[Dict[str, Any]]:
        """プロンプトベースの企業名照合"""
        try:
            variables = {
                "issuer_name": issuer_name,
                "master_company_list": master_company_list  # JSON文字列ではなく配列として直接渡す
            }
            
            try:
                # 統一プロンプト管理システムを使用
                system_prompt, user_prompt = self.prompt_manager.format_prompt_for_gemini("master_matcher_prompt", variables)
                prompt = f"{system_prompt}\n\n{user_prompt}"
            except Exception as e:
                logger.error(f"プロンプト生成エラー: {e}")
                # フォールバック: 手動でプロンプトを構築
                company_list_str = json.dumps(master_company_list, ensure_ascii=False)
                prompt = f"""
以下の請求元企業名を支払マスタの企業名リストと照合してください。

請求元企業名: {issuer_name}

支払マスタ企業名リスト:
{company_list_str}

最も類似度が高い企業名を特定し、以下のJSON形式で回答してください：

{{
    "matched_company": "マッチした企業名",
  "confidence_score": 0.95,
    "match_reason": "マッチ理由",
    "is_perfect_match": true
}}
"""
            
            logger.info(f"企業名照合プロンプト実行: {issuer_name}")
            ai_result = self.gemini_manager.generate_text(prompt)
            
            if ai_result:
                # JSON解析
                parsed_result = self._parse_json_response(ai_result)
                
                if parsed_result:
                    # 結果の後処理
                    final_result = self._process_matching_result(parsed_result, issuer_name, master_company_list)
                    
                    if final_result:
                        logger.info(f"企業名照合成功: {final_result.get('matched_company', 'N/A')} (信頼度: {final_result.get('confidence_score', 0):.2f})")
                        return final_result
            
            logger.warning(f"企業名照合失敗: {issuer_name}")
            return None
            
        except Exception as e:
            logger.error(f"プロンプトベース企業名照合でエラー: {e}")
            return None
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        Gemini AIレスポンスからJSON部分を抽出
        
        Args:
            response: Gemini AIからの生レスポンス
            
        Returns:
            抽出されたJSON文字列
        """
        try:
            # パターン1: ```json ～ ``` ブロック
            json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                return json_match.group(1).strip()
            
            # パターン2: ```～``` ブロック（json指定なし）
            code_match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
            if code_match:
                potential_json = code_match.group(1).strip()
                # JSONっぽいかチェック
                if potential_json.startswith('{') and potential_json.endswith('}'):
                    return potential_json
            
            # パターン3: { ～ } の最初のJSONオブジェクト
            brace_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if brace_match:
                return brace_match.group(0)
            
            # どれも見つからない場合は元の文字列をそのまま返す
            logger.warning("JSONパターンが見つかりません。元のレスポンスを返します。")
            return response
            
        except Exception as e:
            logger.error(f"JSON抽出エラー: {e}")
            return response

    def _try_enhanced_matching(self, issuer_name: str, master_company_list: List[str]) -> Optional[Dict[str, Any]]:
        """強化版照合を試行"""
        try:
            from utils.company_name_normalizer import get_company_normalizer
            
            normalizer = get_company_normalizer()
            result = normalizer.enhanced_company_matching(issuer_name, master_company_list)
            
            if result:
                logger.info(f"強化版照合結果: {result.get('matched_company_name')} (確信度: {result.get('confidence_score', 0):.2f})")
            
            return result
            
        except Exception as e:
            logger.warning(f"強化版照合エラー: {e}")
            return None
    
    def match_integrated_invoice(self, invoice_data: Dict[str, Any], 
                               payment_masters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        統合請求書照合機能（integrated_matcher）
        
        Args:
            invoice_data: 請求書データ
            payment_masters: 支払マスタデータリスト
            
        Returns:
            照合結果辞書またはNone
        """
        try:
            logger.info(f"統合請求書照合開始: {invoice_data.get('issuer', 'N/A')}")
            
            variables = {
                "invoice_data": invoice_data,
                "payment_masters": payment_masters
            }
            
            try:
                # 統一プロンプト管理システムを使用
                system_prompt, user_prompt = self.prompt_manager.format_prompt_for_gemini("integrated_matcher_prompt", variables)
                prompt = f"{system_prompt}\n\n{user_prompt}"
            except Exception as e:
                logger.error(f"統合照合プロンプト生成エラー: {e}")
                # フォールバック処理
                prompt = self._create_fallback_integrated_prompt(invoice_data, payment_masters)
            
            # Gemini APIで照合実行
            ai_result = self.gemini_manager.generate_text(prompt)
            
            if ai_result:
                parsed_result = self._parse_json_response(ai_result)
                
                if parsed_result and self._validate_integrated_result(parsed_result):
                    logger.info(f"統合照合成功: {parsed_result.get('final_classification', 'N/A')}")
                    return parsed_result
            
            logger.warning("統合照合失敗")
            return None
            
        except Exception as e:
            logger.error(f"統合請求書照合でエラー: {e}")
            return None
    
    def extract_invoice_advanced(self, invoice_text: str, 
                               context_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        高度請求書情報抽出（invoice_extractor）
        
        Args:
            invoice_text: 請求書テキスト
            context_info: コンテキスト情報
            
        Returns:
            抽出結果辞書またはNone
        """
        try:
            logger.info("高度請求書情報抽出開始")
            
            variables = {
                "invoice_text": invoice_text,
                "context_info": context_info or {}
            }
            
            try:
                # 統一プロンプト管理システムを使用
                system_prompt, user_prompt = self.prompt_manager.format_prompt_for_gemini("invoice_extractor_prompt", variables)
                prompt = f"{system_prompt}\n\n{user_prompt}"
            except Exception as e:
                logger.error(f"抽出プロンプト生成エラー: {e}")
                # フォールバック処理
                prompt = self._create_fallback_extraction_prompt(invoice_text)
            
            # Gemini APIで抽出実行
            ai_result = self.gemini_manager.generate_text(prompt)
            
            if ai_result:
                parsed_result = self._parse_json_response(ai_result)
                
                if parsed_result:
                    logger.info("高度情報抽出成功")
                    return parsed_result
            
            logger.warning("高度情報抽出失敗")
                return None
                
        except Exception as e:
            logger.error(f"高度請求書情報抽出でエラー: {e}")
            return None
    
    def _post_process_key_info(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        キー情報の後処理・強化
        
        Args:
            extracted_data: 抽出された生データ
            
        Returns:
            後処理済みデータ
        """
        try:
            # key_infoが空の場合は基本情報から補完
            key_info = extracted_data.get("key_info", {})
            
            if not key_info or key_info == {}:
                # 基本情報から重要なキー情報を抽出
                key_info = self._extract_fallback_keys(extracted_data)
                extracted_data["key_info"] = key_info
            
            # キー情報の標準化
            standardized_keys = self._standardize_key_names(key_info)
            extracted_data["key_info"] = standardized_keys
            
            logger.debug(f"キー情報後処理完了: {len(standardized_keys)}件のキー")
            return extracted_data
            
        except Exception as e:
            logger.error(f"キー情報後処理エラー: {e}")
            return extracted_data
    
    def _extract_fallback_keys(self, data: Dict[str, Any]) -> Dict[str, str]:
        """基本情報からフォールバックキー情報を抽出（優先度順）"""
        fallback_keys = {}
        
        # 【最優先】企業・アカウント特定用キー
        # T番号を顧客コードとして活用
        if data.get("t_number"):
            fallback_keys["登録番号"] = data["t_number"]
        
        # 請求元を企業特定キーとして活用
        if data.get("issuer"):
            fallback_keys["請求元企業"] = data["issuer"]
        
        # 請求先を顧客特定キーとして活用
        if data.get("payer"):
            fallback_keys["請求先企業"] = data["payer"]
        
        # 【高優先】重複判定用キー
        # 請求書番号系（重複判定の主要キー）
        if data.get("main_invoice_number"):
            fallback_keys["請求書番号"] = data["main_invoice_number"]
        elif data.get("receipt_number"):
            fallback_keys["領収書番号"] = data["receipt_number"]
        
        # 期間情報（重複判定の補助キー）
        if data.get("issue_date") and data.get("due_date"):
            fallback_keys["請求期間"] = f"{data['issue_date']}～{data['due_date']}"
        elif data.get("issue_date"):
            fallback_keys["発行日"] = data["issue_date"]
        
        # 金額情報（重複判定の検証用）
        if data.get("amount_inclusive_tax"):
            fallback_keys["請求金額"] = str(data["amount_inclusive_tax"])
        
        # 【中優先】ファイル管理・分類用キー
        # 通貨情報（分類用）
        if data.get("currency"):
            fallback_keys["通貨"] = data["currency"]
        
        return fallback_keys
    
    def _standardize_key_names(self, key_info: Dict[str, Any]) -> Dict[str, str]:
        """キー名の標準化"""
        if not isinstance(key_info, dict):
            return {}
        
        standardized = {}
        
        # 標準化マッピング（優先度順）
        key_mapping = {
            # 【最優先】企業・アカウント特定用キー
            "account_id": "アカウントID",
            "customer_number": "顧客番号", 
            "customer_code": "顧客コード",
            "contract_number": "契約番号",
            "billing_code": "請求先コード",
            "branch_code": "支店コード",
            "department_code": "部門コード",
            "company_id": "企業ID",
            "tenant_id": "テナントID",
            "organization_id": "組織ID",
            
            # 【高優先】重複判定用キー
            "period": "利用期間",
            "usage_period": "利用期間",
            "billing_period": "請求対象期間",
            "reference_number": "参照番号",
            "transaction_id": "取引ID",
            "order_number": "注文番号",
            
            # 【中優先】ファイル管理・分類用キー
            "service_name": "サービス名",
            "plan_name": "プラン名",
            "billing_type": "請求種別",
            "payment_type": "支払種別",
            "invoice_type": "請求書種別",
            "department": "請求先部署",
            "branch_name": "支店名",
            
            # 【補助】その他識別子
            "contact_person": "担当者",
            "auxiliary_number": "補助番号",
            "sub_number": "補助番号",
            "memo": "備考",
            "notes": "備考"
        }
        
        for key, value in key_info.items():
            if value is not None and value != "":
                # 英語キーを日本語に変換
                japanese_key = key_mapping.get(key, key)
                standardized[japanese_key] = str(value)
        
        return standardized
    
    def test_prompts(self) -> Dict[str, Any]:
        """プロンプト機能のテスト"""
        test_results = {
            "invoice_extractor": False,
            "master_matcher": False,
            "integrated_matcher": False,
            "prompt_loading": False,
            "errors": []
        }
        
        try:
            # プロンプト読み込みテスト
            prompts = ["invoice_extractor_prompt", "master_matcher_prompt", "integrated_matcher_prompt"]
            
            for prompt_name in prompts:
                try:
                    prompt_info = self.prompt_manager.get_prompt_info(prompt_name)
                    logger.info(f"プロンプト読み込み成功: {prompt_name} v{prompt_info['version']}")
                    test_results[prompt_name.replace("_prompt", "")] = True
                except Exception as e:
                    error_msg = f"{prompt_name}読み込み失敗: {e}"
                    test_results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            test_results["prompt_loading"] = len(test_results["errors"]) == 0
            
            logger.info(f"プロンプトテスト完了: {test_results}")
            return test_results
            
        except Exception as e:
            error_msg = f"プロンプトテスト全体エラー: {e}"
            test_results["errors"].append(error_msg)
            logger.error(error_msg)
            return test_results

    # テスト用シミュレーションメソッド
    def simulate_company_matching(self, issuer_name: str, master_company_list: List[str]) -> Dict[str, Any]:
        """企業名照合のシミュレーション（テスト用）"""
        # 簡単な文字列マッチングロジック
        best_match = None
        best_score = 0
        
        for company in master_company_list:
            # 簡単な類似度計算
            if issuer_name in company or company in issuer_name:
                score = 95
            elif issuer_name.replace("株式会社", "").replace("合同会社", "") in company.replace("株式会社", "").replace("合同会社", ""):
                score = 90
            elif "Google" in issuer_name and "Google" in company:
                score = 95
            elif "Microsoft" in issuer_name and "Microsoft" in company:
                score = 90
            elif "MS" in issuer_name and "Microsoft" in company:
                score = 85
            else:
                score = 30
                
            if score > best_score and score >= 85:  # 85%以上の閾値
                best_match = company
                best_score = score
        
        return {
            "matched_company": best_match,
            "confidence": best_score,
            "method": "simulation"
        }

    def simulate_integrated_matching(self, invoice_data: Dict[str, Any], master_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """統合照合のシミュレーション（テスト用）"""
        best_entry = None
        best_score = 0
        best_reason = ""
        key_matches = []
        
        for record in master_records:
            score = 0
            reasons = []
            
            # 企業名照合
            if invoice_data.get("issuer") == record.get("company_name"):
                score += 40
                reasons.append("企業名完全一致")
                
            # 金額照合
            if invoice_data.get("amount_inclusive_tax") == record.get("amount"):
                score += 30
                reasons.append("金額一致")
            
            # キー情報照合
            invoice_key_info = invoice_data.get("key_info", {})
            additional_condition = record.get("additional_condition", "")
            
            for key, value in invoice_key_info.items():
                if str(value) in additional_condition:
                    score += 15
                    reasons.append(f"キー情報一致({key})")
                    key_matches.append(key)
            
            if score > best_score and score >= 75:  # 75%以上の閾値
                best_entry = record["id"]
                best_score = score
                best_reason = ", ".join(reasons)
        
        return {
            "matched_entry_id": best_entry,
            "confidence": best_score,
            "matching_reason": best_reason,
            "key_info_matches": key_matches,
            "method": "simulation"
        }

    def extract_priority_keys(self, invoice_data: Dict[str, Any], priority_level: str) -> Dict[str, str]:
        """優先度別キー情報の抽出（テスト用）"""
        key_info = invoice_data.get("key_info", {})
        extracted_keys = {}
        
        # 優先度別のキー定義
        priority_mappings = {
            "highest": ["アカウントID", "顧客番号", "契約番号", "登録番号", "企業コード"],
            "high": ["請求書番号", "利用期間", "サービス期間", "課金期間", "subscription_id"],
            "medium": ["支払期限", "税率", "請求日", "発行日", "due_date"],
            "low": ["部署コード", "プロジェクトコード", "コストセンター", "参照番号"]
        }
        
        target_keys = priority_mappings.get(priority_level, [])
        
        for key, value in key_info.items():
            if key in target_keys:
                extracted_keys[key] = str(value)
        
        return extracted_keys

    def standardize_key_name(self, key_name: str) -> str:
        """キー名の標準化（テスト用）"""
        # 基本的なキー名標準化ロジック
        standardization_map = {
            "account_id": "アカウントID",
            "customer_number": "顧客番号",
            "customernumber": "顧客番号",
            "contract_number": "契約番号",
            "invoice_number": "請求書番号",
            "billing_period": "利用期間",
            "payment_due": "支払期限",
            "tax_rate": "税率",
            "department_code": "部署コード",
            "project_code": "プロジェクトコード",
            "請求書id": "請求書番号",
            "請求書ID": "請求書番号"
        }
        
        # 小文字化して標準化マップで確認
        normalized_key = key_name.lower().replace("_", "").replace("-", "")
        
        # 直接マッピング
        if key_name in standardization_map:
            return standardization_map[key_name]
        
        # 正規化後マッピング
        for standard_key, japanese_key in standardization_map.items():
            if normalized_key == standard_key.lower().replace("_", ""):
                return japanese_key
        
        # マッピングがない場合はそのまま返す
        return key_name


# グローバルインスタンス
_global_matcher_service = None

def get_invoice_matcher() -> InvoiceMatcherService:
    """
    グローバルな請求書照合サービスインスタンスを取得
    
    Returns:
        InvoiceMatcherServiceインスタンス
    """
    global _global_matcher_service
    
    if _global_matcher_service is None:
        _global_matcher_service = InvoiceMatcherService()
    
    return _global_matcher_service

def match_company_simple(issuer_name: str, master_list: List[str]) -> Optional[str]:
    """
    シンプルな企業名照合関数
    
    Args:
        issuer_name: 請求元名
        master_list: マスタ企業名リスト
        
    Returns:
        マッチした企業名またはNone
    """
    matcher = get_invoice_matcher()
    result = matcher.match_company_name(issuer_name, master_list)
    
    if result and result.get("matched_company_name"):
        return result["matched_company_name"]
    
    return None

def match_invoice_simple(invoice_data: Dict[str, Any], 
                        master_records: List[Dict[str, Any]]) -> Optional[str]:
    """
    シンプルな統合照合関数
    
    Args:
        invoice_data: 請求書データ
        master_records: マスタレコードリスト
        
    Returns:
        マッチしたエントリIDまたはNone
    """
    matcher = get_invoice_matcher()
    result = matcher.match_integrated_invoice(invoice_data, master_records)
    
    if result and result.get("matched_entry_id"):
        return result["matched_entry_id"]
    
    return None 