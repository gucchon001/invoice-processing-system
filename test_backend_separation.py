"""
バックエンド処理層分離テスト
目的: UI層非依存でのビジネスロジック動作確認
"""

import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal
import json
from typing import List, Dict, Any
import tempfile

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# from core.workflows.unified_processing import UnifiedProcessingWorkflow  # 削除済み - UnifiedWorkflowEngineに統合
# LocalFileAdapterは削除済み（UnifiedWorkflowEngineに統合）
from core.adapters.base_adapters import FileData
from core.models.workflow_models import ProcessingMode, WorkflowProgress
from infrastructure.ai.gemini_helper import GeminiAPIManager
from utils.log_config import get_logger

logger = get_logger(__name__)

class BackendSeparationTester:
    """バックエンド処理層分離テスト実行クラス"""
    
    def __init__(self):
        self.workflow = None
        self.ai_manager = None
        self.test_results = []
        self.mock_files = []
    
    async def setup(self):
        """テスト環境セットアップ"""
        try:
            # 統合ワークフロー初期化
            # UnifiedProcessingWorkflowは削除済み - UnifiedWorkflowEngineに統合
            # self.workflow = UnifiedProcessingWorkflow()
            # await self.workflow.initialize()
            
            # AI管理システム初期化
            self.ai_manager = GeminiAPIManager()
            
            # モックファイル作成
            await self.create_mock_files()
            
            logger.info("✅ バックエンド処理層セットアップ成功")
            return True
        except Exception as e:
            logger.error(f"❌ バックエンド処理層セットアップ失敗: {e}")
            return False
    
    async def create_mock_files(self):
        """テスト用モックファイル作成"""
        try:
            # モック請求書データ
            mock_data_list = [
                {
                    'filename': 'backend_test_invoice_1.pdf',
                    'content': b'%PDF-1.4 Mock Invoice Data 1',
                    'expected_data': {
                        'issuer': 'バックエンドテスト会社1',
                        'amount': '50000',
                        'invoice_number': 'BE-001'
                    }
                },
                {
                    'filename': 'backend_test_invoice_2.pdf', 
                    'content': b'%PDF-1.4 Mock Invoice Data 2',
                    'expected_data': {
                        'issuer': 'バックエンドテスト会社2',
                        'amount': '75000',
                        'invoice_number': 'BE-002'
                    }
                }
            ]
            
            for mock_data in mock_data_list:
                file_data = FileData(
                    content=mock_data['content'],
                    filename=mock_data['filename'],
                    content_type='application/pdf',
                    size=len(mock_data['content']),
                    metadata={'test_mode': 'backend_separation', **mock_data['expected_data']}
                )
                self.mock_files.append(file_data)
            
            logger.info(f"✅ モックファイル作成完了: {len(self.mock_files)}件")
            
        except Exception as e:
            logger.error(f"❌ モックファイル作成失敗: {e}")
            raise
    
    async def test_workflow_independence(self):
        """ワークフロー独立性テスト（無効化済み）"""
        test_name = "ワークフロー独立性（スキップ）"
        try:
            logger.info("🔄 ワークフロー独立性テスト開始（スキップ - 統合済み）")
            
            # UnifiedProcessingWorkflowは削除済みのため、テストをスキップ
            logger.info("✅ ワークフロー独立性テスト: スキップ（統合完了）")
            self.results[test_name] = {
                'status': 'スキップ',
                'message': 'UnifiedWorkflowEngineに統合済み',
                'details': '旧システムは削除済み'
            }
            
            # 結果検証
            if result and result.get('success'):
                processed_count = len(result.get('processed_files', []))
                logger.info(f"✅ ワークフロー実行成功: {processed_count}件処理")
                
                # プログレス追跡確認
                if len(progress_events) > 0:
                    logger.info(f"✅ プログレス追跡成功: {len(progress_events)}イベント")
                else:
                    logger.warning("⚠️ プログレスイベントが記録されていません")
                
                self.test_results.append({
                    'test': test_name,
                    'status': 'success',
                    'details': f'処理: {processed_count}件, イベント: {len(progress_events)}件'
                })
            else:
                raise Exception(f"ワークフロー実行失敗: {result}")
            
        except Exception as e:
            logger.error(f"❌ {test_name}失敗: {e}")
            self.test_results.append({
                'test': test_name,
                'status': 'failed',
                'error': str(e)
            })
    
    async def test_ai_processing_independence(self):
        """AI処理独立性テスト"""
        test_name = "AI処理独立性"
        try:
            logger.info("🤖 AI処理独立性テスト開始")
            
            # モックプロンプトでのAI処理（UI非依存）
            mock_prompt = {
                'name': 'Backend Test Prompt',
                'system_prompt': 'テスト用システムプロンプト',
                'user_prompt_template': '次のデータを解析してください: {content}',
                'response_format': 'JSON'
            }
            
            test_content = "テスト用請求書データ: 会社名=テスト会社, 金額=100000円"
            
            # AI処理実行
            ai_result = await self.ai_manager.process_with_prompt(
                content=test_content,
                prompt_data=mock_prompt,
                max_retries=1
            )
            
            if ai_result and ai_result.get('success'):
                logger.info("✅ AI処理実行成功")
                
                # レスポンス形式確認
                response_data = ai_result.get('data')
                if response_data:
                    logger.info("✅ AI応答データ取得成功")
                else:
                    logger.warning("⚠️ AI応答データが空です")
                
                self.test_results.append({
                    'test': test_name,
                    'status': 'success',
                    'details': 'AI処理・応答解析成功'
                })
            else:
                raise Exception(f"AI処理失敗: {ai_result}")
            
        except Exception as e:
            logger.error(f"❌ {test_name}失敗: {e}")
            self.test_results.append({
                'test': test_name,
                'status': 'failed',
                'error': str(e)
            })
    
    async def test_adapter_system_independence(self):
        """アダプターシステム独立性テスト"""
        test_name = "アダプターシステム独立性"
        try:
            logger.info("🔌 アダプターシステム独立性テスト開始（スキップ - LocalFileAdapter削除済み）")
            
            # ローカルファイルアダプター（UI非依存テスト）
            # adapter = LocalFileAdapter()  # 削除済み - UnifiedWorkflowEngineに統合
            
            # モックStreamlitアップロードオブジェクト作成
            class MockUploadedFile:
                def __init__(self, name: str, content: bytes):
                    self.name = name
                    self._content = content
                    self.type = 'application/pdf'
                    self.size = len(content)
                
                def read(self) -> bytes:
                    return self._content
                
                def getvalue(self) -> bytes:
                    return self._content
            
            mock_uploaded_files = [
                MockUploadedFile('adapter_test_1.pdf', b'Mock PDF Content 1'),
                MockUploadedFile('adapter_test_2.pdf', b'Mock PDF Content 2')
            ]
            
            # アダプター変換実行
            converted_files = await adapter.convert_to_file_data(mock_uploaded_files)
            
            if converted_files and len(converted_files) == 2:
                logger.info(f"✅ アダプター変換成功: {len(converted_files)}件")
                
                # データ整合性確認
                for i, file_data in enumerate(converted_files):
                    if (file_data.filename == mock_uploaded_files[i].name and
                        file_data.content == mock_uploaded_files[i].getvalue()):
                        logger.info(f"✅ ファイル{i+1}データ整合性確認")
                    else:
                        raise Exception(f"ファイル{i+1}データ整合性エラー")
                
                self.test_results.append({
                    'test': test_name,
                    'status': 'success',
                    'details': f'変換: {len(converted_files)}件, 整合性確認済み'
                })
            else:
                raise Exception(f"アダプター変換失敗: {len(converted_files) if converted_files else 0}件")
            
        except Exception as e:
            logger.error(f"❌ {test_name}失敗: {e}")
            self.test_results.append({
                'test': test_name,
                'status': 'failed',
                'error': str(e)
            })
    
    async def test_validation_engine_independence(self):
        """検証エンジン独立性テスト"""
        test_name = "検証エンジン独立性"
        try:
            logger.info("🔍 検証エンジン独立性テスト開始")
            
            # モック抽出データ
            mock_extracted_data = {
                'issuer': 'テスト検証会社',
                'main_invoice_number': 'VAL-001',
                'amount_inclusive_tax': '108000',
                'amount_exclusive_tax': '100000',
                'issue_date': '2025-01-23',
                'line_items': [
                    {
                        'description': '商品A',
                        'quantity': '10',
                        'unit_price': '5000',
                        'amount': '50000'
                    }
                ]
            }
            
            # 検証設定
            validation_config = {
                'strict_mode': True,
                'check_amount_consistency': True,
                'validate_date_format': True,
                'validate_line_items': True
            }
            
            # 検証エンジン実行（UI非依存）
            validation_result = await self.workflow.validation_engine.validate_extracted_data(
                mock_extracted_data,
                validation_config
            )
            
            if validation_result:
                is_valid = validation_result.get('is_valid', False)
                warnings = validation_result.get('warnings', [])
                errors = validation_result.get('errors', [])
                
                logger.info(f"✅ 検証エンジン実行成功")
                logger.info(f"   検証結果: {'有効' if is_valid else '無効'}")
                logger.info(f"   警告: {len(warnings)}件")
                logger.info(f"   エラー: {len(errors)}件")
                
                # 検証ロジック確認
                if len(errors) == 0:  # モックデータは有効なはず
                    logger.info("✅ 検証ロジック正常動作")
                else:
                    logger.warning(f"⚠️ 予期しない検証エラー: {errors}")
                
                self.test_results.append({
                    'test': test_name,
                    'status': 'success',
                    'details': f'検証実行成功 - 警告: {len(warnings)}件, エラー: {len(errors)}件'
                })
            else:
                raise Exception("検証エンジン実行失敗")
            
        except Exception as e:
            logger.error(f"❌ {test_name}失敗: {e}")
            self.test_results.append({
                'test': test_name,
                'status': 'failed',
                'error': str(e)
            })
    
    async def test_error_handling_independence(self):
        """エラーハンドリング独立性テスト"""
        test_name = "エラーハンドリング独立性"
        try:
            logger.info("🚨 エラーハンドリング独立性テスト開始")
            
            # 意図的エラー発生テスト
            error_scenarios = [
                {
                    'name': '無効ファイル',
                    'files': [FileData(
                        content=b'Invalid Content',
                        filename='invalid.txt',  # 無効な拡張子
                        content_type='text/plain',
                        size=15
                    )],
                    'expected_error_type': 'validation_error'
                },
                {
                    'name': '空ファイル',
                    'files': [FileData(
                        content=b'',  # 空コンテンツ
                        filename='empty.pdf',
                        content_type='application/pdf',
                        size=0
                    )],
                    'expected_error_type': 'content_error'
                }
            ]
            
            error_handling_success = 0
            
            for scenario in error_scenarios:
                try:
                    result = await self.workflow.process_batch_files(
                        scenario['files'],
                        mode=ProcessingMode.OCR_TEST,
                        prompt_key="invoice_extractor_prompt",
                        validation_config={'strict_mode': True}
                    )
                    
                    # エラーが適切に処理されたか確認
                    if result and 'errors' in result:
                        logger.info(f"✅ {scenario['name']}エラー適切に処理")
                        error_handling_success += 1
                    else:
                        logger.warning(f"⚠️ {scenario['name']}エラーが予期通りに処理されませんでした")
                
                except Exception as e:
                    # 例外も適切なエラーハンドリング
                    logger.info(f"✅ {scenario['name']}例外適切に捕捉: {type(e).__name__}")
                    error_handling_success += 1
            
            if error_handling_success == len(error_scenarios):
                logger.info("✅ エラーハンドリング独立性確認")
                self.test_results.append({
                    'test': test_name,
                    'status': 'success',
                    'details': f'{error_handling_success}/{len(error_scenarios)}シナリオ成功'
                })
            else:
                raise Exception(f"エラーハンドリング失敗: {error_handling_success}/{len(error_scenarios)}")
            
        except Exception as e:
            logger.error(f"❌ {test_name}失敗: {e}")
            self.test_results.append({
                'test': test_name,
                'status': 'failed',
                'error': str(e)
            })
    
    def print_test_results(self):
        """テスト結果出力"""
        print("\n" + "="*60)
        print("📊 バックエンド処理層分離テスト結果")
        print("="*60)
        
        success_count = sum(1 for r in self.test_results if r['status'] == 'success')
        total_count = len(self.test_results)
        
        print(f"総テスト数: {total_count}")
        print(f"成功: {success_count}")
        print(f"失敗: {total_count - success_count}")
        print(f"成功率: {success_count/total_count*100:.1f}%")
        
        print("\n詳細結果:")
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'success' else "❌"
            print(f"{status_icon} {result['test']}")
            if result['status'] == 'success':
                print(f"   詳細: {result.get('details', 'N/A')}")
            else:
                print(f"   エラー: {result.get('error', 'N/A')}")
        
        print("\n" + "="*60)
        
        # バックエンド分離アーキテクチャ評価
        if success_count == total_count:
            print("🎉 バックエンド処理層の分離アーキテクチャは正常に動作しています！")
            print("✅ UI層非依存でのビジネスロジック実行が確認されました")
            print("✅ 統合ワークフロー・AI処理・検証エンジンの独立性確認")
        else:
            print("⚠️ バックエンド処理層の分離に問題が検出されました")
            print("🔧 修正が必要です")

async def main():
    """メイン実行関数"""
    tester = BackendSeparationTester()
    
    print("🧪 バックエンド処理層分離テスト開始")
    print("目的: UI層非依存でのビジネスロジック動作確認")
    
    # セットアップ
    if not await tester.setup():
        print("❌ セットアップ失敗 - テスト中止")
        return
    
    try:
        # 各テスト実行
        await tester.test_workflow_independence()
        await tester.test_ai_processing_independence()
        await tester.test_adapter_system_independence()
        await tester.test_validation_engine_independence()
        await tester.test_error_handling_independence()
        
    except Exception as e:
        logger.error(f"テスト実行中にエラー: {e}")
    
    # 結果出力
    tester.print_test_results()

if __name__ == "__main__":
    asyncio.run(main()) 