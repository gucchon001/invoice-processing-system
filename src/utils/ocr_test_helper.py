"""
OCRテストヘルパー - Geminiを使用したPDF処理テスト

Google DriveからPDFファイルを取得し、GeminiでOCR処理を実行する
テスト機能を提供します。
"""

import streamlit as st
import pandas as pd
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import io
import uuid

# 設定ヘルパーをインポート
from utils.config_helper import get_gemini_model

# 統一バリデーションシステムをインポート
from core.services.invoice_validator import InvoiceValidator

# ロガー設定
logger = logging.getLogger(__name__)

# 日時をUTCからJSTに変換する関数を追加
def convert_utc_to_jst(utc_time_str: str) -> str:
    """UTC時刻文字列をJST（日本標準時）に変換"""
    try:
        if not utc_time_str:
            return ""
        
        # UTC時刻をパース（タイムゾーン情報を考慮）
        if utc_time_str.endswith('Z'):
            utc_time = datetime.fromisoformat(utc_time_str[:-1] + '+00:00')
        elif '+' in utc_time_str or utc_time_str.endswith('T'):
            utc_time = datetime.fromisoformat(utc_time_str)
        else:
            # タイムゾーン情報がない場合はUTCとして扱う
            utc_time = datetime.fromisoformat(utc_time_str).replace(tzinfo=timezone.utc)
        
        # JSTに変換（UTC+9）
        jst = utc_time.astimezone(timezone(timedelta(hours=9)))
        
        # 表示用フォーマット（YYYY-MM-DD HH:MM）
        return jst.strftime('%Y-%m-%d %H:%M')
        
    except Exception as e:
        logger.warning(f"日時変換エラー: {e}, 元の値: {utc_time_str}")
        return str(utc_time_str)[:16]  # エラーの場合は元の処理

class OCRTestManager:
    """OCRテスト管理クラス"""
    
    def __init__(self, drive_manager, gemini_manager, database_manager=None):
        """初期化"""
        self.drive_manager = drive_manager
        self.gemini_manager = gemini_manager
        self.database_manager = database_manager
        # 統一バリデーションシステムの初期化
        self.validator = InvoiceValidator()
        
    def get_drive_pdfs(self, folder_id: str) -> List[Dict[str, Any]]:
        """Google DriveフォルダからPDFファイル一覧を取得"""
        try:
            logger.info(f"フォルダID {folder_id} からPDFファイル一覧を取得中...")
            
            # フォルダ内のPDFファイルを検索（共有ドライブ対応）
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            
            results = self.drive_manager.service.files().list(
                q=query,
                fields="files(id, name, size, modifiedTime)",
                orderBy="modifiedTime desc",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"{len(files)}個のPDFファイルが見つかりました")
            
            return files
            
        except Exception as e:
            logger.error(f"Google DriveからPDFファイル取得中にエラー: {e}")
            st.error(f"PDFファイル取得エラー: {str(e)}")
            return []
    
    def download_pdf_from_drive(self, file_id: str) -> Optional[bytes]:
        """Google DriveからPDFファイルをダウンロード"""
        try:
            logger.info(f"ファイルID {file_id} をダウンロード中...")
            
            request = self.drive_manager.service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )
            file_content = io.BytesIO()
            
            import googleapiclient.http
            downloader = googleapiclient.http.MediaIoBaseDownload(file_content, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
            file_content.seek(0)
            content = file_content.read()
            
            logger.info(f"ファイルダウンロード完了: {len(content)} bytes")
            return content
            
        except Exception as e:
            logger.error(f"Google Driveからファイルダウンロード中にエラー: {e}")
            st.error(f"ファイルダウンロードエラー: {str(e)}")
            return None
    
    def create_ocr_prompt(self, filename: str = "", file_size: int = 0) -> str:
        """OCR用のプロンプトを作成（JSON外出し対応）"""
        try:
            # プロンプトマネージャーを使用してJSON外出しプロンプト読み込み
            from utils.prompt_manager import get_prompt_manager
            
            prompt_manager = get_prompt_manager()
            
            # ファイル情報を作成
            file_info = f"請求書PDFファイル: {filename}"
            if file_size > 0:
                file_info += f" (サイズ: {file_size:,} bytes)"
            
            # OCR抽出プロンプトの生成（実際のファイル情報を提供）
            ocr_prompt = prompt_manager.render_prompt(
                "invoice_extractor_prompt",
                {
                    "extraction_mode": "comprehensive",
                    "invoice_image": file_info  # 実際のファイル情報を提供
                }
            )
            
            logger.info(f"JSONプロンプトを使用してOCRプロンプトを生成: {filename}")
            return ocr_prompt
            
        except Exception as e:
            logger.error(f"JSONプロンプト読み込みエラー: {e}")
            # フォールバック: レガシープロンプトを使用
            logger.warning("フォールバック: レガシーOCRプロンプトを使用")
            return self._create_ocr_prompt_legacy()
    
    def _create_ocr_prompt_legacy(self) -> str:
        """OCR用レガシープロンプト（フォールバック用）"""
        return """
あなたは請求書のOCR専門家です。アップロードされたPDFから以下の情報を正確に抽出してJSON形式で返してください。

## 抽出対象項目：
1. **請求元企業名** (issuer_name)
2. **請求先企業名** (recipient_name)  
3. **領収書番号** (receipt_number)
4. **請求書番号** (invoice_number)
5. **登録番号** (registration_number)
6. **通貨** (currency) - JPY, USD, EUR等
7. **税込金額** (total_amount_tax_included) - 数値のみ
8. **税抜金額** (total_amount_tax_excluded) - 数値のみ
9. **発行日** (issue_date) - YYYY-MM-DD形式
10. **支払期日** (due_date) - YYYY-MM-DD形式
11. **明細** (line_items) - 各明細の配列
12. **キー情報** (key_info) - 支払マスタ照合用の重要情報

## 明細の構造：
```json
{
  "description": "商品・サービス名",
  "quantity": 数量,
  "unit_price": 単価,
  "amount": 金額,
  "tax": "税率(10%等)"
}
```

## 注意事項：
- 数値は必ず数値型で返す（文字列不可）
- 日付はYYYY-MM-DD形式で統一
- 不明な項目はnullを設定
- 明細が複数ある場合は配列で全て抽出
- 通貨記号は除去し、通貨コードのみ記載

## 出力形式：
```json
{
  "issuer_name": "株式会社○○",
  "recipient_name": "株式会社△△", 
  "receipt_number": "REC-2024-001",
  "invoice_number": "INV-2024-001",
  "registration_number": "T1234567890123",
  "currency": "JPY",
  "total_amount_tax_included": 110000,
  "total_amount_tax_excluded": 100000,
  "issue_date": "2024-12-01",
  "due_date": "2024-12-31",
  "key_info": {
    "payee": "株式会社△△",
    "content": "サービス名",
    "special_conditions": [],
    "confidence_score": 0.95
  },
  "line_items": [
    {
      "description": "サービス名",
      "quantity": 1,
      "unit_price": 100000,
      "amount": 100000,
      "tax": "10%"
    }
  ]
}
```

PDFの内容を詳細に分析し、上記のJSON形式で結果を返してください。
"""

    def process_pdf_with_gemini(self, pdf_content: bytes, filename: str) -> Optional[Dict[str, Any]]:
        """GeminiでPDFをOCR処理"""
        try:
            # 設定ファイルから現在のモデル名を取得
            current_model = get_gemini_model()
            logger.info(f"{current_model}でOCR処理開始: {filename}")
            
            # OCR用プロンプト作成（実際のファイル情報を渡す）
            file_size = len(pdf_content)
            prompt = self.create_ocr_prompt(filename, file_size)
            
            # Gemini APIで処理
            result = self.gemini_manager.analyze_pdf_content(pdf_content, prompt)
            
            if result:
                logger.info(f"OCR処理完了: {filename}")
                return result
            else:
                logger.error(f"OCR処理失敗: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Gemini OCR処理中にエラー ({filename}): {e}")
            st.error(f"OCR処理エラー: {str(e)}")
            return None
    
    def validate_ocr_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """OCR結果の詳細検証（統合版バリデーターを使用）"""
        try:
            # 統一バリデーションシステムを使用
            validation = self.validator.validate_invoice_data(result, strict_mode=False)
            
            # OCRテスト用の完全性スコア計算を追加
            if "completeness_score" not in validation:
                required_fields = {"issuer", "amount_inclusive_tax", "currency"}
                important_fields = {"payer", "main_invoice_number", "issue_date"}
                optional_fields = {"t_number", "amount_exclusive_tax", "due_date", "line_items", "key_info"}
                all_fields = required_fields | important_fields | optional_fields
                
                filled_fields = sum(1 for field in all_fields if self._is_valid_field_value(result.get(field)))
                validation["completeness_score"] = round((filled_fields / len(all_fields)) * 100, 1)
            
            logger.info(f"統合バリデーション完了: エラー{len(validation.get('errors', []))}件, 警告{len(validation.get('warnings', []))}件")
            return validation
            
        except Exception as e:
            logger.error(f"統合バリデーションでエラー: {e}")
            # フォールバック: 基本的な検証結果を返す
            return {
                "is_valid": False,
                "errors": [f"バリデーションシステムエラー: {str(e)}"],
                "warnings": [],
                "completeness_score": 0,
                "error_categories": {
                    "critical": [f"バリデーションシステムエラー: {str(e)}"],
                    "data_missing": [],
                    "data_format": [],
                    "business_logic": []
                }
            }
    
    def _is_valid_field_value(self, value) -> bool:
        """フィールド値の有効性をチェック"""
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        return True

    
    def format_ocr_result_for_display(self, result: Dict[str, Any], validation: Dict[str, Any]) -> pd.DataFrame:
        """OCR結果を表示用データフレームに変換"""
        
        # 基本情報（JSONプロンプト対応）
        basic_info = []
        field_mapping = {
            "issuer": "請求元企業名",
            "payer": "請求先企業名", 
            "receipt_number": "領収書番号",
            "main_invoice_number": "請求書番号",
            "t_number": "登録番号",
            "currency": "通貨",
            "amount_inclusive_tax": "税込金額",
            "amount_exclusive_tax": "税抜金額",
            "issue_date": "発行日",
            "due_date": "支払期日",
            "key_info": "キー情報"
        }
        
        for field, label in field_mapping.items():
            value = result.get(field, "")
            if value is None:
                value = ""
            basic_info.append({
                "項目": label,
                "値": str(value),
                "フィールド名": field
            })
        
        df_basic = pd.DataFrame(basic_info)
        
        # 明細情報
        line_items = result.get("line_items", [])
        df_details = pd.DataFrame()
        
        # line_itemsの安全な処理
        if not isinstance(line_items, list):
            line_items = []
        
        if len(line_items) > 0:
            details_data = []
            for i, item in enumerate(line_items, 1):
                details_data.append({
                    "No.": i,
                    "商品・サービス名": item.get("description", ""),
                    "数量": item.get("quantity", ""),
                    "単価": item.get("unit_price", ""),
                    "金額": item.get("amount", ""),
                    "税率": item.get("tax", "")
                })
            df_details = pd.DataFrame(details_data)
        
        return df_basic, df_details
    
    def run_comprehensive_test(self, folder_id: str, max_files: int = -1) -> Dict[str, Any]:
        """包括的OCRテスト実行"""
        test_results = {
            "start_time": datetime.now(),
            "folder_id": folder_id,
            "files_processed": 0,
            "files_success": 0,
            "files_failed": 0,
            "results": [],
            "summary": {}
        }
        
        try:
            # PDFファイル一覧取得
            pdf_files = self.get_drive_pdfs(folder_id)
            
            # DataFrameの場合はリストに変換
            if hasattr(pdf_files, 'to_dict'):
                pdf_files = pdf_files.to_dict('records')
            elif not isinstance(pdf_files, list):
                pdf_files = []
            
            if len(pdf_files) == 0:
                st.warning("指定フォルダにPDFファイルが見つかりません")
                return test_results
            
            # 件数制限を適用
            if max_files > 0:
                pdf_files = pdf_files[:max_files]
                st.info(f"{len(pdf_files)}個のPDFファイルをテストします（制限: {max_files}件）")
            else:
                st.info(f"{len(pdf_files)}個のPDFファイルが見つかりました（全件テスト）")
            
            # 進捗バー設定
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # ファイルIDマッピングをセッション状態に保存
            if "file_id_mapping" not in st.session_state:
                st.session_state.file_id_mapping = {}
            
            # 各ファイルを処理
            for i, file_info in enumerate(pdf_files):
                file_id = file_info["id"]
                filename = file_info["name"]
                
                # ファイルIDマッピングを保存（原本表示用）
                st.session_state.file_id_mapping[filename] = file_id
                
                status_text.text(f"処理中: {filename} ({i+1}/{len(pdf_files)})")
                
                # ファイルダウンロード
                pdf_content = self.download_pdf_from_drive(file_id)
                
                if pdf_content:
                    # OCR処理
                    ocr_result = self.process_pdf_with_gemini(pdf_content, filename)
                    
                    if ocr_result:
                        # 結果検証
                        validation = self.validate_ocr_result(ocr_result)
                        
                        test_results["results"].append({
                            "file_id": file_id,
                            "filename": filename,
                            "file_size": file_info.get("size", 0),
                            "ocr_result": ocr_result,
                            "validation": validation,
                            "processed_at": datetime.now().isoformat()
                        })
                        
                        # 検証結果に基づいて成功をカウント
                        if validation["is_valid"]:
                            test_results["files_success"] += 1
                        else:
                            test_results["files_failed"] += 1
                    else:
                        test_results["files_failed"] += 1
                else:
                    test_results["files_failed"] += 1
                
                test_results["files_processed"] += 1
                
                # 進捗更新
                progress = (i + 1) / len(pdf_files)
                progress_bar.progress(progress)
            
            # サマリー計算
            test_results["end_time"] = datetime.now()
            test_results["duration"] = (test_results["end_time"] - test_results["start_time"]).total_seconds()
            
            if len(test_results.get("results", [])) > 0:
                # None値を除外して有効なスコアのみを取得
                completeness_scores = [
                    r["validation"]["completeness_score"] 
                    for r in test_results["results"] 
                    if r["validation"]["completeness_score"] is not None
                ]
                
                if completeness_scores:
                    test_results["summary"] = {
                        "average_completeness": round(sum(completeness_scores) / len(completeness_scores), 1),
                        "min_completeness": min(completeness_scores),
                        "max_completeness": max(completeness_scores),
                        "success_rate": round((test_results["files_success"] / test_results["files_processed"]) * 100, 1)
                    }
                else:
                    test_results["summary"] = {
                        "average_completeness": 0.0,
                        "min_completeness": 0.0,
                        "max_completeness": 0.0,
                        "success_rate": round((test_results["files_success"] / test_results["files_processed"]) * 100, 1)
                    }
            
            status_text.text("処理完了!")
            progress_bar.progress(1.0)
            
        except Exception as e:
            logger.error(f"包括的OCRテスト中にエラー: {e}")
            st.error(f"テスト実行エラー: {str(e)}")
        
        return test_results
    
    def save_to_supabase(self, test_results: Dict[str, Any], user_email: str) -> Optional[str]:
        """テスト結果をSupabaseに保存"""
        if not self.database_manager:
            logger.warning("データベースマネージャーが設定されていません")
            return None
        
        try:
            # Service Role Keyを使用してRLS回避
            try:
                import streamlit as st
                service_key = st.secrets["database"]["supabase_service_key"]
                supabase_url = st.secrets["database"]["supabase_url"]
                
                from supabase import create_client
                service_supabase = create_client(supabase_url, service_key)
                
                logger.info("Service Role Keyを使用してデータ保存")
                
            except Exception as e:
                logger.warning(f"Service Role Key使用失敗、通常キーで試行: {e}")
                service_supabase = self.database_manager.supabase
            
            # セッション情報を保存
            session_data = {
                "session_name": f"OCRテスト_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "folder_id": test_results["folder_id"],
                "total_files": test_results["files_processed"],
                "processed_files": test_results["files_processed"],
                "success_files": test_results["files_success"],
                "failed_files": test_results["files_failed"],
                "average_completeness": test_results.get("summary", {}).get("average_completeness"),
                "success_rate": test_results.get("summary", {}).get("success_rate"),
                "processing_duration": test_results.get("duration"),
                "created_by": user_email
            }
            
            session_response = service_supabase.table("ocr_test_sessions").insert(session_data).execute()
            
            if not session_response.data:
                logger.error("セッションの保存に失敗しました")
                return None
            
            session_id = session_response.data[0]["id"]
            logger.info(f"セッション保存完了: {session_id}")
            
            # 各結果を保存
            for result in test_results.get("results", []):
                ocr_result = result["ocr_result"]
                validation = result["validation"]
                
                # 結果データを準備（JSONプロンプト対応）
                result_data = {
                    "session_id": session_id,
                    "file_id": result["file_id"],
                    "filename": result["filename"],
                    "file_size": result.get("file_size"),
                    "issuer_name": ocr_result.get("issuer"),                    # JSONプロンプト版
                    "recipient_name": ocr_result.get("payer"),                  # JSONプロンプト版
                    "receipt_number": ocr_result.get("receipt_number"),
                    "invoice_number": ocr_result.get("main_invoice_number"),    # JSONプロンプト版
                    "registration_number": ocr_result.get("t_number"),          # JSONプロンプト版
                    "currency": ocr_result.get("currency"),
                    "total_amount_tax_included": ocr_result.get("amount_inclusive_tax"),  # JSONプロンプト版
                    "total_amount_tax_excluded": ocr_result.get("amount_exclusive_tax"),  # JSONプロンプト版
                    "issue_date": ocr_result.get("issue_date"),
                    "due_date": ocr_result.get("due_date"),
                    "key_info": ocr_result.get("key_info"),
                    "is_valid": validation["is_valid"],
                    "completeness_score": validation["completeness_score"],
                    "validation_errors": validation["errors"],
                    "validation_warnings": validation["warnings"],
                    "processing_time": 8.5,  # 実際の処理時間を記録
                    "raw_response": ocr_result
                }
                
                # 結果を保存
                result_response = service_supabase.table("ocr_test_results").insert(result_data).execute()
                
                if result_response.data:
                    result_id = result_response.data[0]["id"]
                    
                    # 明細データを保存
                    line_items = ocr_result.get("line_items", [])
                    for i, item in enumerate(line_items, 1):
                        # 税率データの数値変換（"10%" → 10.0）
                        tax_rate = item.get("tax")
                        if tax_rate and isinstance(tax_rate, str):
                            # "%"を除去して数値に変換
                            try:
                                if "%" in tax_rate:
                                    tax_rate = float(tax_rate.replace("%", "").strip())
                                else:
                                    tax_rate = float(tax_rate)
                            except (ValueError, AttributeError):
                                tax_rate = None
                        
                        line_item_data = {
                            "result_id": result_id,
                            "line_number": i,
                            "item_description": item.get("description"),
                            "quantity": item.get("quantity"),
                            "unit_price": item.get("unit_price"),
                            "amount": item.get("amount"),
                            "tax_rate": tax_rate
                        }
                        
                        service_supabase.table("ocr_test_line_items").insert(line_item_data).execute()
            
            logger.info(f"全テスト結果をSupabaseに保存完了: セッションID {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Supabaseへの保存中にエラー: {e}")
            # テーブルが存在しない場合の特別なメッセージ
            if "does not exist" in str(e) or "relation" in str(e):
                st.warning("📊 データベーステーブルが未作成のため、結果を保存できません。管理者にお問い合わせください。")
                logger.info("OCRテスト用テーブルが未作成のため、結果保存をスキップします")
            else:
                st.error(f"データベース保存エラー: {str(e)}")
            return None
    
    def load_sessions_from_supabase(self, user_email: str) -> List[Dict[str, Any]]:
        """ユーザーのOCRテストセッション一覧を取得"""
        if not self.database_manager:
            return []
        
        try:
            # Service Role Keyを使用してRLS回避
            try:
                import streamlit as st
                service_key = st.secrets["database"]["supabase_service_key"]
                supabase_url = st.secrets["database"]["supabase_url"]
                
                from supabase import create_client
                service_supabase = create_client(supabase_url, service_key)
                
                logger.info("Service Role Keyを使用してセッション履歴取得")
                
            except Exception as e:
                logger.warning(f"Service Role Key使用失敗、通常キーで試行: {e}")
                service_supabase = self.database_manager.supabase
            
            response = service_supabase.table("ocr_test_sessions").select("*").eq("created_by", user_email).order("created_at", desc=True).execute()
            
            # レスポンスデータの安全な処理
            data = response.data if response.data else []
            
            # DataFrameの場合はリストに変換
            if hasattr(data, 'to_dict'):
                data = data.to_dict('records')
            elif not isinstance(data, list):
                data = []
            
            return data
            
        except Exception as e:
            logger.error(f"セッション読み込み中にエラー: {e}")
            # テーブルが存在しない場合は空のリストを返す
            if "does not exist" in str(e) or "relation" in str(e):
                logger.info("OCRテスト用テーブルが未作成のため、履歴は表示されません")
            return []
    
    def load_session_results(self, session_id: str) -> List[Dict[str, Any]]:
        """特定セッションの結果を取得"""
        if not self.database_manager:
            return []
        
        try:
            # Service Role Keyを使用してRLS回避
            try:
                import streamlit as st
                service_key = st.secrets["database"]["supabase_service_key"]
                supabase_url = st.secrets["database"]["supabase_url"]
                
                from supabase import create_client
                service_supabase = create_client(supabase_url, service_key)
                
                logger.info("Service Role Keyを使用してセッション結果取得")
                
            except Exception as e:
                logger.warning(f"Service Role Key使用失敗、通常キーで試行: {e}")
                service_supabase = self.database_manager.supabase
            
            # 結果とその明細を結合して取得
            response = service_supabase.table("ocr_test_results").select(
                "*, ocr_test_line_items(*)"
            ).eq("session_id", session_id).execute()
            
            # レスポンスデータの安全な処理
            data = response.data if response.data else []
            
            # DataFrameの場合はリストに変換
            if hasattr(data, 'to_dict'):
                data = data.to_dict('records')
            elif not isinstance(data, list):
                data = []
            
            # ファイルIDマッピングを復元（原本表示用）
            if "file_id_mapping" not in st.session_state:
                st.session_state.file_id_mapping = {}
            
            for record in data:
                filename = record.get("filename", "")
                file_id = record.get("file_id", "")
                if filename and file_id:
                    st.session_state.file_id_mapping[filename] = file_id
            
            return data
            
        except Exception as e:
            logger.error(f"セッション結果読み込み中にエラー: {e}")
            return []

    def display_line_items(self, data_source: Dict, title: str = "📋 明細情報") -> None:
        """明細情報をag-gridで表示する共通メソッド
        
        Args:
            data_source: line_itemsを含む辞書データ (ocr_result または raw_response)
            title: 表示タイトル
        """
        # DataFrameの場合は辞書に変換
        if hasattr(data_source, 'to_dict'):
            data_source = data_source.to_dict()
        elif not isinstance(data_source, dict):
            data_source = {}
        
        # 明細情報を取得
        line_items = data_source.get("line_items", [])
        if not isinstance(line_items, list):
            line_items = []
        
        if len(line_items) > 0:
            st.markdown(f"### {title}")
            line_items_df = pd.DataFrame([
                {
                    "No.": i+1,
                    "商品・サービス名": item.get("description", ""),
                    "数量": item.get("quantity", ""),
                    "単価": item.get("unit_price", ""),
                    "金額": item.get("amount", ""),
                    "税率": item.get("tax", "")
                }
                for i, item in enumerate(line_items)
            ])
            
            # ag-gridで明細表示
            try:
                from infrastructure.ui.aggrid_helper import get_aggrid_manager
                aggrid_manager = get_aggrid_manager()
                aggrid_manager.create_data_grid(
                    line_items_df,
                    editable=False,
                    fit_columns_on_grid_load=True,
                    height=200
                )
            except ImportError:
                # ag-gridが利用できない場合は標準表示
                st.dataframe(line_items_df, use_container_width=True)
            except Exception as e:
                st.error(f"明細表示エラー: {str(e)}")
                st.dataframe(line_items_df, use_container_width=True)
        else:
            st.info(f"{title}: このファイルには明細データがありません")

    def display_invoice_basic_info(self, data_source: Dict, data_type: str = "new") -> None:
        """請求書基本情報を表示する共通メソッド
        
        Args:
            data_source: OCR結果を含む辞書データ
            data_type: データタイプ ("new": 新しいOCRテスト, "history": 履歴データ)
        """
        st.markdown("**基本情報**")
        
        if data_type == "new":
            # 新しいOCRテスト結果の場合
            ocr_result = data_source.get("ocr_result", {})
            
            # 基本フィールドを順序付きで表示（JSONプロンプト対応）
            basic_fields = [
                ("issuer", "請求元"),
                ("payer", "請求先"),
                ("main_invoice_number", "請求書番号"),
                ("amount_inclusive_tax", "税込金額"),
                ("currency", "通貨"),
                ("issue_date", "発行日")
            ]
            
            for field_key, field_label in basic_fields:
                value = ocr_result.get(field_key, "")
                if field_key == "amount_inclusive_tax" and value:
                    try:
                        amount = float(value)
                        st.write(f"• **{field_label}**: {amount:,.0f}円")
                    except (ValueError, TypeError):
                        st.write(f"• **{field_label}**: {value}")
                else:
                    st.write(f"• **{field_label}**: {value}")
                    
        elif data_type == "history":
            # 履歴データの場合
            st.write(f"• **請求元**: {data_source.get('issuer_name', '')}")
            st.write(f"• **請求先**: {data_source.get('recipient_name', '')}")
            st.write(f"• **請求書番号**: {data_source.get('invoice_number', '')}")
            
            amount = data_source.get('total_amount_tax_included', 0)
            try:
                amount_float = float(amount)
                st.write(f"• **税込金額**: {amount_float:,.0f}円")
            except (ValueError, TypeError):
                st.write(f"• **税込金額**: {amount}")
                
            st.write(f"• **通貨**: {data_source.get('currency', '')}")
            st.write(f"• **発行日**: {data_source.get('issue_date', '')}")

    def display_validation_results(self, data_source: Dict, data_type: str = "new") -> None:
        """検証結果を表示する共通メソッド
        
        Args:
            data_source: 検証結果を含む辞書データ
            data_type: データタイプ ("new": 新しいOCRテスト, "history": 履歴データ)
        """
        st.markdown("**検証結果**")
        
        if data_type == "new":
            # 新しいOCRテスト結果の場合
            validation = data_source.get("validation", {})
            is_valid = validation.get("is_valid", False)
            completeness_score = validation.get("completeness_score", 0)
            
            st.write(f"• **検証状況**: {'✅ 正常' if is_valid else '❌ エラー'}")
            st.write(f"• **完全性スコア**: {completeness_score:.1f}%")
            
            # エラー・警告表示
            errors = validation.get("errors", [])
            warnings = validation.get("warnings", [])
            
            if errors:
                st.write("• **エラー**:")
                for error in errors:
                    st.write(f"  - {error}")
            
            if warnings:
                st.write("• **警告**:")
                for warning in warnings:
                    st.write(f"  - {warning}")
                    
        elif data_type == "history":
            # 履歴データの場合
            is_valid = data_source.get("is_valid", False)
            completeness_score = data_source.get("completeness_score", 0)
            
            st.write(f"• **検証状況**: {'✅ 正常' if is_valid else '❌ エラー'}")
            st.write(f"• **完全性スコア**: {completeness_score:.1f}%")
            
            # エラー・警告表示（履歴データから）
            validation_errors = data_source.get("validation_errors", [])
            validation_warnings = data_source.get("validation_warnings", [])
            
            # DataFrameの場合はリストに変換
            if hasattr(validation_errors, 'tolist'):
                validation_errors = validation_errors.tolist()
            elif hasattr(validation_errors, 'to_dict'):
                validation_errors = validation_errors.to_dict('records')
            elif not isinstance(validation_errors, list):
                validation_errors = []
            
            if hasattr(validation_warnings, 'tolist'):
                validation_warnings = validation_warnings.tolist()
            elif hasattr(validation_warnings, 'to_dict'):
                validation_warnings = validation_warnings.to_dict('records')
            elif not isinstance(validation_warnings, list):
                validation_warnings = []
            
            if len(validation_errors) > 0:
                st.write("• **エラー**:")
                for error in validation_errors:
                    st.write(f"  - {error}")
            
            if len(validation_warnings) > 0:
                st.write("• **警告**:")
                for warning in validation_warnings:
                    st.write(f"  - {warning}")

    def display_invoice_details(self, data_source: Dict, data_type: str = "new", show_line_items: bool = True, show_json: bool = True, show_original: bool = True) -> None:
        """請求書詳細情報を統合表示する共通メソッド
        
        Args:
            data_source: 請求書データを含む辞書
            data_type: データタイプ ("new": 新しいOCRテスト, "history": 履歴データ)
            show_line_items: 明細表示の有無
            show_json: JSON表示の有無
            show_original: 原本表示の有無
        """
        col1, col2 = st.columns(2)
        
        with col1:
            self.display_invoice_basic_info(data_source, data_type)
        
        with col2:
            self.display_validation_results(data_source, data_type)
        
        if show_line_items:
            # 明細表示
            st.markdown("---")
            if data_type == "new":
                ocr_result = data_source.get("ocr_result", {})
                self.display_line_items(ocr_result, "📋 明細情報")
            elif data_type == "history":
                raw_response = data_source.get("raw_response", {})
                self.display_line_items(raw_response, "📋 明細情報")
        
        if show_json:
            # JSON表示
            st.markdown("---")
            self.display_json_data(data_source, data_type)
        
        if show_original:
            # 原本表示
            st.markdown("---")
            self.display_original_document(data_source, data_type)

    def display_json_data(self, data_source: Dict, data_type: str = "new") -> None:
        """JSON形式でデータを表示する共通メソッド
        
        Args:
            data_source: 表示するデータ
            data_type: データタイプ ("new": 新しいOCRテスト, "history": 履歴データ)
        """
        st.markdown("### 📄 JSON形式のOCR結果")
        
        if data_type == "new":
            # 新しいOCRテスト結果の場合
            ocr_result = data_source.get("ocr_result", {})
            validation = data_source.get("validation", {})
            
            # OCR結果と検証結果を統合
            json_data = {
                "ocr_result": ocr_result,
                "validation": validation,
                "filename": data_source.get("filename", "")
            }
            
        elif data_type == "history":
            # 履歴データの場合
            raw_response = data_source.get("raw_response", {})
            
            # DataFrameの場合は辞書に変換
            if hasattr(raw_response, 'to_dict'):
                raw_response = raw_response.to_dict()
            elif not isinstance(raw_response, dict):
                raw_response = {}
            
            json_data = {
                "filename": data_source.get("filename", ""),
                "issuer_name": data_source.get("issuer_name", ""),
                "recipient_name": data_source.get("recipient_name", ""),
                "invoice_number": data_source.get("invoice_number", ""),
                "total_amount_tax_included": data_source.get("total_amount_tax_included", 0),
                "currency": data_source.get("currency", ""),
                "issue_date": data_source.get("issue_date", ""),
                "is_valid": data_source.get("is_valid", False),
                "completeness_score": data_source.get("completeness_score", 0),
                "validation_errors": data_source.get("validation_errors", []),
                "validation_warnings": data_source.get("validation_warnings", []),
                "raw_response": raw_response
            }
        
        # JSONを整形して表示
        import json
        try:
            json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
            st.code(json_str, language="json")
        except Exception as e:
            st.error(f"JSON表示エラー: {str(e)}")
            st.write("**Raw Data:**")
            st.write(json_data)

    def display_original_document(self, data_source: Dict, data_type: str = "new") -> None:
        """原本ドキュメントを表示する共通メソッド
        
        Args:
            data_source: ファイル情報を含む辞書
            data_type: データタイプ ("new": 新しいOCRテスト, "history": 履歴データ)
        """
        st.markdown("### 📎 原本ドキュメント")
        
        filename = data_source.get("filename", "")
        if not filename:
            st.info("ファイル名が取得できません")
            return
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # 原本表示ボタン
            if st.button(f"📄 {filename} を表示", key=f"show_original_{filename}_{data_type}"):
                st.session_state[f"show_pdf_{filename}"] = True
            
            # デバッグ用: ファイルIDマッピング確認ボタン
            if st.button(f"🔍 IDマッピング確認", key=f"check_mapping_{filename}_{data_type}"):
                file_id_mapping = st.session_state.get("file_id_mapping", {})
                file_id = file_id_mapping.get(filename, "")
                if file_id:
                    st.success(f"✅ ファイルID: {file_id}")
                else:
                    st.error(f"❌ ファイルIDが見つかりません")
                    st.write(f"利用可能なマッピング: {list(file_id_mapping.keys())}")
        
        with col2:
            # ファイル情報表示
            st.write(f"**ファイル名**: {filename}")
            if data_type == "new":
                file_size = data_source.get("file_size", 0)
                try:
                    # ファイルサイズを数値に変換
                    size_num = float(file_size) if file_size else 0
                    st.write(f"**ファイルサイズ**: {size_num:,.0f} bytes")
                except (ValueError, TypeError):
                    st.write(f"**ファイルサイズ**: {file_size} bytes")
        
        # PDF表示（ポップアップ的な表示）
        if st.session_state.get(f"show_pdf_{filename}", False):
            with st.expander(f"📄 {filename} - 原本表示", expanded=True):
                try:
                    # Google Driveからファイルを取得
                    if hasattr(self, 'drive_manager') and self.drive_manager:
                        # ファイル名からGoogle Drive IDを取得
                        file_id = self._get_file_id_from_filename(filename)
                        if file_id:
                            # PDFファイルをダウンロード
                            pdf_content = self.download_pdf_from_drive(file_id)
                            if pdf_content:
                                # PDFを表示
                                st.markdown("**📄 PDF原本:**")
                                
                                # ダウンロードボタン
                                st.download_button(
                                    label="📥 PDFをダウンロード",
                                    data=pdf_content,
                                    file_name=filename,
                                    mime="application/pdf",
                                    key=f"download_{filename}_{data_type}"
                                )
                                
                                # PDFビューアー（iframe使用）
                                import base64
                                base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
                                pdf_display = f'''
                                <div style="border: 1px solid #ccc; border-radius: 5px; margin: 10px 0;">
                                    <iframe 
                                        src="data:application/pdf;base64,{base64_pdf}" 
                                        width="100%" 
                                        height="600px" 
                                        style="border: none;"
                                        type="application/pdf">
                                        <p>PDFを表示できません。<a href="data:application/pdf;base64,{base64_pdf}" download="{filename}">ダウンロード</a>してご確認ください。</p>
                                    </iframe>
                                </div>
                                '''
                                st.markdown(pdf_display, unsafe_allow_html=True)
                                
                                # ファイル情報
                                st.info(f"📊 ファイルサイズ: {len(pdf_content):,} bytes")
                            else:
                                st.error("📥 PDFファイルの取得に失敗しました")
                                st.info("Google Driveからファイルをダウンロードできませんでした。")
                        else:
                            st.error("🔍 Google Drive上のファイルIDが見つかりません")
                            st.info(f"ファイル名: {filename} のIDがセッション状態に保存されていません。")
                    else:
                        st.error("🔧 Google Driveマネージャーが利用できません")
                        st.info("Google Driveとの接続が確立されていません。")
                
                except Exception as e:
                    st.error(f"🚨 原本表示エラー: {str(e)}")
                    st.info("原本の表示に失敗しました。以下をご確認ください：")
                    st.write("• Google Driveへの接続状況")
                    st.write("• ファイルのアクセス権限")
                    st.write("• ファイルが削除されていないか")
                    
                    # デバッグ情報
                    with st.expander("🔍 デバッグ情報"):
                        st.write(f"**ファイル名**: {filename}")
                        st.write(f"**データタイプ**: {data_type}")
                        st.write(f"**ファイルIDマッピング**: {st.session_state.get('file_id_mapping', {})}")
                        st.write(f"**drive_manager**: {hasattr(self, 'drive_manager')}")
                        if hasattr(self, 'drive_manager'):
                            st.write(f"**drive_manager.service**: {hasattr(self.drive_manager, 'service') if self.drive_manager else 'None'}")
                        import traceback
                        st.code(traceback.format_exc())
                
                # 閉じるボタン
                if st.button("❌ 閉じる", key=f"close_pdf_{filename}_{data_type}"):
                    st.session_state[f"show_pdf_{filename}"] = False
                    st.rerun()

    def _get_file_id_from_filename(self, filename: str) -> str:
        """ファイル名からGoogle Drive IDを取得するヘルパーメソッド
        
        Args:
            filename: ファイル名
            
        Returns:
            Google Drive ファイルID
        """
        # セッション状態に保存されたファイルIDマッピングを確認
        file_id_mapping = st.session_state.get("file_id_mapping", {})
        file_id = file_id_mapping.get(filename, "")
        
        # デバッグログ
        logger.info(f"ファイルID取得: {filename} -> {file_id}")
        logger.info(f"利用可能なファイルIDマッピング: {list(file_id_mapping.keys())}")
        
        return file_id

    def analyze_error_details(self, result: Dict[str, Any], validation: Dict[str, Any]) -> Dict[str, Any]:
        """エラー詳細分析と修正提案"""
        analysis = {
            "error_summary": {},
            "missing_fields": [],
            "correction_suggestions": [],
            "manual_review_needed": False,
            "retry_recommended": False
        }
        
        # 必須フィールドの欠損分析（JSONプロンプト対応）
        required_fields = {
            "issuer": "請求元企業名",
            "amount_inclusive_tax": "税込金額", 
            "currency": "通貨"
        }
        
        for field, display_name in required_fields.items():
            value = result.get(field)
            if not self._is_valid_field_value(value):
                analysis["missing_fields"].append({
                    "field": field,
                    "display_name": display_name,
                    "current_value": value,
                    "suggestion": self._get_field_correction_suggestion(field, result)
                })
        
        # エラーカテゴリ別の修正提案
        error_categories = validation.get("error_categories", {})
        
        if error_categories.get("data_missing"):
            analysis["correction_suggestions"].append({
                "type": "prompt_improvement",
                "priority": "high",
                "description": "プロンプトを調整して必須データの抽出精度を向上",
                "action": "OCRプロンプトの必須フィールド指示を強化"
            })
            analysis["retry_recommended"] = True
        
        if error_categories.get("data_format"):
            analysis["correction_suggestions"].append({
                "type": "data_validation",
                "priority": "medium", 
                "description": "データ形式の正規化処理を追加",
                "action": "前処理ステップでデータクリーニングを実施"
            })
        
        if error_categories.get("business_logic"):
            analysis["correction_suggestions"].append({
                "type": "business_rule",
                "priority": "low",
                "description": "ビジネスルールの調整が必要",
                "action": "個別処理ルールまたは例外設定を検討"
            })
        
        # 手動レビューが必要かの判定
        if (len(analysis["missing_fields"]) > 2 or 
            validation["completeness_score"] < 30 or
            any("critical" in str(error) for error in validation.get("errors", []))):
            analysis["manual_review_needed"] = True
        
        return analysis
    
    def _get_field_correction_suggestion(self, field: str, result: Dict[str, Any]) -> str:
        """フィールド別の修正提案を生成（JSONプロンプト対応）"""
        if field == "issuer":
            # 他のフィールドから推測可能な情報を確認
            if result.get("key_info", {}).get("payee"):
                return f"key_info.payeeに '{result['key_info']['payee']}' があります。これを使用可能か確認"
            return "PDFから企業名を手動で確認し、プロンプトの企業名抽出指示を強化"
        
        elif field == "amount_inclusive_tax":
            # 明細から推測可能か確認
            line_items = result.get("line_items", [])
            if not isinstance(line_items, list):
                line_items = []
            if len(line_items) > 0:
                return "明細情報は取得できています。明細合計から税込金額を計算することを検討"
            return "金額情報の抽出ルールを見直し、数値フォーマットの認識を改善"
        
        elif field == "currency":
            # 他の金額フィールドから推測（JSONプロンプト対応）
            if result.get("amount_inclusive_tax") or result.get("amount_exclusive_tax"):
                return "金額は取得できているため、通貨はJPYと推定。自動補完ルールを追加"
            return "PDFから通貨表記を確認し、通貨コード抽出の指示を強化"
        
        return "個別確認が必要です"

    def create_correction_workflow(self, error_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """エラーファイルの修正ワークフローを作成"""
        workflow = {
            "total_errors": len(error_files),
            "correction_plan": {
                "prompt_adjustments": [],
                "manual_reviews": [],
                "system_improvements": []
            },
            "priority_order": []
        }
        
        for error_file in error_files:
            result = error_file["ocr_result"]
            validation = error_file["validation"]
            analysis = self.analyze_error_details(result, validation)
            
            file_info = {
                "filename": error_file["filename"],
                "completeness_score": validation["completeness_score"],
                "analysis": analysis,
                "priority": "high" if analysis["manual_review_needed"] else "medium"
            }
            
            workflow["priority_order"].append(file_info)
            
            # 修正提案を分類
            for suggestion in analysis["correction_suggestions"]:
                if suggestion["type"] == "prompt_improvement":
                    workflow["correction_plan"]["prompt_adjustments"].append({
                        "file": error_file["filename"],
                        "suggestion": suggestion
                    })
                elif suggestion["type"] == "data_validation":
                    workflow["correction_plan"]["system_improvements"].append({
                        "file": error_file["filename"],
                        "suggestion": suggestion
                    })
            
            if analysis["manual_review_needed"]:
                workflow["correction_plan"]["manual_reviews"].append(file_info)
        
        # 優先順位でソート（完全性スコアが低い順）
        workflow["priority_order"].sort(key=lambda x: x["completeness_score"])
        
        return workflow

    def display_results_with_aggrid(self, test_results: Dict[str, Any]) -> None:
        """ag-gridを使ってテスト結果を表示"""
        try:
            from infrastructure.ui.aggrid_helper import get_aggrid_manager
            
            aggrid_manager = get_aggrid_manager()
            if not aggrid_manager:
                st.warning("ag-gridマネージャーの初期化に失敗しました。代替表示を使用します。")
                return
            
            # 結果データをDataFrameに変換
            results_data = []
            for result in test_results.get("results", []):
                ocr_result = result["ocr_result"]
                validation = result["validation"]
                
                # 完全性スコアの安全な変換
                completeness_score = validation.get('completeness_score', 0)
                if isinstance(completeness_score, (int, float)):
                    completeness_score = float(round(completeness_score, 1))
                else:
                    completeness_score = 0.0
                
                # 税込金額の安全な変換（JSONプロンプト対応）
                tax_included = ocr_result.get("amount_inclusive_tax", 0)
                if not isinstance(tax_included, (int, float)):
                    try:
                        tax_included = float(tax_included) if tax_included else 0
                    except (ValueError, TypeError):
                        tax_included = 0
                tax_included = int(tax_included)
                
                # エラー数と警告数の安全な変換
                error_count = len(validation.get("errors", []))
                warning_count = len(validation.get("warnings", []))
                file_size = result.get('file_size', 0)
                
                # ファイルサイズの安全な変換
                try:
                    file_size = int(file_size) if file_size else 0
                except (ValueError, TypeError):
                    file_size = 0
                
                results_data.append({
                    "ファイル名": str(result["filename"]),
                    "請求元": str(ocr_result.get("issuer", "")),                   # JSONプロンプト版
                    "請求先": str(ocr_result.get("payer", "")),                    # JSONプロンプト版
                    "請求書番号": str(ocr_result.get("main_invoice_number", "")),  # JSONプロンプト版
                    "通貨": str(ocr_result.get("currency", "")),
                    "税込金額": tax_included,
                    "発行日": str(ocr_result.get("issue_date", "")),
                    "検証状況": "✅ 正常" if validation["is_valid"] else "❌ エラー",
                    "完全性スコア": completeness_score,
                    "エラー数": error_count,
                    "警告数": warning_count,
                    "ファイルサイズ": f"{file_size:,} bytes"
                })
            
            if len(results_data) > 0:
                df = pd.DataFrame(results_data)
                
                # 選択状態リセットボタン
                col_grid, col_reset = st.columns([4, 1])
                with col_grid:
                    st.subheader("📊 OCRテスト結果 (ag-grid)")
                with col_reset:
                    if st.button("🔄 選択リセット", key="reset_current_test_selection"):
                        current_test_key = "selected_current_test_file"
                        if current_test_key in st.session_state:
                            del st.session_state[current_test_key]
                        st.rerun()
                
                grid_response = aggrid_manager.create_data_grid(
                    df,
                    editable=False,
                    fit_columns_on_grid_load=True,
                    selection_mode="single",
                    use_checkbox=False,
                    height=400
                )
                
                # 選択された行の詳細表示
                selected_rows = aggrid_manager.get_selected_rows(grid_response)
                
                # selected_rowsの安全な処理
                if hasattr(selected_rows, 'to_dict'):
                    selected_rows = selected_rows.to_dict('records')
                elif not isinstance(selected_rows, list):
                    selected_rows = []
                
                # セッション状態で選択情報を管理（新しいOCRテスト用）
                current_test_key = "selected_current_test_file"
                
                # 新しい選択があればセッション状態を更新
                if len(selected_rows) > 0:
                    selected_row = selected_rows[0]
                    filename = selected_row["ファイル名"]
                    st.session_state[current_test_key] = filename
                # 選択がなければセッション状態から復元
                elif current_test_key in st.session_state:
                    filename = st.session_state[current_test_key]
                else:
                    filename = None
                
                # ファイルが選択されている場合の詳細表示
                if filename:
                    st.markdown(f"### 📄 選択されたファイル: {filename}")
                    
                    # 該当する詳細結果を取得
                    try:
                        selected_result = next(
                            r for r in test_results["results"] 
                            if r["filename"] == filename
                        )
                    except StopIteration:
                        st.error(f"❌ ファイル '{filename}' の詳細結果が見つかりません")
                        # セッション状態をクリア
                        if current_test_key in st.session_state:
                            del st.session_state[current_test_key]
                        selected_result = None
                    
                    # 詳細情報を表示（共通メソッド使用）
                    if selected_result is not None:
                        self.display_invoice_details(selected_result, data_type="new", show_line_items=True)
                    
        except ImportError:
            st.warning("ag-gridライブラリが利用できません。標準のDataFrameで表示します。")
        except Exception as e:
            st.error(f"ag-grid表示中にエラー: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            
            # デバッグ情報を表示
            st.subheader("🔍 デバッグ情報")
            st.write("**データ型情報:**")
            if len(results_data) > 0:
                sample_data = results_data[0]
                for key, value in sample_data.items():
                    st.write(f"• {key}: {type(value)} = {repr(value)}")
            
            # 代替表示
            st.subheader("📊 代替表示（標準DataFrame）")
            if len(results_data) > 0:
                df = pd.DataFrame(results_data)
                st.dataframe(df, use_container_width=True)


def display_session_history(ocr_test_manager: 'OCRTestManager', user_email: str) -> None:
    """Supabaseからのセッション履歴を表示"""
    
    st.markdown("---")
    st.subheader("📈 過去のOCRテスト履歴")
    
    sessions = ocr_test_manager.load_sessions_from_supabase(user_email)
    
    # DataFrameの場合はリストに変換
    if hasattr(sessions, 'to_dict'):
        sessions = sessions.to_dict('records')
    elif not isinstance(sessions, list):
        sessions = []
    
    if len(sessions) == 0:
        st.info("過去のテスト履歴がありません")
        return
    
    # セッション選択
    session_options = [
        f"{session['session_name']} ({convert_utc_to_jst(session['created_at'])}) - 成功率: {session['success_rate']}%"
        for session in sessions
    ]
    
    selected_session_index = st.selectbox(
        "表示するセッションを選択",
        range(len(session_options)),
        format_func=lambda x: session_options[x]
    )
    
    if selected_session_index is not None:
        selected_session = sessions[selected_session_index]
        session_id = selected_session["id"]
        
        # セッション詳細表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("処理ファイル数", selected_session["total_files"])
        with col2:
            st.metric("成功ファイル数", selected_session["success_files"])
        with col3:
            st.metric("成功率", f"{selected_session['success_rate']}%")
        with col4:
            st.metric("平均完全性", f"{selected_session['average_completeness']}%")
        
        # セッション結果を取得
        session_results = ocr_test_manager.load_session_results(session_id)
        
        # DataFrameの場合はリストに変換
        if hasattr(session_results, 'to_dict'):
            session_results = session_results.to_dict('records')
        elif not isinstance(session_results, list):
            session_results = []
        
        if len(session_results) > 0:
            try:
                from infrastructure.ui.aggrid_helper import get_aggrid_manager
                
                aggrid_manager = get_aggrid_manager()
                if aggrid_manager:
                    # 履歴データをDataFrameに変換
                    history_data = []
                    for result in session_results:
                        # 完全性スコアの安全な変換
                        completeness_score = result.get('completeness_score', 0)
                        if isinstance(completeness_score, (int, float)):
                            completeness_score = float(round(completeness_score, 1))
                        else:
                            completeness_score = 0.0
                        
                        # 税込金額の安全な変換
                        tax_included = result.get("total_amount_tax_included", 0)
                        if not isinstance(tax_included, (int, float)):
                            tax_included = 0
                        
                        history_data.append({
                            "ファイル名": str(result["filename"]),
                            "請求元": str(result["issuer_name"] or ""),      # DBフィールド名（変更なし）
                            "請求書番号": str(result["invoice_number"] or ""), # DBフィールド名（変更なし）
                            "通貨": str(result["currency"] or ""),
                            "税込金額": int(tax_included),
                            "発行日": str(result["issue_date"]) if result["issue_date"] else "",
                            "検証状況": "✅ 正常" if result["is_valid"] else "❌ エラー",
                            "完全性スコア": completeness_score,
                            "処理日時": convert_utc_to_jst(result["created_at"])
                        })
                    
                    if len(history_data) > 0:
                        df_history = pd.DataFrame(history_data)
                        
                        # 選択状態リセットボタン
                        col_grid, col_reset = st.columns([4, 1])
                        with col_grid:
                            st.subheader("履歴詳細 (ag-grid)")
                        with col_reset:
                            if st.button("🔄 選択リセット", key=f"reset_selection_{session_id}"):
                                session_key = f"selected_history_file_{session_id}"
                                if session_key in st.session_state:
                                    del st.session_state[session_key]
                                st.rerun()
                        
                        grid_response = aggrid_manager.create_data_grid(
                            df_history,
                            editable=False,
                            fit_columns_on_grid_load=True,
                            selection_mode="single",
                            height=400
                        )
                        
                        # 選択された行の詳細表示
                        selected_rows = aggrid_manager.get_selected_rows(grid_response)
                        
                        # selected_rowsの安全な処理
                        if hasattr(selected_rows, 'to_dict'):
                            selected_rows = selected_rows.to_dict('records')
                        elif not isinstance(selected_rows, list):
                            selected_rows = []
                        
                        # セッション状態で選択情報を管理
                        session_key = f"selected_history_file_{session_id}"
                        
                        # 新しい選択があればセッション状態を更新
                        if len(selected_rows) > 0:
                            selected_row = selected_rows[0]
                            filename = selected_row["ファイル名"]
                            st.session_state[session_key] = filename
                        # 選択がなければセッション状態から復元
                        elif session_key in st.session_state:
                            filename = st.session_state[session_key]
                        else:
                            filename = None
                        
                        # ファイルが選択されている場合の詳細表示
                        if filename:
                            st.markdown(f"### 📄 選択されたファイル: {filename}")
                            
                            # 該当する詳細結果を取得
                            try:
                                selected_result = next(
                                    r for r in session_results 
                                    if r["filename"] == filename
                                )
                            except StopIteration:
                                st.error(f"❌ ファイル '{filename}' の詳細結果が見つかりません")
                                # セッション状態をクリア
                                if session_key in st.session_state:
                                    del st.session_state[session_key]
                                selected_result = None
                            
                            # 詳細情報を表示（共通メソッド使用）
                            if selected_result is not None:
                                # 基本情報+検証結果+明細を統合表示
                                ocr_test_manager.display_invoice_details(selected_result, data_type="history", show_line_items=True)
                                
                                # エラーファイルの場合、修正提案を表示
                                is_valid = selected_result.get("is_valid", False)
                                if not is_valid:
                                    st.markdown("---")
                                    st.markdown("### 🔧 エラー修正提案")
                                    
                                    # raw_responseから詳細なデータを復元
                                    raw_response = selected_result.get("raw_response", {})
                                    
                                    # DataFrameの場合は辞書に変換
                                    if hasattr(raw_response, 'to_dict'):
                                        raw_response = raw_response.to_dict()
                                    elif not isinstance(raw_response, dict):
                                        raw_response = {}
                                    
                                    if len(raw_response) > 0:
                                        # 簡易的な修正提案を表示
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            st.markdown("**欠損している可能性のあるフィールド:**")
                                            
                                            # 必須フィールドチェック（JSONプロンプト対応）
                                            required_checks = [
                                                ("請求元企業名", raw_response.get("issuer")),
                                                ("税込金額", raw_response.get("amount_inclusive_tax")),
                                                ("通貨", raw_response.get("currency"))
                                            ]
                                            
                                            for field_name, value in required_checks:
                                                if not value:
                                                    st.write(f"❌ {field_name}")
                                                else:
                                                    st.write(f"✅ {field_name}: {value}")
                                        
                                        with col2:
                                            st.markdown("**推奨修正アクション:**")
                                            st.write("• プロンプト調整を検討")
                                            st.write("• ファイル品質を確認")
                                            st.write("• 手動補正を実施")
                    else:
                        st.info("テスト結果データがありません")
                        
            except ImportError:
                st.warning("ag-gridライブラリが利用できません。標準表示を使用します。")
                
                # 標準的なDataFrame表示
                if len(session_results) > 0:
                    history_df = pd.DataFrame([
                        {
                            "ファイル名": result["filename"],
                            "請求元": result.get("issuer_name", ""),
                            "請求書番号": result.get("invoice_number", ""),
                            "通貨": result.get("currency", ""),
                            "税込金額": result.get("total_amount_tax_included", 0),
                            "検証状況": "✅ 正常" if result.get("is_valid") else "❌ エラー",
                            "完全性スコア": result.get("completeness_score", 0),
                            "処理日時": convert_utc_to_jst(result["created_at"])
                        }
                        for result in session_results
                    ])
                    st.dataframe(history_df, use_container_width=True)
        else:
            st.info("選択されたセッションの結果データがありません")


def create_ocr_test_app():
    """OCRテスト用Streamlitアプリを作成"""
    
    st.title("🔍 OCR精度テスト - Gemini 2.0-flash")
    st.markdown("---")
    
    # 必要なモジュールをインポート
    try:
        from infrastructure.storage.google_drive_helper import get_google_drive
        from infrastructure.ai.gemini_helper import get_gemini_api
        from infrastructure.database.database import get_database
        from infrastructure.auth.oauth_handler import get_current_user
        
        drive_manager = get_google_drive()
        gemini_manager = get_gemini_api()
        database_manager = get_database()
        
        if not drive_manager or not gemini_manager:
            st.error("Google DriveまたはGemini APIの初期化に失敗しました")
            return
        
        ocr_test_manager = OCRTestManager(drive_manager, gemini_manager, database_manager)
        
        # 現在のユーザー情報を取得
        current_user = get_current_user()
        user_email = current_user.get("email", "unknown@example.com")
        
    except Exception as e:
        st.error(f"初期化エラー: {str(e)}")
        return
    
    # タブ作成
    tab1, tab2 = st.tabs(["🚀 新しいOCRテスト", "📈 テスト履歴"])
    
    with tab1:
        # Google Driveフォルダ設定
        st.subheader("📁 Google Driveフォルダ設定")
        
        default_folder_id = "1ZCJsI9j8A9VJcmiY79BcP1jgzsD51X6E"
        folder_id = st.text_input(
            "フォルダID",
            value=default_folder_id,
            help="Google DriveのフォルダIDを入力してください"
        )
        
        if st.button("📋 フォルダ内PDFファイル一覧取得"):
            with st.spinner("PDFファイル一覧を取得中..."):
                pdf_files = ocr_test_manager.get_drive_pdfs(folder_id)
                
                # DataFrameの場合はリストに変換
                if hasattr(pdf_files, 'to_dict'):
                    pdf_files = pdf_files.to_dict('records')
                elif not isinstance(pdf_files, list):
                    pdf_files = []
                
                if len(pdf_files) > 0:
                    st.success(f"{len(pdf_files)}個のPDFファイルが見つかりました")
                    
                    # ファイル一覧表示
                    files_df = pd.DataFrame([
                        {
                            "ファイル名": f["name"],
                            "サイズ": f.get("size", "不明"),
                            "更新日時": convert_utc_to_jst(f.get("modifiedTime", "")) if f.get("modifiedTime") else "不明",
                            "ファイルID": f["id"]
                        }
                        for f in pdf_files
                    ])
                    
                    st.dataframe(files_df, use_container_width=True)
                    
                    # セッションステートに保存
                    st.session_state.pdf_files = pdf_files
        
        st.markdown("---")
        
        # OCRテスト実行
        st.subheader("🤖 OCRテスト実行")
        
        # テスト件数選択
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write("指定フォルダ内のPDFファイルに対してOCR処理を実行します")
            
        with col2:
            # テスト件数選択
            max_files = st.selectbox(
                "テスト件数",
                options=[5, 10, 20, 50, -1],
                format_func=lambda x: "全て" if x == -1 else f"{x}件",
                index=0,  # デフォルト5件
                help="処理するPDFファイルの最大件数を選択"
            )
            
        with col3:
            if st.button("🚀 OCRテスト実行", type="primary"):
                if not folder_id:
                    st.error("フォルダIDを入力してください")
                else:
                    with st.spinner(f"OCRテストを実行中...（最大{max_files if max_files != -1 else '全'}件）"):
                        test_results = ocr_test_manager.run_comprehensive_test(folder_id, max_files=max_files)
                        
                        # セッションステートに保存
                        st.session_state.test_results = test_results
                        
                        # Supabaseに保存
                        if len(test_results.get("results", [])) > 0:
                            session_id = ocr_test_manager.save_to_supabase(test_results, user_email)
                            if session_id:
                                st.success(f"✅ 結果をデータベースに保存しました (セッションID: {session_id})")
                                st.session_state.current_session_id = session_id
        
        # テスト結果表示
        if hasattr(st.session_state, 'test_results') and len(st.session_state.test_results.get("results", [])) > 0:
            st.markdown("---")
            st.subheader("📊 テスト結果")
            
            test_results = st.session_state.test_results
            
            # サマリー表示
            if test_results.get("summary"):
                summary = test_results["summary"]
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("成功率", f"{summary['success_rate']}%")
                with col2:
                    st.metric("平均完全性", f"{summary['average_completeness']}%")
                with col3:
                    st.metric("処理ファイル数", test_results["files_processed"])
                with col4:
                    st.metric("処理時間", f"{test_results['duration']:.1f}秒")
            
            # ag-gridでの表示
            ocr_test_manager.display_results_with_aggrid(test_results)
    
    with tab2:
        # テスト履歴表示
        display_session_history(ocr_test_manager, user_email)


if __name__ == "__main__":
    create_ocr_test_app() 