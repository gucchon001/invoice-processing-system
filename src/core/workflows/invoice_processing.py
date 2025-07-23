"""
請求書処理統合ワークフロー

PDF → AI抽出 → DB保存の統合処理を管理するユースケースクラス
"""

from datetime import datetime
from typing import Dict, Any, Optional, Callable
import logging
from core.models.workflow_models import WorkflowStatus, WorkflowProgress, WorkflowResult

logger = logging.getLogger(__name__)


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
            # Step 1: ファイルアップロード（強化版エラーハンドリング）
            self._notify_progress(
                WorkflowStatus.UPLOADING, 
                "ファイルアップロード", 
                10, 
                "Google Driveにファイルをアップロード中..."
            )
            
            try:
                # タイムアウト制御付きでアップロード実行
                logger.info(f"🔄 Google Driveアップロード開始: {filename}")
                
                file_info = self.storage_service.upload_file(
                    file_content=pdf_file_data,
                    filename=filename,
                    folder_id=None,  # デフォルトフォルダ
                    mime_type="application/pdf"
                )
                
                logger.info(f"📤 Google Driveアップロード完了: {file_info}")
                
                if not file_info:
                    raise Exception("ファイルアップロードに失敗しました（戻り値がNone）")
                
                # アップロード成功の進捗通知
                uploaded_filename = file_info.get('filename', filename)
                file_id = file_info.get('file_id', 'unknown')
                
                self._notify_progress(
                    WorkflowStatus.UPLOADING,
                    "ファイルアップロード",
                    30,
                    f"アップロード完了: {uploaded_filename} (ID: {file_id})"
                )
                
                logger.info(f"✅ アップロード成功: {uploaded_filename} -> {file_id}")
                
            except Exception as upload_error:
                logger.error(f"❌ Google Driveアップロードエラー: {upload_error}")
                logger.exception("アップロード詳細エラー:")
                raise Exception(f"Google Driveアップロードに失敗しました: {upload_error}")
            
            # 🚨 超緊急デバッグ（7/22）: 30%直後の即座ログ
            # logger.error(f"🔍 DEBUG: 【キャッシュテスト】30%ログ出力完了 - キャッシュがクリアされていれば このメッセージが表示されます")
            # logger.error(f"🔍 DEBUG: 【キャッシュテスト】ファイル名: {file_info.get('filename', filename)}")
            # logger.error(f"🔍 DEBUG: 【キャッシュテスト】これから40%に進みます")
            
            # Step 2: AI情報抽出（強化版エラーハンドリング）
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "AI情報抽出", 
                40,
                "Gemini APIで請求書情報を抽出中..."
            )
            
            try:
                logger.info(f"🤖 AI情報抽出開始: {filename}")
                
                # プロンプト準備
                from core.services.unified_prompt_manager import UnifiedPromptManager
                prompt_manager = UnifiedPromptManager()
                
                # 請求書抽出用プロンプトを取得
                system_prompt, user_prompt = prompt_manager.format_prompt_for_gemini(
                    "invoice_extractor_prompt", {"filename": filename}
                )
                
                # AI処理実行
                combined_prompt = f"{system_prompt}\n\n{user_prompt}"
                
                extracted_data = self.ai_service.analyze_pdf_content(
                    pdf_file_data,
                    combined_prompt
                )
                
                logger.info(f"🤖 AI情報抽出完了: {extracted_data}")
                
                if not extracted_data:
                    raise Exception("AI情報抽出に失敗しました（戻り値がNone）")
                
            except Exception as ai_error:
                logger.error(f"❌ AI情報抽出エラー: {ai_error}")
                logger.exception("AI処理詳細エラー:")
                raise Exception(f"AI情報抽出に失敗しました: {ai_error}")
            
            # AI処理成功時の進捗通知
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "AI情報抽出",
                70,
                "情報抽出完了",
                details={"extracted_data": extracted_data}
            )
            
            # Step 3: データベース保存（強化版エラーハンドリング）
            self._notify_progress(
                WorkflowStatus.SAVING,
                "データベース保存",
                80,
                "請求書データをデータベースに保存中..."
            )
            
            try:
                logger.info(f"💾 データベース保存開始: {filename}")
                
                # 請求書データの準備
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
                    raise Exception("データベース保存に失敗しました（戻り値がNone）")
                
                invoice_id = save_result.get('id')
                logger.info(f"💾 データベース保存完了: ID={invoice_id}")
                
            except Exception as db_error:
                logger.error(f"❌ データベース保存エラー: {db_error}")
                logger.exception("データベース保存詳細エラー:")
                raise Exception(f"データベース保存に失敗しました: {db_error}")
            
            # Step 4: 完了（強化版）
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self._notify_progress(
                WorkflowStatus.COMPLETED,
                "処理完了",
                100,
                f"請求書処理が完了しました (ID: {invoice_id})",
                details={
                    "invoice_id": invoice_id,
                    "processing_time": processing_time,
                    "extracted_data_keys": list(extracted_data.keys()) if extracted_data else []
                }
            )
            
            logger.info(f"✅ 統合ワークフロー完了: {filename} -> ID={invoice_id}, 処理時間={processing_time:.2f}秒")
            
            # 正常完了時の結果作成
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