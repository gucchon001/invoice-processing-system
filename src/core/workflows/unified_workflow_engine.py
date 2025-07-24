"""
統一ワークフローエンジン

全ての請求書処理ワークフローを統一管理するエンジンクラス
重複コードの統合とメンテナンス性の向上を目的とする
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
import uuid

from core.models.workflow_models import WorkflowStatus, WorkflowProgress, WorkflowResult
from core.services.unified_prompt_manager import UnifiedPromptManager, PromptSelector
from infrastructure.ai.gemini_helper import GeminiAPIManager
from infrastructure.storage.google_drive_helper import GoogleDriveManager
from infrastructure.database.database import DatabaseManager
from utils.log_config import get_logger

logger = get_logger(__name__)

class UnifiedWorkflowEngine:
    """統一ワークフローエンジン"""
    
    def __init__(self, 
                 ai_service: GeminiAPIManager,
                 storage_service: GoogleDriveManager,
                 database_service: DatabaseManager,
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
        
        # 統一サービス初期化
        self.prompt_manager = UnifiedPromptManager()
        self.prompt_selector = PromptSelector(self.prompt_manager)
        
        # 処理履歴管理
        self.progress_history = []
        logger.info("UnifiedWorkflowEngine initialized.")

    def _notify_progress(self, status: WorkflowStatus, step: str, 
                        progress_percent: int, message: str, 
                        details: Optional[Dict[str, Any]] = None):
        """統一進捗通知"""
        progress = WorkflowProgress(
            status=status,
            step=step,
            progress_percent=progress_percent,
            message=message,
            timestamp=datetime.now(),
            details=details
        )
        
        self.progress_history.append(progress)
        logger.info(f"統一ワークフロー進捗: {step} - {message} ({progress_percent}%)")
        
        if self.progress_callback:
            self.progress_callback(progress)
    
    def process_single_file(self, 
                           pdf_file_data: bytes, 
                           filename: str, 
                           user_id: str,
                           mode: str = "upload") -> WorkflowResult:
        """
        単一ファイル処理（統一エントリーポイント）
        
        Args:
            pdf_file_data: PDFファイルのバイナリデータ
            filename: ファイル名
            user_id: ユーザーID
            mode: 処理モード（"upload", "test", "batch"）
            
        Returns:
            WorkflowResult: 統一処理結果
        """
        start_time = datetime.now()
        session_id = str(uuid.uuid4())
        
        try:
            logger.info(f"🚀 統一ワークフロー開始: {filename} (モード: {mode})")
            
            # Step 1: 統一ファイルアップロード処理
            file_info = self._unified_file_upload(pdf_file_data, filename)
            
            # Step 2: 統一AI情報抽出処理
            extracted_data = self._unified_ai_extraction(pdf_file_data, filename)
            
            # Step 2.5: 統一データ検証・正規化処理
            validated_data = self._unified_data_validation(extracted_data, filename)
            
            # Step 3: 統一データベース保存処理
            invoice_id = self._unified_database_save(
                file_info, validated_data, filename, user_id, mode
            )
            
            # Step 4: 完了処理
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self._notify_progress(
                WorkflowStatus.COMPLETED,
                "処理完了",
                100,
                f"統一ワークフロー完了 (ID: {invoice_id})",
                details={
                    "session_id": session_id,
                    "invoice_id": invoice_id,
                    "processing_time": processing_time,
                    "mode": mode
                }
            )
            
            logger.info(f"✅ 統一ワークフロー完了: {filename} -> ID={invoice_id}, 時間={processing_time:.2f}秒")
            
            return WorkflowResult(
                success=True,
                invoice_id=invoice_id,
                extracted_data=validated_data,
                file_info=file_info,
                processing_time=processing_time,
                progress_history=self.progress_history.copy()
            )
            
        except Exception as e:
            error_message = str(e)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"❌ 統一ワークフローエラー: {error_message}")
            
            self._notify_progress(
                WorkflowStatus.FAILED,
                "エラー発生",
                0,
                f"処理に失敗しました: {error_message}",
                details={"error": error_message, "session_id": session_id}
            )
            
            return WorkflowResult(
                success=False,
                error_message=error_message,
                processing_time=processing_time,
                progress_history=self.progress_history.copy()
            )
    
    def _unified_file_upload(self, pdf_file_data: bytes, filename: str) -> Dict[str, Any]:
        """統一ファイルアップロード処理"""
        self._notify_progress(
            WorkflowStatus.UPLOADING, 
            "ファイルアップロード", 
            10, 
            "Google Driveにファイルをアップロード中..."
        )
        
        try:
            logger.info(f"📤 統一アップロード開始: {filename} ({len(pdf_file_data)} bytes)")
            
            # Google Drive APIの呼び出し（完全同期処理）
            logger.info("🌐 Google Drive APIサービス取得中...")
            
            if not self.storage_service:
                raise Exception("Google Drive APIサービスが初期化されていません")
            
            logger.info("🌐 Google Drive APIサービス確認完了")
            
            # アップロード実行（タイムアウト制御付き）
            logger.info("📤 ファイルアップロード実行開始...")
            
            file_info = self.storage_service.upload_file(
                file_content=pdf_file_data,
                filename=filename,
                folder_id=None,  # デフォルトフォルダ
                mime_type="application/pdf"
            )
            
            logger.info(f"📤 ファイルアップロード実行完了: {file_info}")
            
            if not file_info:
                raise Exception("Google Drive APIからの戻り値がNoneです")
            
            if not file_info.get('file_id'):
                raise Exception(f"ファイルIDが取得できませんでした: {file_info}")
            
            # 成功時の詳細ログ
            file_id = file_info.get('file_id')
            file_url = file_info.get('file_url', '')
            
            logger.info(f"✅ 統一アップロード成功: {filename}")
            logger.info(f"📊 アップロード結果: ID={file_id}, URL={file_url}")
            
            self._notify_progress(
                WorkflowStatus.UPLOADING,
                "ファイルアップロード",
                30,
                f"アップロード完了: {filename}"
            )
            
            return file_info
            
        except Exception as e:
            error_msg = f"統一ファイルアップロードに失敗しました: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.exception("統一アップロード詳細エラー:")
            
            # エラー時の進捗通知
            self._notify_progress(
                WorkflowStatus.FAILED,
                "ファイルアップロードエラー",
                10,
                f"アップロード失敗: {str(e)}",
                details={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "filename": filename,
                    "file_size": len(pdf_file_data)
                }
            )
            
            raise Exception(error_msg)
    
    def _unified_ai_extraction(self, pdf_file_data: bytes, filename: str) -> Dict[str, Any]:
        """統一AI情報抽出処理"""
        self._notify_progress(
            WorkflowStatus.PROCESSING,
            "AI情報抽出", 
            40,
            "Gemini APIで請求書情報を抽出中..."
        )
        
        try:
            logger.info(f"🤖 統一AI抽出開始: {filename}")
            
            # 統一プロンプト管理システムを使用
            prompt_key = self.prompt_selector.get_recommended_prompt("upload")
            system_prompt, user_prompt = self.prompt_manager.format_prompt_for_gemini(
                prompt_key, {"invoice_image": filename}
            )
            
            # AI処理実行
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            extracted_data = self.ai_service.analyze_pdf_content(
                pdf_file_data,
                combined_prompt
            )
            
            if not extracted_data:
                raise Exception("AI情報抽出に失敗しました")
            
            logger.info(f"🤖 統一AI抽出完了: {list(extracted_data.keys())}")
            
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "AI情報抽出",
                70,
                "情報抽出完了",
                details={"extracted_keys": list(extracted_data.keys())}
            )
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ 統一AI抽出エラー: {e}")
            raise Exception(f"統一AI情報抽出に失敗しました: {e}")
    
    def _unified_data_validation(self, extracted_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """統一データ検証・正規化処理"""
        self._notify_progress(
            WorkflowStatus.PROCESSING,
            "データ検証",
            75,
            "AI抽出データの検証・正規化を実行中..."
        )
        
        try:
            logger.info(f"🔍 統一データ検証開始: {filename}")
            
            # InvoiceValidatorを使用してデータ検証・正規化
            logger.info("📋 InvoiceValidatorインポート開始...")
            from core.services.invoice_validator import InvoiceValidator
            logger.info("📋 InvoiceValidator初期化開始...")
            validator = InvoiceValidator()
            logger.info("✅ InvoiceValidator初期化完了")
            
            # バリデーション実行（データが正規化される）
            logger.info("🔍 バリデーション実行開始...")
            validation_result = validator.validate_invoice_data(extracted_data)
            logger.info("✅ バリデーション実行完了")
            
            # 正規化されたデータ（extracted_dataは参照渡しで更新されている）
            validated_data = extracted_data.copy()
            
            # バリデーション結果をログ出力
            is_valid = validation_result.get('is_valid', False)
            warnings = validation_result.get('warnings', [])
            errors = validation_result.get('errors', [])
            
            logger.info(f"🔍 データ検証完了: valid={is_valid}, warnings={len(warnings)}, errors={len(errors)}")
            
            # 通貨正規化の確認
            original_currency = extracted_data.get('currency')
            final_currency = validated_data.get('currency')
            if original_currency != final_currency:
                logger.info(f"💱 通貨正規化: {original_currency} → {final_currency}")
            else:
                logger.info(f"💱 通貨確認: {original_currency} (変更なし)")
            
            # 警告・エラーの簡易ログ出力
            if warnings:
                logger.warning(f"⚠️ 検証警告({len(warnings)}件): {warnings[:2]}")  # 最初の2件のみ
            if errors:
                logger.error(f"❌ 検証エラー({len(errors)}件): {errors[:2]}")  # 最初の2件のみ
            
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "データ検証",
                77,
                "データ検証・正規化完了",
                details={
                    "is_valid": is_valid,
                    "warnings_count": len(warnings),
                    "errors_count": len(errors),
                    "currency_normalized": original_currency != final_currency
                }
            )
            
            logger.info("✅ 統一データ検証完了、正規化済みデータを返します")
            return validated_data
            
        except Exception as e:
            logger.error(f"❌ 統一データ検証エラー: {e}")
            logger.exception("詳細エラー情報:")  # スタックトレースを出力
            # 検証に失敗しても処理を継続（元データを返す）
            logger.warning("⚠️ データ検証失敗、元のデータで処理を継続します")
            return extracted_data
    
    def _unified_database_save(self, 
                              file_info: Dict[str, Any], 
                              extracted_data: Dict[str, Any], 
                              filename: str, 
                              user_id: str,
                              mode: str) -> str:
        """統一データベース保存処理"""
        self._notify_progress(
            WorkflowStatus.SAVING,
            "データベース保存",
            80,
            "請求書データをデータベースに保存中..."
        )
        
        try:
            logger.info(f"💾 統一DB保存開始: {filename} (モード: {mode})")
            
            # 統一データレコード準備
            invoice_record = {
                "file_id": file_info.get("file_id", ""),  # file_pathからfile_idに修正
                "file_name": filename,
                "extracted_data": extracted_data,
                "created_by": user_id,
                "status": "extracted",
                "processing_mode": mode,
                "issuer_name": extracted_data.get("issuer"),
                "total_amount_tax_included": extracted_data.get("amount_inclusive_tax"),
                "issue_date": extracted_data.get("issue_date"),
                "invoice_number": extracted_data.get("main_invoice_number")
            }
            
            # データベースに保存
            save_result = self.database_service.insert_invoice(invoice_record)
            
            if not save_result:
                raise Exception("データベース保存に失敗しました")
            
            invoice_id = save_result.get('id')
            logger.info(f"💾 統一DB保存完了: ID={invoice_id}")
            
            self._notify_progress(
                WorkflowStatus.SAVING,
                "データベース保存",
                90,
                f"データベース保存完了 (ID: {invoice_id})"
            )
            
            return str(invoice_id)
            
        except Exception as e:
            logger.error(f"❌ 統一DB保存エラー: {e}")
            raise Exception(f"統一データベース保存に失敗しました: {e}")
    
    def process_uploaded_files(self, 
                             uploaded_files, 
                             user_id: str,
                             mode: str = "upload") -> Dict[str, Any]:
        """
        Streamlit uploaded files の直接処理（複数ファイル対応）
        
        Args:
            uploaded_files: Streamlit st.file_uploader から返されるファイルリスト
            user_id: ユーザーID
            mode: 処理モード
            
        Returns:
            バッチ処理結果辞書
        """
        logger.info(f"📤 Streamlitアップロードファイル処理開始: {len(uploaded_files)}件")
        
        try:
            # Streamlit uploaded files を files_data 形式に変換
            files_data = []
            for uploaded_file in uploaded_files:
                # ファイルデータを読み取り
                pdf_data = uploaded_file.read()
                files_data.append({
                    'filename': uploaded_file.name,
                    'data': pdf_data
                })
                logger.info(f"📄 ファイル変換完了: {uploaded_file.name} ({len(pdf_data):,} bytes)")
            
            # 既存のバッチ処理メソッドを呼び出し
            result = self.process_batch_files(files_data, user_id, mode)
            
            logger.info(f"✅ Streamlitアップロードファイル処理完了: {len(uploaded_files)}件")
            return result
            
        except Exception as e:
            logger.error(f"❌ Streamlitアップロードファイル処理エラー: {e}")
            raise Exception(f"アップロードファイル処理に失敗しました: {e}")
    
    def process_batch_files(self, 
                           files_data: List[Dict[str, Any]], 
                           user_id: str,
                           mode: str = "batch") -> Dict[str, Any]:
        """
        バッチファイル処理（統一実装）
        
        Args:
            files_data: ファイルデータのリスト [{'filename': str, 'data': bytes}]
            user_id: ユーザーID
            mode: 処理モード
            
        Returns:
            バッチ処理結果辞書
        """
        start_time = datetime.now()
        session_id = str(uuid.uuid4())
        
        logger.info(f"🔄 統一バッチ処理開始: {len(files_data)}件 (モード: {mode})")
        
        results = []
        successful_files = 0
        
        for i, file_info in enumerate(files_data, 1):
            try:
                self._notify_progress(
                    WorkflowStatus.PROCESSING,
                    "バッチ処理",
                    int((i / len(files_data)) * 80),  # 80%まで使用
                    f"処理中: {file_info['filename']} ({i}/{len(files_data)})"
                )
                
                # 単一ファイル処理を統一エンジンで実行
                result = self.process_single_file(
                    file_info['data'],
                    file_info['filename'],
                    user_id,
                    mode
                )
                
                if result.success:
                    successful_files += 1
                
                results.append({
                    'filename': file_info['filename'],
                    'success': result.success,
                    'invoice_id': result.invoice_id,
                    'extracted_data': result.extracted_data,
                    'error_message': result.error_message,
                    'processing_time': result.processing_time
                })
                
            except Exception as e:
                logger.error(f"❌ ファイル {file_info['filename']} 処理エラー: {e}")
                results.append({
                    'filename': file_info['filename'],
                    'success': False,
                    'error_message': str(e),
                    'processing_time': 0
                })
        
        # バッチ結果集計
        total_files = len(files_data)
        failed_files = total_files - successful_files
        total_processing_time = (datetime.now() - start_time).total_seconds()
        
        self._notify_progress(
            WorkflowStatus.COMPLETED,
            "バッチ処理完了",
            100,
            f"バッチ処理完了: 成功={successful_files}件, 失敗={failed_files}件"
        )
        
        logger.info(f"✅ 統一バッチ処理完了: 成功={successful_files}/{total_files}件, 時間={total_processing_time:.2f}秒")
        
        return {
            'session_id': session_id,
            'total_files': total_files,
            'successful_files': successful_files,
            'failed_files': failed_files,
            'results': results,
            'total_processing_time': total_processing_time,
            'mode': mode
        }
    
    def get_progress_history(self) -> List[WorkflowProgress]:
        """進捗履歴取得"""
        return self.progress_history.copy()
    
    def reset_progress(self):
        """進捗履歴リセット"""
        self.progress_history.clear() 

    def process_ocr_test_from_drive(self, folder_id: str, user_id: str, max_files: int = -1) -> Dict[str, Any]:
        """
        Google Driveの指定フォルダからファイルを取得してOCRテストを実行する

        Args:
            folder_id (str): Google DriveのフォルダID
            user_id (str): 実行ユーザーID
            max_files (int, optional): 処理する最大ファイル数. Defaults to -1 (すべて).

        Returns:
            Dict[str, Any]: process_batch_files と同じ形式のバッチ処理結果
        """
        self._notify_progress(WorkflowStatus.PROCESSING, "OCR_TEST_PREPARATION", 5, f"Google Driveフォルダからファイルリスト取得開始: {folder_id}")

        try:
            # 1. Google Driveからファイル一覧取得
            if not self.storage_service:
                raise ValueError("Storage service (Google Drive) is not configured.")
            
            from utils.ocr_test_helper import OCRTestManager
            ocr_manager = OCRTestManager(self.storage_service, None, None)
            pdf_files = ocr_manager.get_drive_pdfs(folder_id)

            if not pdf_files:
                logger.warning(f"指定フォルダにPDFファイルが見つかりません: {folder_id}")
                return {"error": f"No PDF files found in folder {folder_id}", "results": [], "total_files": 0, "successful_files": 0, "failed_files": 0}

            # 2. ファイル数制限
            if max_files != -1 and len(pdf_files) > max_files:
                pdf_files = pdf_files[:max_files]
            
            self._notify_progress(WorkflowStatus.PROCESSING, "OCR_TEST_PREPARATION", 10, f"{len(pdf_files)}件のPDFファイルをダウンロードします")

            # 3. ファイルダウンロードとデータ準備
            files_data = []
            for i, file_info in enumerate(pdf_files):
                try:
                    progress = 10 + int((i / len(pdf_files)) * 20) # 10%-30%
                    self._notify_progress(WorkflowStatus.PROCESSING, "FILE_DOWNLOAD", progress, f"ファイルダウンロード中 ({i+1}/{len(pdf_files)}): {file_info['name']}")
                    
                    file_data = self.storage_service.download_file(file_info['id'])
                    if file_data:
                        files_data.append({
                            'filename': file_info['name'],
                            'data': file_data
                        })
                    else:
                        logger.warning(f"ファイルダウンロード失敗（データが空）: {file_info['name']}")

                except Exception as e:
                    logger.error(f"ファイル処理エラー（ダウンロード中）: {file_info['name']} - {e}", exc_info=True)
            
            if not files_data:
                logger.error("処理可能なファイルのダウンロードにすべて失敗しました。")
                return {"error": "Failed to download any processable files.", "results": [], "total_files": len(pdf_files), "successful_files": 0, "failed_files": len(pdf_files)}

            # 4. 既存のバッチ処理メソッドを呼び出し
            self._notify_progress(WorkflowStatus.PROCESSING, "BATCH_PROCESSING_START", 30, "AIによる一括解析処理を開始します")
            return self.process_batch_files(
                files_data=files_data,
                user_id=user_id,
                mode="ocr_test"
            )

        except Exception as e:
            logger.error(f"OCRテスト準備フェーズでエラーが発生: {e}", exc_info=True)
            self._notify_progress(WorkflowStatus.FAILED, "OCR_TEST_PREPARATION", 0, f"OCRテスト準備エラー: {e}")
            return {"error": f"An error occurred during OCR test preparation: {e}"} 