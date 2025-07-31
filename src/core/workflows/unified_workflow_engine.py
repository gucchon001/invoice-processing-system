"""
統一ワークフローエンジン

全ての請求書処理ワークフローを統一管理するエンジンクラス
重複コードの統合とメンテナンス性の向上を目的とする
40カラム新機能対応: 外貨換算・承認ワークフロー・freee連携統合
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
import uuid

from core.models.workflow_models import WorkflowStatus, WorkflowProgress, WorkflowResult
from core.services.unified_prompt_manager import UnifiedPromptManager, PromptSelector
from core.services.currency_conversion_service import CurrencyConversionService  # 🆕 v3.0 NEW
from core.services.approval_control_service import ApprovalControlService        # 🆕 v3.0 NEW
from core.services.freee_integration_service import FreeeIntegrationService      # 🆕 v3.0 NEW
from infrastructure.ai.gemini_helper import GeminiAPIManager
from infrastructure.storage.google_drive_helper import GoogleDriveManager
from infrastructure.database.database import DatabaseManager
from utils.log_config import get_logger

logger = get_logger(__name__)

class UnifiedWorkflowEngine:
    """統一ワークフローエンジン（40カラム新機能対応）"""
    
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
        
        # 🆕 40カラム新機能サービス初期化 ★v3.0 NEW★ - エラーハンドリング強化
        try:
            self.currency_service = CurrencyConversionService()      # 外貨換算サービス
            logger.info("✅ CurrencyConversionService 初期化完了")
        except Exception as e:
            logger.warning(f"⚠️ CurrencyConversionService 初期化エラー（機能制限）: {e}")
            self.currency_service = None
            
        try:
            self.approval_service = ApprovalControlService()         # 承認ワークフローサービス  
            logger.info("✅ ApprovalControlService 初期化完了")
        except Exception as e:
            logger.warning(f"⚠️ ApprovalControlService 初期化エラー（機能制限）: {e}")
            self.approval_service = None
            
        try:
            self.freee_service = FreeeIntegrationService()           # freee連携サービス
            logger.info("✅ FreeeIntegrationService 初期化完了")
        except Exception as e:
            logger.warning(f"⚠️ FreeeIntegrationService 初期化エラー（機能制限）: {e}")
            self.freee_service = None
        
        # 処理履歴管理
        self.progress_history = []
        logger.info("UnifiedWorkflowEngine initialized with 40-column features (with error handling).")

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
            
            # 🆕 Step 2.6: 外貨換算処理 ★v3.0 NEW★
            currency_data = self._unified_currency_conversion(validated_data, filename)
            
            # 🆕 Step 2.7: 承認ワークフロー処理 ★v3.0 NEW★
            approval_data = self._unified_approval_workflow(currency_data, filename)
            
            # 🆕 Step 2.8: freee連携準備 ★v3.0 NEW★
            integration_data = self._unified_freee_preparation(approval_data, filename)
            
            # Step 3: 統一データベース保存処理（40カラム完全対応）
            invoice_id = self._unified_database_save(
                file_info, integration_data, filename, user_id, mode
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
            
            # 正規化前の状態を記録
            original_currency = extracted_data.get('currency')
            logger.info(f"🔍 バリデーション前通貨: {original_currency}")
            
            # バリデーション実行（extracted_dataが参照渡しで正規化される）
            logger.info("🔍 バリデーション実行開始...")
            validation_result = validator.validate_invoice_data(extracted_data)
            logger.info("✅ バリデーション実行完了")
            
            # バリデーション後の状態を確認
            final_currency = extracted_data.get('currency')
            logger.info(f"🔍 バリデーション後通貨: {final_currency}")
            
            # 通貨正規化の確認（修正版）
            if original_currency != final_currency:
                logger.info(f"💱 通貨正規化: {original_currency} → {final_currency}")
            else:
                logger.info(f"💱 通貨確認: {final_currency} (変更なし)")
            
            # バリデーション結果をログ出力
            is_valid = validation_result.get('is_valid', False)
            warnings = validation_result.get('warnings', [])
            errors = validation_result.get('errors', [])
            
            logger.info(f"🔍 データ検証完了: valid={is_valid}, warnings={len(warnings)}, errors={len(errors)}")
            
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
            
            # 重要：extracted_dataが既に正規化されているので、そのまま返す
            return extracted_data  # validated_data = extracted_data.copy() ではなく直接返す
            
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
        """統一データベース保存処理（モード別テーブル対応）"""
        self._notify_progress(
            WorkflowStatus.SAVING,
            "データベース保存",
            80,
            "請求書データをデータベースに保存中..."
        )
        
        try:
            logger.info(f"💾 統一DB保存開始: {filename} (モード: {mode})")
            
            # 🎯 モード別保存処理
            if mode in ["ocr_test", "test"]:
                # OCRテスト用データベース保存
                return self._save_to_test_table(file_info, extracted_data, filename, user_id, mode)
            else:
                # 本番用データベース保存
                return self._save_to_production_table(file_info, extracted_data, filename, user_id, mode)
            
        except Exception as e:
            logger.error(f"❌ 統一DB保存エラー: {e}")
            raise
    
    def _save_to_production_table(self, file_info: Dict[str, Any], extracted_data: Dict[str, Any], 
                                 filename: str, user_id: str, mode: str) -> str:
        """本番テーブル（invoices）への保存"""
        logger.info(f"📋 本番テーブル保存: {filename}")
        
        # 🎯 本番用データレコード完全準備（40カラム対応）
        from datetime import timezone, timedelta
        jst = timezone(timedelta(hours=9))
        jst_now = datetime.now(jst).isoformat()
        
        invoice_record = {
            # 🔑 基本管理
            "user_email": user_id,  # RLS対応
            "status": "extracted",
            "uploaded_at": jst_now,
            "created_at": jst_now,
            "updated_at": jst_now,
            
            # 📁 ファイル管理
            "file_name": filename,
            "gdrive_file_id": file_info.get("file_id"),  # Google Drive ID  
            "file_path": file_info.get("file_path"),     # ファイルパス
            "source_type": self._determine_source_type(mode, file_info),  # local/gdrive/gmail
            "gmail_message_id": None,  # Gmail連携時に設定
            "attachment_id": None,     # Gmail連携時に設定
            "sender_email": None,      # Gmail連携時に設定
            
            # 📄 請求書基本情報
            "issuer_name": extracted_data.get("issuer"),
            "recipient_name": extracted_data.get("payer"),
            "main_invoice_number": extracted_data.get("main_invoice_number"),
            "receipt_number": extracted_data.get("receipt_number"),
            "t_number": extracted_data.get("t_number"),
            "issue_date": extracted_data.get("issue_date"),
            "due_date": extracted_data.get("due_date"),
            
            # 💰 金額・通貨情報
            "currency": extracted_data.get("currency"),
            "total_amount_tax_included": extracted_data.get("amount_inclusive_tax"),
            "total_amount_tax_excluded": extracted_data.get("amount_exclusive_tax"),
            "exchange_rate": extracted_data.get("exchange_rate"),
            "jpy_amount": extracted_data.get("jpy_amount"),
            "card_statement_id": None,  # カード明細連携時に設定
            
            # 🤖 AI処理・検証結果
            "extracted_data": extracted_data,
            "raw_response": None,  # 生のAIレスポンス（オプション）
            "key_info": extracted_data.get("key_info"),  # ★ 重要：key_info設定 ★
            "is_valid": True,  # 基本的にはTrue
            "validation_errors": None,  # エラー配列
            "validation_warnings": None,  # 警告配列
            "completeness_score": None,  # 完全性スコア
            "processing_time": None,  # 処理時間
            
            # ✅ 承認ワークフロー（本番専用）
            "approval_status": extracted_data.get("approval_status", "pending"),
            "approved_by": extracted_data.get("approved_by"),
            "approved_at": extracted_data.get("approved_at"),
            
            # 📊 freee連携（本番専用）
            "exported_to_freee": extracted_data.get("exported_to_freee", False),
            "export_date": None,  # freee実際エクスポート時に設定
            "freee_batch_id": extracted_data.get("freee_batch_id")
        }
        
        # 🔍 RLSデバッグログ追加 ★DEBUG★
        logger.info(f"🔍 本番DB Debug - user_email設定: {user_id}")
        logger.info(f"🔍 本番DB Debug - invoice_record keys: {list(invoice_record.keys())}")
        logger.info(f"🔍 本番DB Debug - file_name: {filename}")
        
        # 本番データベースに保存
        save_result = self.database_service.insert_invoice(invoice_record)
        
        if not save_result:
            raise Exception("本番データベース保存に失敗しました")
        
        invoice_id = save_result.get('id')
        logger.info(f"💾 本番DB保存完了: ID={invoice_id}")
        
        self._notify_progress(
            WorkflowStatus.SAVING,
            "本番データベース保存",
            90,
            f"本番データベース保存完了 (ID: {invoice_id})"
        )
        
        return str(invoice_id)
    
    def _save_to_test_table(self, file_info: Dict[str, Any], extracted_data: Dict[str, Any], 
                           filename: str, user_id: str, mode: str) -> str:
        """テスト用テーブル（ocr_test_results）への保存"""
        logger.info(f"🧪 テストテーブル保存: {filename}")
        
        # 🎯 テスト用データレコード完全準備（40カラム対応）
        from datetime import timezone, timedelta
        jst = timezone(timedelta(hours=9))
        jst_now = datetime.now(jst).isoformat()
        
        test_record = {
            # 🔑 基本識別情報
            "user_email": user_id,
            "status": "extracted",
            "uploaded_at": jst_now,
            "created_at": jst_now,
            "updated_at": jst_now,
            
            # 📁 ファイル・データ情報
            "file_name": filename,
            "gdrive_file_id": file_info.get("file_id"),  # Google Drive ID
            "file_path": file_info.get("file_path"),     # ファイルパス
            "source_type": "gdrive",  # OCRテストはGoogle Drive固定
            
            # 📄 請求書基本情報（完全マッピング）
            "issuer_name": extracted_data.get("issuer"),
            "recipient_name": extracted_data.get("payer"),  # 支払者（受取人）
            "main_invoice_number": extracted_data.get("main_invoice_number"),
            "receipt_number": extracted_data.get("receipt_number"),  # 領収書番号
            "t_number": extracted_data.get("t_number"),  # 適格請求書発行事業者登録番号
            "issue_date": extracted_data.get("issue_date"),
            "due_date": extracted_data.get("due_date"),  # 支払期日
            
            # 💰 金額・通貨情報（完全マッピング）
            "currency": extracted_data.get("currency"),  # 通貨情報
            "total_amount_tax_included": extracted_data.get("amount_inclusive_tax"),
            "total_amount_tax_excluded": extracted_data.get("amount_exclusive_tax"),  # 税抜金額
            "exchange_rate": extracted_data.get("exchange_rate"),
            "jpy_amount": extracted_data.get("jpy_amount"),
            
            # 🤖 AI処理・検証結果（完全マッピング）
            "extracted_data": extracted_data,
            "raw_response": None,  # テスト用では未使用
            "key_info": extracted_data.get("key_info"),  # ★ 重要：key_info設定 ★
            "is_valid": True,  # 基本的にはTrue
            "validation_errors": None,  # エラー配列
            "validation_warnings": None,  # 警告配列
            "completeness_score": None,  # 完全性スコア
            "processing_time": None,  # 処理時間（秒）
            
            # 🧪 テスト固有フィールド
            "gemini_model": "gemini-2.5-flash-lite-preview-06-17",
            "test_batch_name": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "session_id": None  # OCRテストセッション管理は後で実装
        }
        
        # 🔍 テストDBデバッグログ
        logger.info(f"🔍 テストDB Debug - user_email設定: {user_id}")
        logger.info(f"🔍 テストDB Debug - test_record keys: {list(test_record.keys())}")
        logger.info(f"🔍 テストDB Debug - file_name: {filename}")
        
        # テスト用データベースに保存
        if hasattr(self.database_service, 'insert_test_result'):
            save_result = self.database_service.insert_test_result(test_record)
        else:
            # フォールバック: 直接SQLで挿入
            save_result = self._insert_test_result_direct(test_record)
        
        if not save_result:
            raise Exception("テストデータベース保存に失敗しました")
        
        result_id = save_result.get('id')
        logger.info(f"💾 テストDB保存完了: ID={result_id}")
        
        # 🔧 明細データもテスト用テーブルに保存
        line_items = extracted_data.get('line_items', [])
        if line_items and isinstance(line_items, list):
            logger.info(f"📋 テスト明細データ保存開始: {len(line_items)}件")
            self._insert_test_line_items(result_id, line_items)
            logger.info(f"✅ テスト明細データ保存完了: {len(line_items)}件")
        else:
            logger.warning(f"⚠️ テスト明細データなし: {type(line_items)} - {line_items}")
        
        self._notify_progress(
            WorkflowStatus.SAVING,
            "テストデータベース保存",
            90,
            f"テストデータベース保存完了 (ID: {result_id})"
        )
        
        return str(result_id)
    
    def _insert_test_result_direct(self, test_record: Dict[str, Any]) -> Dict[str, Any]:
        """テスト用テーブルへの直接挿入（フォールバック）"""
        try:
            # Supabaseクライアントを直接使用
            supabase = self.database_service.supabase
            
            result = supabase.table('ocr_test_results').insert(test_record).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                raise Exception("テスト用テーブル挿入結果が空です")
                
        except Exception as e:
            logger.error(f"❌ テスト用テーブル直接挿入エラー: {e}")
            raise
    
    def _insert_test_line_items(self, result_id: str, line_items: List[Dict[str, Any]]) -> None:
        """テスト用明細テーブル（ocr_test_line_items）への保存"""
        try:
            from datetime import datetime, timezone, timedelta
            jst = timezone(timedelta(hours=9))
            jst_now = datetime.now(jst).isoformat()
            
            # Supabaseクライアントを直接使用
            supabase = self.database_service.supabase
            
            for i, item in enumerate(line_items, 1):
                # テスト明細データ準備
                test_line_item_data = {
                    'result_id': result_id,  # ocr_test_resultsのUUIDを参照
                    'line_number': i,
                    'item_description': str(item.get('description', item.get('item', item.get('product', '')))),
                    'quantity': self._safe_numeric_value(item.get('quantity', item.get('qty'))),
                    'unit_price': self._safe_numeric_value(item.get('unit_price', item.get('price'))),
                    'amount': self._safe_numeric_value(item.get('amount', item.get('total'))),
                    'tax_rate': self._safe_numeric_value(item.get('tax_rate', item.get('tax'))),
                    'created_at': jst_now,
                    'updated_at': jst_now
                }
                
                # Noneや空文字列を除去
                clean_line_data = {k: v for k, v in test_line_item_data.items() if v is not None and v != ''}
                
                # テスト用明細テーブルに挿入
                result = supabase.table('ocr_test_line_items').insert(clean_line_data).execute()
                
                if not result.data:
                    logger.warning(f"⚠️ テスト明細挿入失敗: 行{i}")
                else:
                    logger.debug(f"✅ テスト明細挿入成功: 行{i} - {clean_line_data.get('item_description', 'N/A')}")
                    
        except Exception as e:
            logger.error(f"❌ テスト明細データ挿入エラー: {e}")
    
    def _safe_numeric_value(self, value) -> float:
        """数値を安全に変換（テスト用）"""
        if value is None:
            return None
        try:
            return float(value) if value != '' else None
        except (ValueError, TypeError):
            return None
    
    def _determine_source_type(self, mode: str, file_info: Dict[str, Any]) -> str:
        """処理モードとファイル情報からソースタイプを判定"""
        if mode in ["ocr_test", "test"]:
            return "gdrive"  # OCRテストはGoogle Drive固定
        elif file_info.get("file_id"):
            return "gdrive"  # Google Drive ID があればgdrive
        elif file_info.get("gmail_message_id"):
            return "gmail"   # Gmail Message ID があればgmail
        else:
            return "local"   # デフォルトはlocal
    
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
                    'file_info': result.file_info,  # ★ PDFプレビュー用 file_info 追加 ★
                    'error_message': result.error_message,
                    'processing_time': result.processing_time
                })
                
            except Exception as e:
                logger.error(f"❌ ファイル {file_info['filename']} 処理エラー: {e}")
                results.append({
                    'filename': file_info['filename'],
                    'success': False,
                    'file_info': None,  # ★ エラー時はfile_info無し ★
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

    def process_production_upload_from_drive(self, folder_id: str, user_id: str, max_files: int = -1) -> Dict[str, Any]:
        """
        Google Driveの指定フォルダからファイルを取得して本番データベースにアップロードする

        Args:
            folder_id (str): Google DriveのフォルダID
            user_id (str): 実行ユーザーID
            max_files (int, optional): 処理する最大ファイル数. Defaults to -1 (すべて).

        Returns:
            Dict[str, Any]: process_batch_files と同じ形式のバッチ処理結果
        """
        self._notify_progress(WorkflowStatus.PROCESSING, "PRODUCTION_UPLOAD_PREPARATION", 5, f"Google Driveフォルダからファイルリスト取得開始: {folder_id}")

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
            
            self._notify_progress(WorkflowStatus.PROCESSING, "PRODUCTION_UPLOAD_PREPARATION", 10, f"{len(pdf_files)}件のPDFファイルをダウンロードします")

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

            # 4. 既存のバッチ処理メソッドを呼び出し（本番アップロードモード）
            self._notify_progress(WorkflowStatus.PROCESSING, "BATCH_PROCESSING_START", 30, "AIによる一括解析処理を開始し、本番データベースに保存します")
            return self.process_batch_files(
                files_data=files_data,
                user_id=user_id,
                mode="upload"  # 本番アップロードモード
            )

        except Exception as e:
            logger.error(f"本番アップロード準備フェーズでエラーが発生: {e}", exc_info=True)
            self._notify_progress(WorkflowStatus.FAILED, "PRODUCTION_UPLOAD_PREPARATION", 0, f"本番アップロード準備エラー: {e}")
            return {"error": f"An error occurred during production upload preparation: {e}"} 
    
    # ============================================================
    # 🆕 40カラム新機能処理メソッド ★v3.0 NEW★
    # ============================================================
    
    def _unified_currency_conversion(self, validated_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """統一外貨換算処理（40カラム新機能）
        
        Args:
            validated_data: 検証済みデータ
            filename: ファイル名
            
        Returns:
            Dict: 外貨換算データ追加済みデータ
        """
        try:
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "外貨換算処理",
                75,
                "外貨換算処理中..."
            )
            
            logger.info(f"💱 外貨換算処理開始: {filename}")
            
            # 通貨情報取得
            currency = validated_data.get('currency', 'JPY')
            amount = validated_data.get('amount_inclusive_tax', 0)
            
            # JPYの場合は換算不要
            if currency.upper() == 'JPY':
                logger.info(f"💱 JPY請求書のため換算不要: {filename}")
                validated_data.update({
                    'exchange_rate': 1.0,
                    'jpy_amount': amount,
                    'currency_conversion_status': 'no_conversion_needed'
                })
                return validated_data
            
            # ★ 外貨換算サービスが利用不可の場合はスキップ
            if not self.currency_service:
                logger.warning(f"⚠️ 外貨換算サービス未初期化のためスキップ: {filename}")
                validated_data.update({
                    'exchange_rate': None,
                    'jpy_amount': amount,  # 元の金額を保持
                    'currency_conversion_status': 'service_unavailable'
                })
                return validated_data
            
            # 外貨換算実行
            if amount and amount > 0:
                conversion_result = self.currency_service.convert_to_jpy(amount, currency)
                
                validated_data.update({
                    'exchange_rate': conversion_result['exchange_rate'],
                    'jpy_amount': conversion_result['jpy_amount'],
                    'currency_conversion_status': 'converted',
                    'conversion_timestamp': conversion_result['conversion_timestamp'],
                    'rate_source': conversion_result['source']
                })
                
                logger.info(f"✅ 外貨換算完了: {amount} {currency} → ¥{conversion_result['jpy_amount']:,.2f}")
            else:
                logger.warning(f"⚠️ 金額不明のため外貨換算スキップ: {filename}")
                validated_data.update({
                    'currency_conversion_status': 'skipped_no_amount'
                })
            
            return validated_data
            
        except Exception as e:
            logger.error(f"❌ 外貨換算処理エラー: {e}")
            # エラー時でも処理を継続（換算なしで）
            validated_data.update({
                'currency_conversion_status': 'error',
                'currency_conversion_error': str(e)
            })
            return validated_data
    
    def _unified_approval_workflow(self, currency_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """統一承認ワークフロー処理（40カラム新機能）
        
        Args:
            currency_data: 外貨換算済みデータ
            filename: ファイル名
            
        Returns:
            Dict: 承認ワークフローデータ追加済みデータ
        """
        try:
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "承認ワークフロー処理",
                80,
                "承認要否判定中..."
            )
            
            logger.info(f"✅ 承認ワークフロー処理開始: {filename}")
            
            # ★ 承認ワークフローサービスが利用不可の場合はデフォルト設定
            if not self.approval_service:
                logger.warning(f"⚠️ 承認ワークフローサービス未初期化のためデフォルト設定: {filename}")
                currency_data.update({
                    'approval_status': 'auto_approved',
                    'approved_by': 'system_default',
                    'approved_at': datetime.now().isoformat(),
                    'approval_reason': '承認サービス未初期化のため自動承認'
                })
                return currency_data
            
            # 承認要否評価
            approval_evaluation = self.approval_service.evaluate_approval_requirement(currency_data)
            
            if approval_evaluation['requires_approval']:
                # 承認必要な場合
                approval_level = approval_evaluation['approval_level']
                approver_email = self.approval_service.assign_approver(approval_level)
                
                currency_data.update({
                    'approval_status': 'pending',
                    'approval_level': approval_level,
                    'current_approver': approver_email,
                    'approval_reason': approval_evaluation['reason'],
                    'approval_evaluation': approval_evaluation
                })
                
                logger.info(f"📋 承認必要: レベル={approval_level}, 承認者={approver_email}")
                
                # 承認通知送信（実際の実装では承認者情報を取得）
                # self.approval_service.send_approval_notification(...)
                
            else:
                # 自動承認可能な場合
                currency_data.update({
                    'approval_status': 'auto_approved',
                    'approved_by': 'system',
                    'approved_at': datetime.now().isoformat(),
                    'approval_reason': '自動承認基準を満たす'
                })
                
                logger.info(f"🟢 自動承認: {filename}")
            
            return currency_data
            
        except Exception as e:
            logger.error(f"❌ 承認ワークフロー処理エラー: {e}")
            # エラー時はpendingステータスで保存
            currency_data.update({
                'approval_status': 'pending',
                'approval_error': str(e)
            })
            return currency_data
    
    def _unified_freee_preparation(self, approval_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """統一freee連携準備処理（40カラム新機能）
        
        Args:
            approval_data: 承認ワークフロー済みデータ
            filename: ファイル名
            
        Returns:
            Dict: freee連携準備済みデータ
        """
        try:
            self._notify_progress(
                WorkflowStatus.PROCESSING,
                "freee連携準備",
                85,
                "freee連携データ準備中..."
            )
            
            logger.info(f"📊 freee連携準備開始: {filename}")
            
            # ★ freee連携サービスが利用不可の場合はスキップ
            if not self.freee_service:
                logger.warning(f"⚠️ freee連携サービス未初期化のためスキップ: {filename}")
                approval_data.update({
                    'freee_ready': False,
                    'freee_preparation_status': 'service_unavailable',
                    'exported_to_freee': False
                })
                return approval_data
            
            # 承認済みの場合のみfreee連携準備
            approval_status = approval_data.get('approval_status', 'pending')
            
            if approval_status in ['approved', 'auto_approved']:
                # 承認済み：freee連携準備実行
                try:
                    # freee連携データ準備（実際の連携は別途実行）
                    category = self._detect_expense_category(approval_data)
                    account_mapping = self.freee_service.map_expense_category(category)
                    batch_id = self.freee_service.generate_batch_id()
                    
                    approval_data.update({
                        'freee_ready': True,
                        'freee_batch_id': batch_id,
                        'freee_account_mapping': account_mapping,
                        'freee_category': category,
                        'exported_to_freee': False,  # 実際の連携はまだ
                        'freee_preparation_status': 'ready'
                    })
                    
                    logger.info(f"✅ freee連携準備完了: バッチID={batch_id}, 勘定科目={account_mapping['name']}")
                    
                except Exception as freee_error:
                    logger.warning(f"⚠️ freee連携準備でエラー（処理は継続）: {freee_error}")
                    approval_data.update({
                        'freee_ready': False,
                        'freee_preparation_status': 'error',
                        'freee_preparation_error': str(freee_error)
                    })
            else:
                # 未承認：freee連携は保留
                approval_data.update({
                    'freee_ready': False,
                    'freee_preparation_status': 'pending_approval',
                    'exported_to_freee': False
                })
                
                logger.info(f"📋 未承認のためfreee連携は保留: {filename}")
            
            return approval_data
            
        except Exception as e:
            logger.error(f"❌ freee連携準備エラー: {e}")
            # エラー時でも処理を継続
            approval_data.update({
                'freee_ready': False,
                'freee_preparation_status': 'error',
                'freee_preparation_error': str(e)
            })
            return approval_data
    
    def _detect_expense_category(self, invoice_data: Dict[str, Any]) -> str:
        """経費カテゴリ推定（内部ヘルパー）
        
        Args:
            invoice_data: 請求書データ
            
        Returns:
            str: 推定カテゴリ
        """
        # ★ freee連携サービスが利用不可の場合はデフォルトカテゴリ
        if not self.freee_service:
            return 'general'
            
        # FreeeIntegrationService の _detect_expense_category を活用
        return self.freee_service._detect_expense_category(invoice_data) 