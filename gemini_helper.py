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
from pathlib import Path

# ロガー設定
logger = logging.getLogger(__name__)


class GeminiAPIManager:
    """Gemini API管理クラス"""
    
    def __init__(self):
        """Gemini API接続を初期化"""
        try:
            self.api_key = st.secrets["ai"]["gemini_api_key"]
            genai.configure(api_key=self.api_key)
            
            # モデル設定
            self.model_name = "gemini-1.5-flash"
            self.model = genai.GenerativeModel(self.model_name)
            
            logger.info("Gemini API接続初期化完了")
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
    
    def analyze_pdf_content(self, pdf_content: bytes, prompt: str) -> Optional[Dict[str, Any]]:
        """PDFコンテンツを分析"""
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
            
            # 生成設定
            generation_config = {
                "response_mime_type": "application/json"
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
            logger.error(f"PDF分析でエラー: {e}")
            return None
    
    def extract_invoice_data(self, pdf_content: bytes) -> Optional[Dict[str, Any]]:
        """請求書データ抽出（専用プロンプト使用）"""
        
        # 請求書情報抽出用プロンプト
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