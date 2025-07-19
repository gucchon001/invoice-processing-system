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
                f"アップロード完了: {file_info['name']}",
                details={"file_info": file_info}
            )
            
            # Step 2: AI情報抽出
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "AI情報抽出", 
                40,
                "Gemini APIで請求書情報を抽出中..."
            )
            
            extracted_data = self.ai_service.extract_pdf_invoice_data(pdf_file_data)
            
            if not extracted_data:
                raise Exception("AI情報抽出に失敗しました")
            
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
            
            # 請求書データの準備
            invoice_record = {
                "supplier_name": extracted_data.get("supplier_name", ""),
                "invoice_number": extracted_data.get("invoice_number", ""),
                "invoice_date": extracted_data.get("invoice_date"),
                "due_date": extracted_data.get("due_date"),
                "total_amount": extracted_data.get("total_amount", 0),
                "tax_amount": extracted_data.get("tax_amount", 0),
                "currency": extracted_data.get("currency", "JPY"),
                "file_path": file_info.get("id", ""),
                "file_name": filename,
                "extracted_data": extracted_data,
                "created_by": user_id,
                "created_at": datetime.now().isoformat(),
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