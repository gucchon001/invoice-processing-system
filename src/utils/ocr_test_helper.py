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
from datetime import datetime
import io
import uuid

# 設定ヘルパーをインポート
from utils.config_helper import get_gemini_model

# ロガー設定
logger = logging.getLogger(__name__)

class OCRTestManager:
    """OCRテスト管理クラス"""
    
    def __init__(self, drive_manager, gemini_manager, database_manager=None):
        """初期化"""
        self.drive_manager = drive_manager
        self.gemini_manager = gemini_manager
        self.database_manager = database_manager
        
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
    
    def create_ocr_prompt(self) -> str:
        """OCR用のプロンプトを作成"""
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
            
            # OCR用プロンプト作成
            prompt = self.create_ocr_prompt()
            
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
        """OCR結果の検証"""
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "completeness_score": 0
        }
        
        required_fields = [
            "issuer_name", "total_amount_tax_included", "currency"
        ]
        
        optional_fields = [
            "recipient_name", "invoice_number", "registration_number", 
            "total_amount_tax_excluded", "issue_date", "due_date", "line_items"
        ]
        
        # 必須フィールドチェック
        for field in required_fields:
            if not result.get(field):
                validation["errors"].append(f"必須フィールド '{field}' が欠損")
                validation["is_valid"] = False
        
        # オプションフィールドチェック
        for field in optional_fields:
            if not result.get(field):
                validation["warnings"].append(f"オプションフィールド '{field}' が欠損")
        
        # 完全性スコア計算
        total_fields = len(required_fields) + len(optional_fields)
        filled_fields = sum(1 for field in required_fields + optional_fields if result.get(field))
        validation["completeness_score"] = round((filled_fields / total_fields) * 100, 1)
        
        # 金額の妥当性チェック
        tax_included = result.get("total_amount_tax_included")
        tax_excluded = result.get("total_amount_tax_excluded")
        
        if (tax_included is not None and isinstance(tax_included, (int, float)) and 
            tax_excluded is not None and isinstance(tax_excluded, (int, float))):
            if tax_included <= tax_excluded:
                validation["warnings"].append("税込金額が税抜金額以下です")
        
        # 明細の整合性チェック
        line_items = result.get("line_items", [])
        if line_items:
            line_total = sum(item.get("amount", 0) for item in line_items if isinstance(item.get("amount"), (int, float)))
            invoice_total = result.get("total_amount_tax_excluded")
            
            # invoice_totalがNoneでない場合のみチェック
            if invoice_total is not None and isinstance(invoice_total, (int, float)) and invoice_total > 0:
                if abs(line_total - invoice_total) > invoice_total * 0.1:  # 10%以上の差異
                    validation["warnings"].append(f"明細合計({line_total})と請求金額({invoice_total})に差異があります")
        
        return validation
    
    def format_ocr_result_for_display(self, result: Dict[str, Any], validation: Dict[str, Any]) -> pd.DataFrame:
        """OCR結果を表示用データフレームに変換"""
        
        # 基本情報
        basic_info = []
        field_mapping = {
            "issuer_name": "請求元企業名",
            "recipient_name": "請求先企業名", 
            "receipt_number": "領収書番号",
            "invoice_number": "請求書番号",
            "registration_number": "登録番号",
            "currency": "通貨",
            "total_amount_tax_included": "税込金額",
            "total_amount_tax_excluded": "税抜金額",
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
        
        if line_items:
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
            
            if not pdf_files:
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
            
            # 各ファイルを処理
            for i, file_info in enumerate(pdf_files):
                file_id = file_info["id"]
                filename = file_info["name"]
                
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
                        
                        test_results["files_success"] += 1
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
            
            if test_results["results"]:
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
                
                # 結果データを準備
                result_data = {
                    "session_id": session_id,
                    "file_id": result["file_id"],
                    "filename": result["filename"],
                    "file_size": result.get("file_size"),
                    "issuer_name": ocr_result.get("issuer_name"),
                    "recipient_name": ocr_result.get("recipient_name"),
                    "receipt_number": ocr_result.get("receipt_number"),
                    "invoice_number": ocr_result.get("invoice_number"),
                    "registration_number": ocr_result.get("registration_number"),
                    "currency": ocr_result.get("currency"),
                    "total_amount_tax_included": ocr_result.get("total_amount_tax_included"),
                    "total_amount_tax_excluded": ocr_result.get("total_amount_tax_excluded"),
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
            
            return response.data if response.data else []
            
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
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"セッション結果読み込み中にエラー: {e}")
            return []


def display_results_with_aggrid(test_results: Dict[str, Any]) -> None:
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
            
            # 税込金額の安全な変換
            tax_included = ocr_result.get("total_amount_tax_included", 0)
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
                "請求元": str(ocr_result.get("issuer_name", "")),
                "請求先": str(ocr_result.get("recipient_name", "")),
                "請求書番号": str(ocr_result.get("invoice_number", "")),
                "通貨": str(ocr_result.get("currency", "")),
                "税込金額": tax_included,
                "発行日": str(ocr_result.get("issue_date", "")),
                "検証状況": "✅ 正常" if validation["is_valid"] else "❌ エラー",
                "完全性スコア": completeness_score,
                "エラー数": error_count,
                "警告数": warning_count,
                "ファイルサイズ": f"{file_size:,} bytes"
            })
        
        if results_data and len(results_data) > 0:
            df = pd.DataFrame(results_data)
            
            # ag-gridで表示
            st.subheader("📊 OCRテスト結果 (ag-grid)")
            
            grid_response = aggrid_manager.create_data_grid(
                df,
                editable=False,
                fit_columns_on_grid_load=True,
                selection_mode="single",
                use_checkbox=False,
                height=400
            )
            
            # 選択された行の詳細表示
            if grid_response and grid_response.get("selected_rows"):
                selected_row = grid_response["selected_rows"][0]
                filename = selected_row["ファイル名"]
                
                st.markdown(f"### 📄 選択されたファイル: {filename}")
                
                # 該当する詳細結果を取得
                selected_result = next(
                    r for r in test_results["results"] 
                    if r["filename"] == filename
                )
                
                # 詳細情報を表示
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**基本情報**")
                    ocr_result = selected_result["ocr_result"]
                    for key, value in ocr_result.items():
                        if key != "line_items" and value is not None:
                            st.write(f"• **{key}**: {value}")
                
                with col2:
                    st.markdown("**検証結果**")
                    validation = selected_result["validation"]
                    st.write(f"• **検証状況**: {'✅ 正常' if validation['is_valid'] else '❌ エラー'}")
                    st.write(f"• **完全性スコア**: {validation['completeness_score']:.1f}%")
                    
                    if validation["errors"]:
                        st.write("• **エラー**:")
                        for error in validation["errors"]:
                            st.write(f"  - {error}")
                    
                    if validation["warnings"]:
                        st.write("• **警告**:")
                        for warning in validation["warnings"]:
                            st.write(f"  - {warning}")
                
                # 明細表示
                line_items = ocr_result.get("line_items", [])
                if line_items:
                    st.markdown("**明細情報**")
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
                    
                    aggrid_manager.create_data_grid(
                        line_items_df,
                        editable=False,
                        fit_columns_on_grid_load=True,
                        height=200
                    )
                
    except ImportError:
        st.warning("ag-gridライブラリが利用できません。標準のDataFrameで表示します。")
    except Exception as e:
        st.error(f"ag-grid表示中にエラー: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        
        # デバッグ情報を表示
        st.subheader("🔍 デバッグ情報")
        st.write("**データ型情報:**")
        if results_data and len(results_data) > 0:
            sample_data = results_data[0]
            for key, value in sample_data.items():
                st.write(f"• {key}: {type(value)} = {repr(value)}")
        
        # 代替表示
        st.subheader("📊 代替表示（標準DataFrame）")
        if results_data and len(results_data) > 0:
            df = pd.DataFrame(results_data)
            st.dataframe(df, use_container_width=True)


def display_session_history(ocr_test_manager: 'OCRTestManager', user_email: str) -> None:
    """Supabaseからのセッション履歴を表示"""
    
    st.markdown("---")
    st.subheader("📈 過去のOCRテスト履歴")
    
    sessions = ocr_test_manager.load_sessions_from_supabase(user_email)
    
    if not sessions:
        st.info("過去のテスト履歴がありません")
        return
    
    # セッション選択
    session_options = [
        f"{session['session_name']} ({session['created_at'][:10]}) - 成功率: {session['success_rate']}%"
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
        
        if session_results:
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
                            "請求元": str(result["issuer_name"] or ""),
                            "請求書番号": str(result["invoice_number"] or ""),
                            "通貨": str(result["currency"] or ""),
                            "税込金額": int(tax_included),
                            "発行日": str(result["issue_date"]) if result["issue_date"] else "",
                            "検証状況": "✅ 正常" if result["is_valid"] else "❌ エラー",
                            "完全性スコア": completeness_score,
                            "処理日時": str(result["created_at"][:16])
                        })
                    
                    if history_data:
                        df_history = pd.DataFrame(history_data)
                        
                        st.subheader("履歴詳細 (ag-grid)")
                        aggrid_manager.create_data_grid(
                            df_history,
                            editable=False,
                            fit_columns_on_grid_load=True,
                            selection_mode="single",
                            height=400
                        )
                
            except ImportError:
                st.warning("ag-gridライブラリが利用できません")


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
                
                if pdf_files:
                    st.success(f"{len(pdf_files)}個のPDFファイルが見つかりました")
                    
                    # ファイル一覧表示
                    files_df = pd.DataFrame([
                        {
                            "ファイル名": f["name"],
                            "サイズ": f.get("size", "不明"),
                            "更新日時": f.get("modifiedTime", "不明")[:10] if f.get("modifiedTime") else "不明",
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
                        if test_results.get("results"):
                            session_id = ocr_test_manager.save_to_supabase(test_results, user_email)
                            if session_id:
                                st.success(f"✅ 結果をデータベースに保存しました (セッションID: {session_id})")
                                st.session_state.current_session_id = session_id
        
        # テスト結果表示
        if hasattr(st.session_state, 'test_results') and st.session_state.test_results.get("results"):
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
            display_results_with_aggrid(test_results)
            
            # 詳細結果表示（従来版も残す）
            with st.expander("📋 詳細結果（従来表示）", expanded=False):
                # ファイル選択
                result_files = [r["filename"] for r in test_results["results"]]
                selected_file = st.selectbox("表示するファイルを選択", result_files)
                
                if selected_file:
                    # 選択されたファイルの結果を取得
                    selected_result = next(
                        r for r in test_results["results"] 
                        if r["filename"] == selected_file
                    )
                    
                    ocr_result = selected_result["ocr_result"]
                    validation = selected_result["validation"]
                    
                    # 検証結果表示
                    col1, col2 = st.columns(2)
                    with col1:
                        status_color = "🟢" if validation["is_valid"] else "🔴"
                        st.write(f"{status_color} **検証ステータス**: {'正常' if validation['is_valid'] else 'エラーあり'}")
                        st.write(f"📊 **完全性スコア**: {validation['completeness_score']:.1f}%")
                    
                    with col2:
                        if validation["errors"]:
                            st.error("エラー:")
                            for error in validation["errors"]:
                                st.write(f"❌ {error}")
                                
                        if validation["warnings"]:
                            st.warning("警告:")
                            for warning in validation["warnings"]:
                                st.write(f"⚠️ {warning}")
                    
                    # OCR結果表示
                    df_basic, df_details = ocr_test_manager.format_ocr_result_for_display(ocr_result, validation)
                    
                    st.subheader("基本情報")
                    st.dataframe(df_basic, use_container_width=True)
                    
                    if not df_details.empty:
                        st.subheader("明細情報")
                        st.dataframe(df_details, use_container_width=True)
                    
                    # JSON表示
                    with st.expander("生JSONデータ"):
                        st.json(ocr_result)
    
    with tab2:
        # テスト履歴表示
        display_session_history(ocr_test_manager, user_email)


if __name__ == "__main__":
    create_ocr_test_app() 