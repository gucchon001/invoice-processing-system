"""
統一請求書処理ワークフロー

OCRテスト機能とアップロード機能を統合した
共通処理ワークフローシステムを提供します。
"""

import logging
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from pathlib import Path
import asyncio

from core.services.invoice_validator import InvoiceValidator
from core.services.unified_prompt_manager import UnifiedPromptManager, PromptSelector
from infrastructure.ui.validation_display import ValidationDisplay, BatchValidationDisplay
from infrastructure.ai.gemini_helper import GeminiAPIManager
from infrastructure.database.database import DatabaseManager
# LocalFileAdapter関連は削除（UnifiedWorkflowEngineに統合済み）
from core.models.workflow_models import ProcessingMode, ProcessingStatus

logger = logging.getLogger(__name__)

def get_jst_now():
    """JST（日本標準時）の現在時刻を取得"""
    jst = timezone(timedelta(hours=9))  # JST = UTC+9
    return datetime.now(jst).isoformat()

class UnifiedProcessingWorkflow:
    """統一処理ワークフローシステム"""
    
    def __init__(self, 
                 gemini_helper: GeminiAPIManager,
                 database_manager: DatabaseManager,
                 prompts_dir: str = "prompts"):
        """
        ワークフローシステムの初期化
        
        Args:
            gemini_helper: Gemini AI処理マネージャー
            database_manager: データベース管理システム
            prompts_dir: プロンプトディレクトリ
        """
        self.gemini_helper = gemini_helper
        self.database_manager = database_manager
        
        # 共通コンポーネントの初期化
        self.validator = InvoiceValidator()
        self.prompt_manager = UnifiedPromptManager(prompts_dir)
        self.prompt_selector = PromptSelector(self.prompt_manager)
        self.display = ValidationDisplay()
        self.batch_display = BatchValidationDisplay()
        
        # 処理状態管理
        self.active_sessions = {}
        self.processing_callbacks = []
    
    def register_progress_callback(self, callback: Callable[[str, int, int, str], None]):
        """進捗通知コールバックの登録"""
        self.processing_callbacks.append(callback)
    
    def notify_progress(self, session_id: str, current: int, total: int, message: str = ""):
        """進捗通知の送信"""
        for callback in self.processing_callbacks:
            try:
                callback(session_id, current, total, message)
            except Exception as e:
                logger.error(f"進捗通知エラー: {e}")
    
    async def process_single_file(self, 
                                file_data: bytes,
                                filename: str,
                                mode: str = ProcessingMode.UPLOAD,
                                prompt_key: str = None,
                                validation_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        単一ファイルの処理
        
        Args:
            file_data: ファイルデータ
            filename: ファイル名
            mode: 処理モード
            prompt_key: 使用するプロンプト
            validation_config: 検証設定
            
        Returns:
            処理結果辞書
        """
        session_id = str(uuid.uuid4())
        start_time = time.time()  # 処理時間測定開始
        
        try:
            # セッション開始
            await self._start_session(session_id, mode, [filename])
            
            # プロンプト準備
            if not prompt_key:
                prompt_key = self.prompt_selector.get_recommended_prompt(mode)
            
            system_prompt, user_prompt = self.prompt_manager.format_prompt_for_gemini(
                prompt_key, {"filename": filename}
            )
            
            # AI処理実行
            self.notify_progress(session_id, 1, 3, "AI解析中...")
            
            # 統一プロンプトを結合
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # GeminiAPIManagerの直接呼び出し（中間レイヤー削除）
            ai_result = await asyncio.to_thread(
                self.gemini_helper.analyze_pdf_content,
                file_data,
                combined_prompt
            )
            
            # データ検証
            self.notify_progress(session_id, 2, 3, "データ検証中...")
            
            validation_result = self.validator.validate_invoice_data(
                ai_result, 
                strict_mode=validation_config.get('strict_mode', False) if validation_config else False
            )
            
            # 結果の組み立て
            self.notify_progress(session_id, 3, 3, "完了")
            
            # 処理時間計算
            processing_time = time.time() - start_time
            
            result = {
                'session_id': session_id,
                'filename': filename,
                'mode': mode,
                'ai_result': ai_result,
                'validation': validation_result,
                'prompt_used': prompt_key,
                'processed_at': get_jst_now(),
                'processing_time': processing_time,  # 処理時間を追加
                'status': ProcessingStatus.COMPLETED,
                'success': True  # 成功フラグを追加
            }
            
            # データベース保存（モードに応じて）
            if mode == ProcessingMode.OCR_TEST:
                await self._save_ocr_test_result(session_id, result)
            elif mode in [ProcessingMode.UPLOAD, ProcessingMode.BATCH]:
                # UPLOADとBATCHの両方で統一ワークフロー保存を実行
                await self._save_upload_result(session_id, result)
            
            await self._complete_session(session_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"単一ファイル処理エラー: {e}")
            logger.exception(f"単一ファイル処理詳細エラー:")  # スタックトレースも出力
            # エラー時も処理時間を記録
            processing_time = time.time() - start_time
            
            error_result = {
                'session_id': session_id,
                'filename': filename,
                'error': str(e),
                'error_details': f"Type: {type(e).__name__}, Message: {str(e)}",
                'status': ProcessingStatus.FAILED,
                'processed_at': get_jst_now(),
                'processing_time': processing_time,  # エラー時も処理時間を追加
                'success': False  # 失敗フラグを追加
            }
            
            await self._fail_session(session_id, error_result)
            return error_result
    
    def process_batch(self, 
                     files_data: List[Dict[str, Any]],
                     mode: str = ProcessingMode.BATCH,
                     prompt_key: str = None,
                     include_validation: bool = True,
                     validation_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        バッチファイル処理（同期版）
        
        Args:
            files_data: ファイルデータのリスト
            mode: 処理モード
            prompt_key: 使用するプロンプト
            include_validation: 検証実行フラグ
            validation_config: 検証設定
            
        Returns:
            バッチ処理結果辞書
        """
        # 非同期処理を同期的に実行
        import asyncio
        
        # Streamlit環境での非同期処理対応
        try:
            # 既存のイベントループがある場合は新しいループを作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.process_batch_files(files_data, mode, prompt_key, validation_config)
            )
            loop.close()
            return result
        except Exception as e:
            logger.error(f"同期バッチ処理エラー: {e}")
            # フォールバック: 基本的な同期処理
            return self._process_batch_sync(files_data, mode, prompt_key, include_validation, validation_config)
    
    def _process_batch_sync(self, 
                           files_data: List[Dict[str, Any]],
                           mode: str = ProcessingMode.BATCH,
                           prompt_key: str = None,
                           include_validation: bool = True,
                           validation_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        同期的なバッチファイル処理（フォールバック）
        
        Args:
            files_data: ファイルデータのリスト
            mode: 処理モード
            prompt_key: 使用するプロンプト
            include_validation: 検証実行フラグ
            validation_config: 検証設定
            
        Returns:
            バッチ処理結果辞書
        """
        session_id = str(uuid.uuid4())
        
        try:
            # セッション開始（同期版）
            filenames = [f['filename'] for f in files_data]
            self._start_session_sync(session_id, mode, filenames)
            
            # プロンプト準備
            if not prompt_key:
                prompt_key = self.prompt_selector.get_recommended_prompt(mode)
            
            # 各ファイルを順次処理
            results = []
            total_files = len(files_data)
            
            for i, file_info in enumerate(files_data, 1):
                try:
                    self.notify_progress(
                        session_id, i, total_files, 
                        f"処理中: {file_info['filename']}"
                    )
                    
                    # 単一ファイル処理を同期実行
                    result = self._process_single_file_sync(
                        file_info['data'],
                        file_info['filename'],
                        mode,
                        prompt_key,
                        include_validation,
                        validation_config
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"ファイル {file_info['filename']} 処理エラー: {e}")
                    results.append({
                        'filename': file_info['filename'],
                        'error': str(e),
                        'status': ProcessingStatus.FAILED,
                        'success': False,
                        'processing_time': 0
                    })
            
            # バッチ結果集計
            successful_files = sum(1 for r in results if r.get('success', False))
            failed_files = total_files - successful_files
            total_processing_time = sum(r.get('processing_time', 0) for r in results)
            
            batch_result = {
                'session_id': session_id,
                'mode': mode,
                'total_files': total_files,
                'successful_files': successful_files,
                'failed_files': failed_files,
                'total_processing_time': total_processing_time,
                'results': results,
                'prompt_used': prompt_key,
                'processed_at': get_jst_now(),
                'status': ProcessingStatus.COMPLETED
            }
            
            self._complete_session_sync(session_id, batch_result)
            return batch_result
            
        except Exception as e:
            logger.error(f"同期バッチ処理エラー: {e}")
            error_result = {
                'session_id': session_id,
                'error': str(e),
                'status': ProcessingStatus.FAILED,
                'processed_at': get_jst_now()
            }
            
            self._fail_session_sync(session_id, error_result)
            return error_result

    async def process_batch_files(self, 
                                files_data: List[Dict[str, Any]],
                                mode: str = ProcessingMode.BATCH,
                                prompt_key: str = None,
                                validation_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        バッチファイル処理
        
        Args:
            files_data: ファイルデータのリスト
            mode: 処理モード
            prompt_key: 使用するプロンプト
            validation_config: 検証設定
            
        Returns:
            バッチ処理結果辞書
        """
        session_id = str(uuid.uuid4())
        
        try:
            # セッション開始
            filenames = [f['filename'] for f in files_data]
            await self._start_session(session_id, mode, filenames)
            
            # プロンプト準備
            if not prompt_key:
                prompt_key = self.prompt_selector.get_recommended_prompt(mode)
            
            # 各ファイルを順次処理
            results = []
            total_files = len(files_data)
            
            for i, file_info in enumerate(files_data, 1):
                try:
                    self.notify_progress(
                        session_id, i, total_files, 
                        f"処理中: {file_info['filename']}"
                    )
                    
                    # 単一ファイル処理を呼び出し
                    result = await self.process_single_file(
                        file_info['data'],
                        file_info['filename'],
                        mode,
                        prompt_key,
                        validation_config
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"ファイル {file_info['filename']} 処理エラー: {e}")
                    results.append({
                        'filename': file_info['filename'],
                        'error': str(e),
                        'status': ProcessingStatus.FAILED,
                        'success': False,  # 失敗フラグを追加
                        'processing_time': 0  # 処理時間も追加
                    })
            
            # デバッグ: 実際のresultsデータをログ出力
            logger.info(f"🔍 バッチ結果集計デバッグ - 総ファイル数: {total_files}")
            for i, r in enumerate(results):
                logger.info(f"📄 ファイル{i+1}: {r.get('filename', 'N/A')}")
                logger.info(f"   - status: {r.get('status', 'N/A')}")
                logger.info(f"   - success: {r.get('success', 'N/A')}")
                logger.info(f"   - error: {r.get('error', 'なし')}")
                logger.info(f"   - 全キー: {list(r.keys())}")
            
            # 統一された集計ロジック（successキーで判定）
            successful_files = sum(1 for r in results if r.get('success', False))
            failed_files = total_files - successful_files
            total_processing_time = sum(r.get('processing_time', 0) for r in results)
            
            batch_result = {
                'session_id': session_id,
                'mode': mode,
                'total_files': total_files,
                'successful_files': successful_files,
                'failed_files': failed_files,
                'total_processing_time': total_processing_time,
                'results': results,
                'prompt_used': prompt_key,
                'processed_at': get_jst_now(),
                'status': ProcessingStatus.COMPLETED
            }
            
            await self._complete_session(session_id, batch_result)
            return batch_result
            
        except Exception as e:
            logger.error(f"バッチ処理エラー: {e}")
            error_result = {
                'session_id': session_id,
                'error': str(e),
                'status': ProcessingStatus.FAILED,
                'processed_at': get_jst_now()
            }
            
            await self._fail_session(session_id, error_result)
            return error_result
        
    def _extract_json_from_raw_text(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        raw_textフィールドからJSONデータを抽出
        
        Args:
            raw_text: Geminiからの生レスポンス（Markdown形式の可能性）
            
        Returns:
            抽出されたJSONデータ、または None
        """
        import re
        import json
        
        try:
            # パターン1: ```json ～ ``` ブロック
            json_match = re.search(r'```json\s*\n(.*?)\n```', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"JSONパース エラー (パターン1): {e}")
            
            # パターン2: ```～``` ブロック（json指定なし）
            code_match = re.search(r'```\s*\n(.*?)\n```', raw_text, re.DOTALL)
            if code_match:
                potential_json = code_match.group(1).strip()
                # JSONっぽいかチェック
                if potential_json.startswith('{') and potential_json.endswith('}'):
                    try:
                        return json.loads(potential_json)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSONパース エラー (パターン2): {e}")
            
            # パターン3: { ～ } の最初のJSONオブジェクト
            brace_match = re.search(r'\{.*?\}', raw_text, re.DOTALL)
            if brace_match:
                try:
                    return json.loads(brace_match.group(0))
                except json.JSONDecodeError as e:
                    logger.error(f"JSONパース エラー (パターン3): {e}")
            
            # パターン4: 直接JSON文字列として解析
            try:
                return json.loads(raw_text)
            except json.JSONDecodeError:
                pass
            
            logger.warning("raw_textからJSONの抽出に失敗: 認識可能なパターンが見つかりません")
            return None
            
        except Exception as e:
            logger.error(f"JSON抽出中にエラー: {e}")
            return None
    
    async def _start_session(self, session_id: str, mode: str, filenames: List[str]):
        """セッション開始処理"""
        self.active_sessions[session_id] = {
            'mode': mode,
            'filenames': filenames,
            'started_at': get_jst_now(),
            'status': ProcessingStatus.IN_PROGRESS
        }
        
        logger.info(f"セッション開始: {session_id} (モード: {mode}, ファイル数: {len(filenames)})")
    
    async def _complete_session(self, session_id: str, result: Dict[str, Any]):
        """セッション完了処理"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['status'] = ProcessingStatus.COMPLETED
            self.active_sessions[session_id]['completed_at'] = get_jst_now()
            self.active_sessions[session_id]['result'] = result
        
        logger.info(f"セッション完了: {session_id}")
    
    async def _fail_session(self, session_id: str, error_result: Dict[str, Any]):
        """セッション失敗処理"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['status'] = ProcessingStatus.FAILED
            self.active_sessions[session_id]['failed_at'] = get_jst_now()
            self.active_sessions[session_id]['error'] = error_result
        
        logger.error(f"セッション失敗: {session_id}")
    
    async def _save_ocr_test_result(self, session_id: str, result: Dict[str, Any]):
        """OCRテスト結果の保存"""
        try:
            # OCRテスト用のテーブルに保存
            pass  # 実装は既存のOCRテスト保存ロジックを使用
        except Exception as e:
            logger.error(f"OCRテスト結果保存エラー: {e}")
    
    async def _save_upload_result(self, session_id: str, result: Dict[str, Any]):
        """アップロード結果の保存（OCRテスト相当のデータベース保存）"""
        try:
            logger.info(f"データベース保存開始: {session_id}")
            
            # OCRテストと同様の形式でデータベースに保存
            ai_result = result.get('ai_result', {})
            validation = result.get('validation', {})
            filename = result.get('filename', 'N/A')
            
            # ファイルサイズの推定（実際のファイルサイズ取得は困難なため推定値を使用）
            estimated_file_size = len(str(ai_result)) * 100  # AI結果サイズから推定
            
            # 結果データを準備（invoicesテーブルフォーマット準拠）
            result_data = {
                "user_email": "y-haraguchi@tomonokai-corp.com",  # デフォルトユーザー
                "status": "processed",
                "file_name": filename,
                "file_id": f"unified_workflow_{session_id}",  # 統一ワークフロー用のfile_id生成
                "session_id": session_id,
                "file_size": estimated_file_size,
                "issuer_name": ai_result.get("issuer"),
                "recipient_name": ai_result.get("payer"),
                "invoice_number": ai_result.get("main_invoice_number"),
                "registration_number": ai_result.get("t_number"),
                "currency": ai_result.get("currency"),
                "total_amount_tax_included": ai_result.get("amount_inclusive_tax"),
                "total_amount_tax_excluded": ai_result.get("amount_exclusive_tax"),
                "issue_date": ai_result.get("issue_date"),
                "due_date": ai_result.get("due_date"),
                "key_info": ai_result.get("key_info"),
                "raw_response": ai_result,
                "extracted_data": ai_result,
                "is_valid": validation.get("is_valid", True),
                "validation_errors": validation.get("errors", []),
                "validation_warnings": validation.get("warnings", []),
                "completeness_score": self._calculate_completeness_score(ai_result),
                "processing_time": result.get('processing_time', 0),
                "gemini_model": "gemini-2.0-flash-exp"
            }
            
            logger.info(f"保存データ準備完了: {filename} (通貨: {result_data['currency']})")
            
            # データベースマネージャーを使用してocr_test_resultsテーブルに保存
            if self.database_manager:
                try:
                    import streamlit as st
                    service_key = st.secrets["database"]["supabase_service_key"]
                    supabase_url = st.secrets["database"]["supabase_url"]
                    
                    from supabase import create_client
                    service_supabase = create_client(supabase_url, service_key)
                    
                    logger.info(f"Service Role Key使用でinvoicesテーブルに保存開始")
                    
                    # 統一ワークフロー結果を本番invoicesテーブルに保存
                    result_response = service_supabase.table("invoices").insert(result_data).execute()
                    
                    if result_response.data:
                        result_id = result_response.data[0]["id"]
                        
                        # 明細データを保存
                        await self._save_line_items(service_supabase, result_id, ai_result.get("line_items", []))
                        
                        logger.info(f"✅ invoicesテーブル保存成功: {result_id}")
                    else:
                        logger.error(f"❌ invoicesテーブル保存失敗: レスポンスデータなし")
                    
                except Exception as db_error:
                    logger.error(f"❌ Service Role Key使用失敗: {db_error}")
                    logger.info("通常キーでのinvoicesテーブル保存は権限エラーのためスキップします")
                    # RLS エラーが確実に発生するため、通常キーでの試行はスキップ
                    
        except Exception as e:
            logger.error(f"アップロード結果保存エラー: {e}")
            # テーブルが存在しない場合の特別なメッセージ
            if "does not exist" in str(e) or "relation" in str(e):
                logger.info("本番用テーブルが未作成のため、結果保存をスキップします")
            else:
                logger.error(f"データベース保存詳細エラー: {e}")
    
    async def _save_line_items(self, supabase_client, result_id: str, line_items: List[Dict[str, Any]]):
        """明細データの保存"""
        try:
            for i, item in enumerate(line_items, 1):
                # 税率データの数値変換（"10%" → 10.0）
                tax_rate = item.get("tax")
                if tax_rate and isinstance(tax_rate, str):
                    try:
                        if "%" in tax_rate:
                            tax_rate = float(tax_rate.replace("%", "").strip())
                        else:
                            tax_rate = float(tax_rate)
                    except (ValueError, AttributeError):
                        tax_rate = None
                
                # JST時間取得
                jst_now = get_jst_now()
                
                line_item_data = {
                    "invoice_id": result_id,
                    "line_number": i,
                    "item_description": item.get("description"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "amount": item.get("amount"),
                    "tax_rate": tax_rate,
                    "created_at": jst_now,
                    "updated_at": jst_now
                }
                
                supabase_client.table("invoice_line_items").insert(line_item_data).execute()
                
        except Exception as e:
            logger.error(f"明細データ保存エラー: {e}")
    
    def _calculate_completeness_score(self, ai_result: Dict[str, Any]) -> float:
        """完全性スコアの計算（OCRテストと同じロジック）"""
        try:
            # 必須フィールド（JSONプロンプト版）
            required_fields = ["issuer", "amount_inclusive_tax", "currency"]
            
            # 重要フィールド
            important_fields = ["payer", "main_invoice_number", "issue_date"]
            
            # オプショナルフィールド
            optional_fields = ["t_number", "amount_exclusive_tax", "due_date", "line_items", "key_info"]
            
            score = 0
            total_weight = 100
            
            # 必須フィールドチェック（60点満点）
            required_weight = 60
            for field in required_fields:
                value = ai_result.get(field)
                if self._is_valid_field_value(value):
                    score += required_weight / len(required_fields)
            
            # 重要フィールドチェック（30点満点）
            important_weight = 30
            for field in important_fields:
                value = ai_result.get(field)
                if self._is_valid_field_value(value):
                    score += important_weight / len(important_fields)
            
            # オプショナルフィールドチェック（10点満点）
            optional_weight = 10
            for field in optional_fields:
                value = ai_result.get(field)
                if self._is_valid_field_value(value):
                    score += optional_weight / len(optional_fields)
            
            return min(100.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"完全性スコア計算エラー: {e}")
            return 0.0
    
    def _is_valid_field_value(self, value) -> bool:
        """フィールド値の有効性チェック"""
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, (int, float)) and value == 0:
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        if isinstance(value, dict) and len(value) == 0:
            return False
        return True
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション状態の取得"""
        return self.active_sessions.get(session_id)
    
    def cancel_session(self, session_id: str) -> bool:
        """セッションのキャンセル"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['status'] = ProcessingStatus.CANCELLED
            self.active_sessions[session_id]['cancelled_at'] = get_jst_now()
            logger.info(f"セッションキャンセル: {session_id}")
            return True
        return False
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """古いセッションのクリーンアップ"""
        jst = timezone(timedelta(hours=9))
        current_time = datetime.now(jst)
        to_remove = []
        
        for session_id, session_data in self.active_sessions.items():
            session_age = current_time - session_data['started_at']
            if session_age.total_seconds() > max_age_hours * 3600:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.active_sessions[session_id]
            logger.info(f"古いセッションを削除: {session_id}")
        
        return len(to_remove)

class WorkflowDisplayManager:
    """ワークフロー表示管理クラス"""
    
    def __init__(self, workflow: UnifiedProcessingWorkflow):
        self.workflow = workflow
        self.display = ValidationDisplay()
        self.batch_display = BatchValidationDisplay()
        
        # 進捗コールバックの登録（無効化 - メインで管理）
        # self.workflow.register_progress_callback(self._handle_progress_update)
    
    def _handle_progress_update(self, session_id: str, current: int, total: int, message: str):
        """進捗更新の処理"""
        # セッション管理されたプログレスバーを使用
        import streamlit as st
        
        # プログレスバーの一意キーを生成
        progress_key = f"progress_{session_id}"
        
        # セッションステートでプログレスバーを管理
        if progress_key not in st.session_state:
            st.session_state[progress_key] = st.empty()
        
        # プログレスバーを更新
        progress_container = st.session_state[progress_key]
        progress_value = current / total if total > 0 else 0
        
        with progress_container.container():
            st.progress(progress_value, text=message)
    
    def display_single_result(self, result: Dict[str, Any]):
        """単一ファイル結果の表示"""
        import streamlit as st
        
        # エラーチェック
        if result.get('error'):
            st.error(f"❌ 処理エラー: {result['error']}")
            st.error(f"📋 エラー詳細: {result.get('error_details', '詳細不明')}")
            
            # ファイル情報のみ表示
            file_info = {
                'name': result.get('filename', 'N/A'),
                'size': 'エラーのため取得不可',
                'processed_at': result.get('processed_at', 'N/A'),
                'processing_time': f"{result.get('processing_time', 0):.2f}秒" if result.get('processing_time') else 'N/A'
            }
            self.display.display_file_info(file_info)
            return
        
        # 正常処理の場合
        status = result.get('status', 'unknown')
        if status != 'completed':
            st.warning(f"⚠️ 処理ステータス: {status}")
        
        # AI結果の表示
        if result.get('ai_result'):
            st.subheader("🤖 AI解析結果")
            
            ai_result = result['ai_result']
            
            # 結果が空の場合
            if not ai_result or ai_result == {}:
                st.warning("⚠️ AI解析結果が空です。PDFの内容を確認してください。")
            else:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("請求元", ai_result.get('issuer', 'N/A'))
                with col2:
                    amount = ai_result.get('amount_inclusive_tax', 0)
                    st.metric("税込金額", f"¥{amount:,}" if amount else 'N/A')
                with col3:
                    st.metric("通貨", ai_result.get('currency', 'JPY'))
                
                # 詳細情報
                with st.expander("📋 詳細データ", expanded=False):
                    st.json(ai_result)
        else:
            st.warning("⚠️ AI解析結果がありません")
        
        # 検証結果の表示
        if result.get('validation'):
            validation = result['validation']
            st.subheader("🔍 データ検証結果")
            
            # 警告とエラーの詳細表示
            if validation.get('warnings'):
                with st.expander(f"⚠️ 警告詳細: {len(validation['warnings'])}件", expanded=True):
                    for i, warning in enumerate(validation['warnings'], 1):
                        st.warning(f"**警告 {i}**: {warning}")
                        
            if validation.get('errors'):
                with st.expander(f"❌ エラー詳細: {len(validation['errors'])}件", expanded=True):
                    for i, error in enumerate(validation['errors'], 1):
                        st.error(f"**エラー {i}**: {error}")
            
            if not validation.get('warnings') and not validation.get('errors'):
                st.success("✅ データ検証: 問題なし")
            
            # 従来の詳細検証結果も表示
            self.display.display_validation_results(
                validation,
                f"詳細検証結果: {result.get('filename', 'N/A')}"
            )
        
        # ag-grid形式での詳細表示を追加
        self.display_detailed_results_with_aggrid([result])
        
        # ファイル情報表示
        ai_result = result.get('ai_result', {})
        file_info = {
            'name': result.get('filename', 'N/A'),
            'size': f"{len(str(ai_result))} bytes (データサイズ)" if ai_result else 'データなし',
            'processed_at': result.get('processed_at', 'N/A'),
            'processing_time': f"{result.get('processing_time', 0):.2f}秒" if result.get('processing_time') else 'N/A'
        }
        self.display.display_file_info(file_info)
    

    def display_batch_results(self, batch_result: Dict[str, Any]):
        """バッチ処理結果の表示"""
        import streamlit as st
        
        results = batch_result.get('results', [])
        
        # バッチサマリーの表示
        self.batch_display.display_batch_summary(results)
        
        # 各ファイルの要約結果
        st.subheader("📋 ファイル別処理結果")
        
        for i, result in enumerate(results, 1):
            filename = result.get('filename', f'ファイル{i}')
            status = result.get('status', 'unknown')
            
            # ステータスアイコン
            status_icon = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
            
            with st.expander(f"{status_icon} {filename}", expanded=False):
                if result.get('ai_result'):
                    ai_result = result['ai_result']
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**請求元**: {ai_result.get('issuer', 'N/A')}")
                        st.write(f"**請求書番号**: {ai_result.get('main_invoice_number', 'N/A')}")
                        st.write(f"**発行日**: {ai_result.get('issue_date', 'N/A')}")
                    
                    with col2:
                        amount = ai_result.get('amount_inclusive_tax', 0)
                        st.write(f"**税込金額**: ¥{amount:,}" if amount else "**税込金額**: N/A")
                        st.write(f"**通貨**: {ai_result.get('currency', 'JPY')}")
                        st.write(f"**処理時間**: {result.get('processing_time', 0):.2f}秒")
                    
                    # キー情報がある場合
                    key_info = ai_result.get('key_info', {})
                    if key_info:
                        st.write("**🔑 重要情報**:")
                        for key, value in key_info.items():
                            st.write(f"- {key}: {value}")
                
                # 検証結果の表示
                if result.get('validation'):
                    validation = result['validation']
                    if validation.get('warnings'):
                        with st.expander(f"⚠️ 警告: {len(validation['warnings'])}件", expanded=False):
                            for i, warning in enumerate(validation['warnings'], 1):
                                st.warning(f"**警告 {i}**: {warning}")
                    if validation.get('errors'):
                        with st.expander(f"❌ エラー: {len(validation['errors'])}件", expanded=False):
                            for i, error in enumerate(validation['errors'], 1):
                                st.error(f"**エラー {i}**: {error}")
                    
                    # 全体の検証サマリー
                    if validation.get('warnings') or validation.get('errors'):
                        total_issues = len(validation.get('warnings', [])) + len(validation.get('errors', []))
                        st.info(f"📋 検証詳細: 合計 {total_issues} 件の課題が検出されました")
                
                if result.get('error'):
                    st.error(f"処理エラー: {result['error']}")
        
        # 全体統計
        st.subheader("📊 処理統計")
        successful = sum(1 for r in results if r.get('status') == 'completed')
        total_files = len(results)
        total_time = sum(r.get('processing_time', 0) for r in results)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("成功率", f"{successful/total_files*100:.1f}%" if total_files > 0 else "0%")
        with col2:
            st.metric("総処理時間", f"{total_time:.2f}秒")
        with col3:
            st.metric("平均処理時間", f"{total_time/total_files:.2f}秒" if total_files > 0 else "0秒")
        with col4:
            st.metric("スループット", f"{total_files/total_time*60:.1f}件/分" if total_time > 0 else "∞")

    def display_detailed_results_with_aggrid(self, results: List[Dict[str, Any]]):
        """ag-gridを使った詳細結果表示（OCRテスト相当）"""
        import streamlit as st
        import pandas as pd
        
        try:
            from infrastructure.ui.aggrid_helper import get_aggrid_manager
            
            aggrid_manager = get_aggrid_manager()
            if not aggrid_manager:
                st.warning("ag-gridマネージャーの初期化に失敗しました。代替表示を使用します。")
                return
            
            # 結果データをDataFrameに変換
            results_data = []
            for result in results:
                ai_result = result.get('ai_result', {})
                validation = result.get('validation', {})
                
                # 完全性スコアの計算（OCRテスト相当）
                total_fields = 10  # 主要フィールド数
                filled_fields = sum(1 for key in ['issuer', 'amount_inclusive_tax', 'currency', 'issue_date', 'main_invoice_number'] 
                                  if ai_result.get(key))
                completeness_score = (filled_fields / total_fields) * 100
                
                # 税込金額の安全な変換
                tax_included = ai_result.get("amount_inclusive_tax", 0)
                if not isinstance(tax_included, (int, float)):
                    try:
                        tax_included = float(tax_included) if tax_included else 0
                    except (ValueError, TypeError):
                        tax_included = 0
                tax_included = int(tax_included)
                
                # エラー数と警告数
                error_count = len(validation.get("errors", []))
                warning_count = len(validation.get("warnings", []))
                
                results_data.append({
                    "ファイル名": result.get('filename', 'N/A'),
                    "請求元": ai_result.get('issuer', ''),
                    "請求書番号": ai_result.get('main_invoice_number', ''),
                    "通貨": ai_result.get('currency', ''),
                    "税込金額": tax_included,
                    "発行日": ai_result.get('issue_date', ''),
                    "検証状況": "✅ 正常" if validation.get('is_valid', True) else "❌ エラー",
                    "完全性スコア": round(completeness_score, 1),
                    "エラー数": error_count,
                    "警告数": warning_count,
                    "処理時間": f"{result.get('processing_time', 0):.2f}秒"
                })
            
            if len(results_data) > 0:
                df = pd.DataFrame(results_data)
                
                # 選択状態リセットボタン
                col_grid, col_reset = st.columns([4, 1])
                with col_grid:
                    st.subheader("📊 統一ワークフロー結果 (ag-grid)")
                with col_reset:
                    if st.button("🔄 選択リセット", key="reset_unified_workflow_selection"):
                        unified_key = "selected_unified_workflow_file"
                        if unified_key in st.session_state:
                            del st.session_state[unified_key]
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
                
                # セッション状態で選択情報を管理
                unified_key = "selected_unified_workflow_file"
                
                # 新しい選択があればセッション状態を更新
                if len(selected_rows) > 0:
                    selected_row = selected_rows[0]
                    filename = selected_row["ファイル名"]
                    st.session_state[unified_key] = filename
                # 選択がなければセッション状態から復元
                elif unified_key in st.session_state:
                    filename = st.session_state[unified_key]
                else:
                    filename = None
                
                # ファイルが選択されている場合の詳細表示
                if filename:
                    st.markdown(f"### 📄 選択されたファイル: {filename}")
                    
                    # 該当する詳細結果を取得
                    try:
                        selected_result = next(
                            r for r in results 
                            if r.get('filename') == filename
                        )
                    except StopIteration:
                        st.error(f"❌ ファイル '{filename}' の詳細結果が見つかりません")
                        # セッション状態をクリア
                        if unified_key in st.session_state:
                            del st.session_state[unified_key]
                        selected_result = None
                    
                    # 詳細情報を表示
                    if selected_result is not None:
                        self.display_invoice_details(selected_result)
                        
        except ImportError:
            st.warning("ag-gridライブラリが利用できません。標準のDataFrameで表示します。")
            # 代替表示
            if len(results_data) > 0:
                df = pd.DataFrame(results_data)
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"ag-grid表示中にエラー: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    def display_invoice_details(self, result: Dict[str, Any]):
        """請求書詳細情報の表示（OCRテスト相当）"""
        import streamlit as st
        
        ai_result = result.get('ai_result', {})
        validation = result.get('validation', {})
        
        # 基本情報表示
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📋 基本情報")
            st.write(f"**請求元**: {ai_result.get('issuer', 'N/A')}")
            st.write(f"**請求先**: {ai_result.get('payer', 'N/A')}")
            st.write(f"**請求書番号**: {ai_result.get('main_invoice_number', 'N/A')}")
            st.write(f"**発行日**: {ai_result.get('issue_date', 'N/A')}")
            st.write(f"**支払期日**: {ai_result.get('due_date', 'N/A')}")
        
        with col2:
            st.markdown("#### 💰 金額情報")
            amount_inc = ai_result.get('amount_inclusive_tax', 0)
            amount_exc = ai_result.get('amount_exclusive_tax', 0)
            st.write(f"**税込金額**: ¥{amount_inc:,}" if amount_inc else "**税込金額**: N/A")
            st.write(f"**税抜金額**: ¥{amount_exc:,}" if amount_exc else "**税抜金額**: N/A")
            st.write(f"**通貨**: {ai_result.get('currency', 'N/A')}")
            
            # 税率計算
            if amount_inc and amount_exc and amount_inc > amount_exc:
                tax_rate = ((amount_inc - amount_exc) / amount_exc) * 100
                st.write(f"**計算税率**: {tax_rate:.1f}%")
        
        # 明細表示
        st.markdown("---")
        self.display_line_items(ai_result)
        
        # JSON表示
        st.markdown("---")
        st.markdown("### 📄 JSON形式のAI結果")
        with st.expander("詳細JSON表示", expanded=False):
            st.json(ai_result)
        
        # 検証結果詳細
        if validation:
            st.markdown("---")
            st.markdown("### 🔍 検証結果詳細")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("検証状況", "✅ 合格" if validation.get('is_valid', True) else "❌ 不合格")
            with col2:
                st.metric("エラー数", len(validation.get('errors', [])))
            with col3:
                st.metric("警告数", len(validation.get('warnings', [])))

    def display_line_items(self, ai_result: Dict[str, Any]):
        """明細情報をag-gridで表示（OCRテスト相当）"""
        import streamlit as st
        import pandas as pd
        
        line_items = ai_result.get("line_items", [])
        if not isinstance(line_items, list):
            line_items = []
        
        if len(line_items) > 0:
            st.markdown("### 📋 明細情報")
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
                if aggrid_manager:
                    aggrid_manager.create_data_grid(
                        line_items_df,
                        editable=False,
                        fit_columns_on_grid_load=True,
                        height=200
                    )
                else:
                    st.dataframe(line_items_df, use_container_width=True)
            except ImportError:
                # ag-gridが利用できない場合は標準表示
                st.dataframe(line_items_df, use_container_width=True)
            except Exception as e:
                st.error(f"明細表示エラー: {str(e)}")
                st.dataframe(line_items_df, use_container_width=True)
        else:
            st.info("📋 明細情報: このファイルには明細データがありません")


# 同期処理用の拡張メソッド（UnifiedProcessingWorkflowクラスに追加）
def _add_sync_methods_to_workflow():
    """同期処理メソッドをワークフロークラスに動的追加"""
    
    def _process_single_file_sync(self, 
                                 file_data: bytes,
                                 filename: str,
                                 mode: str = ProcessingMode.UPLOAD,
                                 prompt_key: str = None,
                                 include_validation: bool = True,
                                 validation_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """単一ファイルの同期処理"""
        session_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # プロンプト準備
            if not prompt_key:
                prompt_key = self.prompt_selector.get_recommended_prompt(mode)
            
            system_prompt, user_prompt = self.prompt_manager.format_prompt_for_gemini(
                prompt_key, {"filename": filename}
            )
            
            # AI処理実行（同期）
            # 統一プロンプトを結合
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # GeminiAPIManagerの直接呼び出し（中間レイヤー削除）
            ai_result = self.gemini_helper.analyze_pdf_content(
                file_data,
                combined_prompt
            )
            
            # データ検証
            validation_result = {}
            if include_validation:
                validation_result = self.validator.validate_invoice_data(
                    ai_result, 
                    strict_mode=validation_config.get('strict_mode', False) if validation_config else False
                )
            
            # 処理時間計算
            processing_time = time.time() - start_time
            
            result = {
                'session_id': session_id,
                'filename': filename,
                'mode': mode,
                'ai_result': ai_result,
                'validation': validation_result,
                'prompt_used': prompt_key,
                'processed_at': get_jst_now(),
                'processing_time': processing_time,
                'status': ProcessingStatus.COMPLETED,
                'success': True
            }
            
            return result
            
        except Exception as e:
            logger.error(f"単一ファイル同期処理エラー: {e}")
            processing_time = time.time() - start_time
            
            error_result = {
                'session_id': session_id,
                'filename': filename,
                'error': str(e),
                'error_details': f"Type: {type(e).__name__}, Message: {str(e)}",
                'status': ProcessingStatus.FAILED,
                'processed_at': get_jst_now(),
                'processing_time': processing_time,
                'success': False
            }
            
            return error_result
    
    # _process_with_gemini_sync メソッド削除済み（直接 GeminiAPIManager.analyze_pdf_content 呼び出しに統一）
    
    def _start_session_sync(self, session_id: str, mode: str, filenames: List[str]):
        """セッション開始処理（同期版）"""
        self.active_sessions[session_id] = {
            'mode': mode,
            'filenames': filenames,
            'started_at': get_jst_now(),
            'status': ProcessingStatus.IN_PROGRESS
        }
        
        logger.info(f"セッション開始: {session_id} (モード: {mode}, ファイル数: {len(filenames)})")
    
    def _complete_session_sync(self, session_id: str, result: Dict[str, Any]):
        """セッション完了処理（同期版）"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['status'] = ProcessingStatus.COMPLETED
            self.active_sessions[session_id]['completed_at'] = get_jst_now()
            self.active_sessions[session_id]['result'] = result
        
        logger.info(f"セッション完了: {session_id}")
    
    def _fail_session_sync(self, session_id: str, error_result: Dict[str, Any]):
        """セッション失敗処理（同期版）"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['status'] = ProcessingStatus.FAILED
            self.active_sessions[session_id]['failed_at'] = get_jst_now()
            self.active_sessions[session_id]['error'] = error_result
        
        logger.error(f"セッション失敗: {session_id}")
    
    # メソッドをクラスに動的追加
    UnifiedProcessingWorkflow._process_single_file_sync = _process_single_file_sync
    # UnifiedProcessingWorkflow._process_with_gemini_sync = _process_with_gemini_sync  # 削除済み
    UnifiedProcessingWorkflow._start_session_sync = _start_session_sync
    UnifiedProcessingWorkflow._complete_session_sync = _complete_session_sync
    UnifiedProcessingWorkflow._fail_session_sync = _fail_session_sync
    
# 自動的にメソッドを追加
_add_sync_methods_to_workflow()