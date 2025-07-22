"""
請求書処理統合ワークフロー

PDF → AI抽出 → DB保存の統合処理を管理するユースケースクラス
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """ワークフロー処理状態"""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowProgress:
    """ワークフロー進捗情報"""
    status: WorkflowStatus
    step: str
    progress_percent: int
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowResult:
    """ワークフロー処理結果"""
    success: bool
    invoice_id: Optional[int] = None
    extracted_data: Optional[Dict[str, Any]] = None
    file_info: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    progress_history: Optional[list] = None


class InvoiceProcessingWorkflow:
    """請求書処理統合ワークフロー"""
    
    def __init__(self, 
                 ai_service,
                 storage_service, 
                 database_service,
                 progress_callback: Optional[Callable[[WorkflowProgress], None]] = None):
        """
        Args:
            ai_service: AI情報抽出サービス
            storage_service: ストレージサービス
            database_service: データベースサービス
            progress_callback: 進捗通知コールバック関数
        """
        self.ai_service = ai_service
        self.storage_service = storage_service
        self.database_service = database_service
        self.progress_callback = progress_callback
        self.progress_history = []
    
    def _notify_progress(self, status: WorkflowStatus, step: str, 
                        progress_percent: int, message: str, 
                        details: Optional[Dict[str, Any]] = None):
        """進捗通知"""
        progress = WorkflowProgress(
            status=status,
            step=step,
            progress_percent=progress_percent,
            message=message,
            timestamp=datetime.now(),
            details=details
        )
        
        self.progress_history.append(progress)
        logger.info(f"Workflow Progress: {step} - {message} ({progress_percent}%)")
        
        if self.progress_callback:
            self.progress_callback(progress)
    
    def process_invoice(self, pdf_file_data: bytes, 
                       filename: str, 
                       user_id: str) -> WorkflowResult:
        """
        請求書処理統合ワークフロー実行
        
        Args:
            pdf_file_data: PDFファイルのバイナリデータ
            filename: ファイル名
            user_id: ユーザーID
            
        Returns:
            WorkflowResult: 処理結果
        """
        start_time = datetime.now()
        
        try:
            # Step 1: ファイルアップロード
            self._notify_progress(
                WorkflowStatus.UPLOADING, 
                "ファイルアップロード", 
                10, 
                "Google Driveにファイルをアップロード中..."
            )
            
            file_info = self.storage_service.upload_file(
                file_content=pdf_file_data,
                filename=filename,
                folder_id=None,  # デフォルトフォルダ
                mime_type="application/pdf"
            )
            
            if not file_info:
                raise Exception("ファイルアップロードに失敗しました")
            
            self._notify_progress(
                WorkflowStatus.UPLOADING,
                "ファイルアップロード",
                30,
                f"アップロード完了: {file_info.get('filename', filename)}"
            )
            
            # 🚨 超緊急デバッグ（7/22）: 30%直後の即座ログ
            # logger.error(f"🔍 DEBUG: 【キャッシュテスト】30%ログ出力完了 - キャッシュがクリアされていれば このメッセージが表示されます")
            # logger.error(f"🔍 DEBUG: 【キャッシュテスト】ファイル名: {file_info.get('filename', filename)}")
            # logger.error(f"🔍 DEBUG: 【キャッシュテスト】これから40%に進みます")
            
            # Step 2: AI情報抽出（強化版エラーハンドリング）
            # 40%通知を復活（コールバック側で制御済み）
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "AI情報抽出", 
                40,
                "Gemini APIで請求書情報を抽出中だよ..."
            )
            
            # 🚨 チェックポイント1: 40%ログ出力直後
            # logger.error(f"🔍 CHECKPOINT-1: 40%ログ出力完了（コールバック制御版テスト）")
            
            # デバッグログを簡素化
            # logger.error(f"🔍 DEBUG: AI処理開始 - PDFサイズ: {len(pdf_file_data)} bytes")
            
            # 🚨 チェックポイント2: インポート確認（一時無効化）
            # logger.error(f"🔍 CHECKPOINT-2: インポート確認開始")
            # import gc
            # logger.error(f"🔍 CHECKPOINT-3: gc インポート成功")
            # import sys
            # logger.error(f"🔍 CHECKPOINT-4: sys インポート成功")
            
            # 🚨 チェックポイント5: 変数確認（一時無効化）
            # logger.error(f"🔍 CHECKPOINT-5: pdf_file_data変数確認開始")
            # if pdf_file_data:
            #     logger.error(f"🔍 CHECKPOINT-6: pdf_file_data存在確認 - タイプ: {type(pdf_file_data)}")
            #     logger.error(f"🔍 CHECKPOINT-7: pdf_file_dataサイズ確認開始")
            #     pdf_size_mb = len(pdf_file_data) / 1024 / 1024
            #     logger.error(f"🔍 CHECKPOINT-8: PDFサイズ計算成功: {pdf_size_mb:.1f} MB")
            # else:
            #     logger.error(f"🔍 CHECKPOINT-6: 【警告】pdf_file_dataが存在しません！")
            
            # 🚨 超緊急デバッグ（7/22）: 40%直後の即座ログ（一時無効化）
            # logger.error(f"🔍 DEBUG: 【超重要】40%ログ出力完了 - ここまでは正常")
            # logger.error(f"🔍 DEBUG: 【超重要】現在のメモリ状況をチェック開始")
            
            # メモリ使用量チェック（簡易版）（一時無効化）
            # try:
            #     logger.error(f"🔍 DEBUG: 【超重要】Python GCオブジェクト数: {len(gc.get_objects())}")
            #     
            #     # PDFデータサイズ確認
            #     pdf_size_mb = len(pdf_file_data) / 1024 / 1024 if pdf_file_data else 0
            #     logger.error(f"🔍 DEBUG: 【超重要】PDFファイルサイズ: {pdf_size_mb:.1f} MB")
            #     
            #     # 大きすぎるPDFの早期検出
            #     if pdf_size_mb > 50:
            #         logger.error(f"🔍 DEBUG: 【警告】PDFサイズが大きすぎます: {pdf_size_mb:.1f} MB")
            #     elif pdf_size_mb == 0:
            #         logger.error(f"🔍 DEBUG: 【警告】PDFファイルが空です！")
            #     else:
            #         logger.error(f"🔍 DEBUG: 【正常】PDFサイズは適切です: {pdf_size_mb:.1f} MB")
            #     
            # except Exception as mem_error:
            #     logger.error(f"🔍 DEBUG: 【超重要】メモリチェック失敗: {mem_error}")
            
            # logger.error(f"🔍 DEBUG: 【超重要】メモリチェック完了 - AI抽出処理に進みます")
            
            # 🚨 緊急デバッグ（7/22）: 致命的エラーキャッチ用の広いtry-except
            try:
                # logger.error(f"🔍 DEBUG: 【重要】AI抽出処理開始前 - メモリ使用量確認")
                # logger.error(f"🔍 DEBUG: pdf_file_data存在チェック: {pdf_file_data is not None}")
                # logger.error(f"🔍 DEBUG: pdf_file_dataサイズ: {len(pdf_file_data) if pdf_file_data else 'None'}")
                # logger.error(f"🔍 DEBUG: ai_service存在チェック: {self.ai_service is not None}")
                
                # 🚨 緊急デバッグ（7/22）: AI抽出呼び出し前ログ
                # logger.error(f"🔍 DEBUG: AI抽出サービス呼び出し開始 - ファイルサイズ: {len(pdf_file_data)} bytes")
                
                extracted_data = self.ai_service.extract_pdf_invoice_data(pdf_file_data)
                
                # logger.error(f"🔍 DEBUG: AI抽出サービス呼び出し完了 - 結果: {extracted_data is not None}")
                
                if not extracted_data:
                    # 🚨 緊急修正（7/22）: より詳細なエラー情報を提供
                    self._notify_progress(
                        WorkflowStatus.FAILED,
                        "AI情報抽出エラー",
                        40,
                        "⚠️ PDF解析に失敗しました",
                        details={
                            "error_type": "extraction_failed",
                            "possible_causes": [
                                "PDFファイルが破損している可能性があります",
                                "PDFにページが含まれていない可能性があります", 
                                "Gemini APIがPDF形式を認識できない可能性があります"
                            ],
                            "recommended_actions": [
                                "PDFファイルを確認してください",
                                "異なるPDFファイルで再試行してください",
                                "PDFを再保存または変換してください"
                            ]
                        }
                    )
                    raise Exception("⚠️ AI情報抽出に失敗しました - PDFファイルを確認してください")
                
            except MemoryError as e:
                # logger.error(f"🔍 DEBUG: 【致命的】メモリ不足エラー: {e}")
                detailed_error = f"⚠️ メモリ不足: PDFファイルが大きすぎます - {e}"
                self._notify_progress(
                    WorkflowStatus.FAILED,
                    "AI情報抽出エラー",
                    40,
                    detailed_error,
                    details={"error_type": "memory_error", "original_error": str(e)}
                )
                raise Exception(detailed_error)
                
            except Exception as ai_error:
                # logger.error(f"🔍 DEBUG: 【致命的】AI抽出で予期しないエラー: {ai_error}")
                # logger.error(f"🔍 DEBUG: エラータイプ: {type(ai_error).__name__}")
                # import traceback
                # logger.error(f"🔍 DEBUG: スタックトレース: {traceback.format_exc()}")
                
                error_msg = str(ai_error)
                
                # エラーメッセージの分類と対処法提示
                if "no pages" in error_msg.lower():
                    detailed_error = "⚠️ PDFにページが認識されません - ファイルが破損している可能性があります"
                elif "400" in error_msg and "document" in error_msg.lower():
                    detailed_error = "⚠️ PDF形式エラー - Gemini APIがファイルを処理できません"
                else:
                    detailed_error = f"⚠️ AI処理エラー: {error_msg}"
                
                self._notify_progress(
                    WorkflowStatus.FAILED,
                    "AI情報抽出エラー",
                    40,
                    detailed_error,
                    details={
                        "error_type": "ai_processing_error",
                        "original_error": error_msg
                    }
                )
                
                raise Exception(detailed_error)
            
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "AI情報抽出",
                70,
                "情報抽出完了",
                details={"extracted_data": extracted_data}
            )
            
            # Step 3: データベース保存
            self._notify_progress(
                WorkflowStatus.SAVING,
                "データベース保存",
                80,
                "請求書データをデータベースに保存中..."
            )
            
            # 🔍 デバッグ: テーブルスキーマ確認
            logger.error(f"🔍 DEBUG: データベース保存前にスキーマ確認を実行")
            self.database_service.debug_table_schema('invoices')
            
            # 請求書データの準備（正しいフィールド名使用）
            invoice_record = {
                "file_path": file_info.get("file_id", ""),
                "file_name": filename,
                "extracted_data": extracted_data,
                "created_by": user_id,
                "status": "extracted"
            }
            
            # データベースに保存
            save_result = self.database_service.insert_invoice(invoice_record)
            
            if not save_result:
                raise Exception("データベース保存に失敗しました")
            
            invoice_id = save_result.get('id')
            
            # Step 4: 完了
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self._notify_progress(
                WorkflowStatus.COMPLETED,
                "処理完了",
                100,
                f"請求書処理が完了しました (ID: {invoice_id})",
                details={
                    "invoice_id": invoice_id,
                    "processing_time": processing_time
                }
            )
            
            return WorkflowResult(
                success=True,
                invoice_id=invoice_id,
                extracted_data=extracted_data,
                file_info=file_info,
                processing_time=processing_time,
                progress_history=self.progress_history.copy()
            )
            
        except Exception as e:
            # エラー処理
            error_message = str(e)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"Invoice processing workflow failed: {error_message}")
            
            self._notify_progress(
                WorkflowStatus.FAILED,
                "エラー発生",
                0,
                f"処理に失敗しました: {error_message}",
                details={"error": error_message}
            )
            
            return WorkflowResult(
                success=False,
                error_message=error_message,
                processing_time=processing_time,
                progress_history=self.progress_history.copy()
            )
    
    def get_progress_history(self) -> list:
        """進捗履歴取得"""
        return self.progress_history.copy()
    
    def reset_progress(self):
        """進捗履歴リセット"""
        self.progress_history.clear() 