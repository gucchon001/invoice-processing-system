"""
請求書処理自動化システム - Gemini APIヘルパー

このモジュールはGoogle Gemini APIとの連携、PDF処理、
情報抽出機能を提供します。
"""

import streamlit as st
import google.generativeai as genai
import base64
import logging
from typing import Dict, Any, Optional, List
import json
import io
import time
from pathlib import Path

# 設定ヘルパーをインポート
from utils.config_helper import (
    get_gemini_model, get_gemini_max_retries, get_gemini_retry_delay,
    get_gemini_temperature, get_gemini_max_tokens, get_gemini_timeout,
    is_ai_debug
)

# ロガー設定
logger = logging.getLogger(__name__)


class GeminiAPIManager:
    """Gemini API管理クラス（JSONプロンプト対応版）"""
    
    def __init__(self):
        """Gemini API接続を初期化"""
        try:
            self.api_key = st.secrets["ai"]["gemini_api_key"]
            genai.configure(api_key=self.api_key)
            
            # モデル設定（settings.iniから取得）
            self.model_name = get_gemini_model()
            self.temperature = get_gemini_temperature()
            self.max_tokens = get_gemini_max_tokens()
            self.timeout = get_gemini_timeout()
            self.max_retries = get_gemini_max_retries()
            self.retry_delay = get_gemini_retry_delay()
            
            # モデル初期化
            self.model = genai.GenerativeModel(self.model_name)
            
            logger.info(f"Gemini API接続初期化完了: モデル={self.model_name}, 温度={self.temperature}")
            
            if is_ai_debug():
                logger.info(f"AI設定詳細: max_tokens={self.max_tokens}, timeout={self.timeout}s, retries={self.max_retries}")
                
        except KeyError as e:
            logger.error(f"Gemini API設定が不完全です: {e}")
            st.error(f"Gemini API設定エラー: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini API接続でエラー: {e}")
            st.error(f"Gemini API接続エラー: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Gemini API接続をテストする"""
        try:
            # シンプルなテキスト生成でテスト
            response = self.model.generate_content("Hello! Please respond with 'Connection successful'")
            
            if response and response.text:
                logger.info("Gemini API接続テスト成功")
                return True
            else:
                logger.error("Gemini APIから応答がありません")
                return False
                
        except Exception as e:
            logger.error(f"Gemini API接続テストでエラー: {e}")
            return False
    
    def generate_text(self, prompt: str) -> Optional[str]:
        """テキスト生成"""
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text
            return None
        except Exception as e:
            logger.error(f"テキスト生成でエラー: {e}")
            return None
    
    def _validate_pdf_content(self, pdf_content: bytes) -> bool:
        """PDF内容を検証"""
        try:
            # 基本的なPDFサイズ・ヘッダーチェック
            if not pdf_content or len(pdf_content) < 10:
                logger.warning("PDFデータが空または短すぎます")
                return False
            
            # PDFヘッダー確認
            if not pdf_content.startswith(b'%PDF'):
                logger.warning("有効なPDFヘッダーが見つかりません")
                return False
            
            # サイズチェック（10MB以上は拒否）
            if len(pdf_content) > 10 * 1024 * 1024:
                logger.warning(f"PDFサイズが大きすぎます: {len(pdf_content)} bytes")
                return False
            
            logger.debug(f"PDF検証成功: サイズ={len(pdf_content)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"PDF検証エラー: {e}")
            return False

    def analyze_pdf_content(self, pdf_content: bytes, prompt: str, max_retries: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """PDFコンテンツを分析（リトライ機能付き・検証強化版）"""
        # 🚨 緊急デバッグ（7/22）: 詳細ログ出力
        logger.error(f"🔍 DEBUG: analyze_pdf_content開始 - PDFサイズ: {len(pdf_content)} bytes")
        logger.error(f"🔍 DEBUG: プロンプト長: {len(prompt)} 文字")
        
        # 🚨 緊急修正（7/22）: PDF検証を追加
        if not self._validate_pdf_content(pdf_content):
            logger.error("PDF検証に失敗しました - 処理を中止します")
            return None
        
        logger.error(f"🔍 DEBUG: PDF検証成功、API呼び出し開始")
        
        # settings.iniから設定値を取得
        if max_retries is None:
            max_retries = self.max_retries
            
        for attempt in range(max_retries):
            try:
                # PDFをBase64エンコード
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                
                # マルチモーダルコンテンツを作成
                contents = [
                    prompt,
                    {
                        "mime_type": "application/pdf",
                        "data": pdf_base64
                    }
                ]
                
                # 生成設定（settings.iniから取得）
                generation_config = {
                    "response_mime_type": "application/json",
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens
                }
                
                # Gemini APIで分析
                response = self.model.generate_content(
                    contents,
                    generation_config=generation_config
                )
                
                if response and response.text:
                    # JSON形式でレスポンスをパース
                    try:
                        result = json.loads(response.text)
                        logger.info("PDF分析成功")
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析エラー: {e}")
                        # JSONでない場合はテキストとして返す
                        return {"raw_text": response.text}
                
                return None
                
            except Exception as e:
                error_str = str(e)
                
                # 🚨 "no pages" エラーの特別処理（リトライしても解決しない）
                if "no pages" in error_str.lower():
                    logger.error(f"⚠️ PDF解析致命的エラー: PDFにページが認識されません - {e}")
                    logger.error("📋 推定原因: PDF破損、空ファイル、またはフォーマット非対応")
                    # このエラーはリトライしても解決しないため即座に終了
                    return None
                elif "400" in error_str and ("bad request" in error_str.lower() or "document" in error_str.lower()):
                    logger.error(f"⚠️ PDF形式エラー: Gemini APIがPDFを処理できません - {e}")
                    return None
                elif "429" in error_str or "quota" in error_str.lower():
                    # レート制限エラーの場合（settings.iniから遅延時間を取得）
                    retry_delay = self.retry_delay if attempt == 0 else self.retry_delay * (attempt + 1)
                    logger.warning(f"Gemini API制限に達しました。{retry_delay}秒後にリトライします (試行 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"最大リトライ回数に達しました: {e}")
                        return None
                else:
                    logger.error(f"PDF分析でエラー: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return None
        
        return None
    
    def extract_invoice_data(self, pdf_content: bytes) -> Optional[Dict[str, Any]]:
        """請求書データ抽出（JSONプロンプト使用）"""
        # 🚨 緊急デバッグ（7/22）: extract_invoice_data開始ログ
        logger.error(f"🔍 DEBUG: extract_invoice_data開始 - PDFサイズ: {len(pdf_content)} bytes")
        
        try:
            # プロンプトマネージャーを使用してJSON外出しプロンプト読み込み
            logger.error("🔍 DEBUG: プロンプトマネージャー呼び出し中...")
            from core.services.unified_prompt_manager import UnifiedPromptManager
            
            prompt_manager = UnifiedPromptManager()
            
            # 請求書抽出プロンプトの生成（統一フォーマット・修正版）
            system_prompt, user_prompt = prompt_manager.format_prompt_for_gemini(
                "invoice_extractor_prompt",
                {
                    "invoice_image": f"PDFファイル（{len(pdf_content)} bytes）",
                    "extraction_mode": "comprehensive"
                }
            )
            # 統一プロンプトを結合
            invoice_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            logger.info("JSONプロンプトを使用して請求書データ抽出を実行")
            return self.analyze_pdf_content(pdf_content, invoice_prompt)
            
        except Exception as e:
            logger.error(f"JSONプロンプト読み込みエラー: {e}")
            # フォールバック: 旧形式プロンプトを使用
            logger.warning("フォールバック: レガシープロンプトを使用")
            return self._extract_invoice_data_legacy(pdf_content)
    
    def _extract_invoice_data_legacy(self, pdf_content: bytes) -> Optional[Dict[str, Any]]:
        """請求書データ抽出（レガシープロンプト・フォールバック用）"""
        
        # レガシー請求書情報抽出用プロンプト（フォールバック用）
        invoice_prompt = """
あなたは高精度なOCRと自然言語処理能力を持つAIアシスタントです。
アップロードされた請求書PDFから以下の情報を抽出してください。

抽出する情報：
1. 請求元（issuer）: 請求書を発行した会社名
2. 請求先（payer）: 請求書の宛先
3. 請求書番号（invoice_number）: 請求書の識別番号
4. 発行日（issue_date）: 請求書の発行日（YYYY-MM-DD形式）
5. 支払期日（due_date）: 支払期限（YYYY-MM-DD形式）
6. 通貨（currency）: 通貨コード（例：JPY, USD）
7. 税込金額（amount_inclusive_tax）: 税込みの合計金額（数値のみ）
8. 税抜金額（amount_exclusive_tax）: 税抜きの合計金額（数値のみ）
9. キー情報（key_info）: アカウントID、お客様番号、期間など特徴的な情報
10. 明細（line_items）: 商品・サービスの詳細

以下のJSON形式で回答してください：
{
    "issuer": "string",
    "payer": "string", 
    "invoice_number": "string",
    "issue_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "currency": "string",
    "amount_inclusive_tax": number,
    "amount_exclusive_tax": number,
    "key_info": {
        "account_id": "string",
        "customer_number": "string",
        "period": "string"
    },
    "line_items": [
        {
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "amount": number
        }
    ]
}

情報が見つからない場合はnullを設定してください。
"""
        
        return self.analyze_pdf_content(pdf_content, invoice_prompt)
    
    def extract_pdf_invoice_data(self, pdf_content: bytes) -> Optional[Dict[str, Any]]:
        """
        請求書PDFデータ抽出（統合メソッド）
        強化版抽出機能も提供
        """
        # 🚨 緊急デバッグ（7/22）: extract_pdf_invoice_data開始ログ
        logger.error(f"🔍 DEBUG: extract_pdf_invoice_data開始 - PDFサイズ: {len(pdf_content)} bytes")
        
        try:
            # 🚨 緊急修正（7/22）: 強化版抽出を一時的に無効化して安定性を確保
            logger.error("🔍 DEBUG: 基本版請求書抽出を実行（強化版は一時無効化）")
            return self.extract_invoice_data(pdf_content)
            
            # 強化版は後日再有効化予定
            # from infrastructure.ai.invoice_matcher import get_invoice_matcher
            # matcher_service = get_invoice_matcher()
            # result = matcher_service.enhanced_invoice_extraction(pdf_content)
                
        except Exception as e:
            logger.error(f"統合抽出エラー: {e}")
            # 基本版にフォールバック
            return self.extract_invoice_data(pdf_content)
    
    def match_company_name(self, issuer_name: str, master_company_list: List[str]) -> Optional[Dict[str, Any]]:
        """
        企業名照合（JSONプロンプト版）
        
        Args:
            issuer_name: 請求書の請求元名
            master_company_list: 支払マスタの企業名リスト
            
        Returns:
            照合結果辞書またはNone
        """
        try:
            from infrastructure.ai.invoice_matcher import get_invoice_matcher
            
            matcher_service = get_invoice_matcher()
            return matcher_service.match_company_name(issuer_name, master_company_list)
            
        except Exception as e:
            logger.error(f"企業名照合エラー: {e}")
            return None
    
    def match_integrated_invoice(self, invoice_data: Dict[str, Any], 
                               master_records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        統合照合（JSONプロンプト版）
        
        Args:
            invoice_data: 請求書から抽出された詳細情報
            master_records: 支払マスタから絞り込まれた候補レコードのリスト
            
        Returns:
            照合結果辞書またはNone
        """
        try:
            from infrastructure.ai.invoice_matcher import get_invoice_matcher
            
            matcher_service = get_invoice_matcher()
            return matcher_service.match_integrated_invoice(invoice_data, master_records)
            
        except Exception as e:
            logger.error(f"統合照合エラー: {e}")
            return None
    
    def test_json_prompts(self) -> Dict[str, Any]:
        """JSONプロンプト機能の包括テスト"""
        try:
            from infrastructure.ai.invoice_matcher import get_invoice_matcher
            
            matcher_service = get_invoice_matcher()
            return matcher_service.test_prompts()
            
        except Exception as e:
            logger.error(f"JSONプロンプトテストエラー: {e}")
            return {
                "invoice_extractor": False,
                "master_matcher": False,
                "integrated_matcher": False,
                "prompt_loading": False,
                "errors": [f"テスト実行エラー: {e}"]
            }


# シングルトンパターンでインスタンスを作成
_gemini_manager = None

def get_gemini_api() -> GeminiAPIManager:
    """GeminiAPIManagerのシングルトンインスタンスを取得"""
    global _gemini_manager
    if _gemini_manager is None:
        _gemini_manager = GeminiAPIManager()
    return _gemini_manager


# 便利関数
def test_gemini_connection() -> bool:
    """Gemini API接続をテストする便利関数"""
    try:
        return get_gemini_api().test_connection()
    except Exception:
        return False

def generate_text_simple(prompt: str) -> Optional[str]:
    """シンプルなテキスト生成"""
    try:
        return get_gemini_api().generate_text(prompt)
    except Exception:
        return None

def extract_pdf_invoice_data(pdf_content: bytes) -> Optional[Dict[str, Any]]:
    """PDFから請求書データを抽出する便利関数"""
    try:
        return get_gemini_api().extract_invoice_data(pdf_content)
    except Exception:
        return None 