#!/usr/bin/env python3
"""
統合システム包括的テスト

重複解消後のシステム全体の動作確認
"""

import sys
import os
from pathlib import Path
import asyncio
import time

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src"))

def test_database_tools():
    """統合データベースツールのテスト"""
    print('\n🔧 統合データベースツール機能テスト')
    print('=' * 60)
    
    try:
        from tools.database_tools import DatabaseTools
        
        # ツール初期化
        db_tools = DatabaseTools()
        success = db_tools.connect()
        
        if success:
            print('✅ データベースツール接続成功')
            
            # 基本機能テスト
            print('\n📊 基本機能テスト:')
            db_tools.show_recent_invoices(3)
            
            return True
        else:
            print('❌ データベースツール接続失敗')
            return False
            
    except Exception as e:
        print(f'❌ データベースツールテスト失敗: {e}')
        return False

def test_validation_system():
    """統合バリデーションシステムのテスト"""
    print('\n🛡️ 統合バリデーションシステムテスト')
    print('=' * 60)
    
    try:
        from core.services.invoice_validator import InvoiceValidator
        
        validator = InvoiceValidator()
        print('✅ InvoiceValidator初期化成功')
        
        # エラーケーステスト
        error_data = {
            'payer': 'テスト企業'
            # 必須フィールド不足
        }
        
        result = validator.validate_invoice_data(error_data)
        
        if not result['is_valid'] and len(result['errors']) > 0:
            print('✅ エラー検出機能正常動作')
            print(f'   検出エラー数: {len(result["errors"])}件')
            return True
        else:
            print('❌ エラー検出機能異常')
            return False
            
    except Exception as e:
        print(f'❌ バリデーションシステムテスト失敗: {e}')
        return False

def test_workflow_components():
    """ワークフロー関連コンポーネントのテスト"""
    print('\n⚙️ ワークフロー関連コンポーネントテスト')
    print('=' * 60)
    
    try:
        # 統一プロンプトマネージャー
        from core.services.unified_prompt_manager import UnifiedPromptManager
        
        prompt_manager = UnifiedPromptManager("prompts")
        available_prompts = prompt_manager.list_available_prompts()
        
        if available_prompts:
            print(f'✅ 統一プロンプトマネージャー動作確認: {len(available_prompts)}個のプロンプト')
        else:
            print('⚠️ プロンプトが見つかりません')
        
        # ワークフローモデル
        from core.models.workflow_models import ProcessingMode, ProcessingStatus
        
        print('✅ ワークフローモデル読み込み成功')
        print(f'   ProcessingMode: {[mode for mode in dir(ProcessingMode) if not mode.startswith("_")]}')
        
        return True
        
    except Exception as e:
        print(f'❌ ワークフローコンポーネントテスト失敗: {e}')
        return False

def test_infrastructure_components():
    """インフラストラクチャコンポーネントのテスト"""
    print('\n🏗️ インフラストラクチャコンポーネントテスト')
    print('=' * 60)
    
    try:
        # データベースマネージャー
        from infrastructure.database.database import DatabaseManager
        
        db_manager = DatabaseManager()
        if db_manager.test_connection():
            print('✅ DatabaseManager接続成功')
        else:
            print('⚠️ DatabaseManager接続警告')
        
        # AI ヘルパー
        from infrastructure.ai.gemini_helper import GeminiAPIManager
        
        try:
            gemini_manager = GeminiAPIManager()
            print('✅ GeminiAPIManager初期化成功')
        except Exception as e:
            print(f'⚠️ GeminiAPIManager初期化警告: {e}')
        
        # Google Drive ヘルパー
        try:
            from infrastructure.storage.google_drive_helper import GoogleDriveManager
            
            drive_manager = GoogleDriveManager()
            print('✅ GoogleDriveManager初期化成功')
        except Exception as e:
            print(f'⚠️ GoogleDriveManager初期化警告: {e}')
        
        return True
        
    except Exception as e:
        print(f'❌ インフラストラクチャテスト失敗: {e}')
        return False

def test_file_structure_consistency():
    """ファイル構造の整合性確認"""
    print('\n📁 ファイル構造整合性テスト')
    print('=' * 60)
    
    # 削除されたファイルの確認
    deleted_files = [
        'src/core/validation/invoice_validator.py',  # 重複削除済み
        'src/core/workflows/invoice_processing.py',  # 重複削除済み
        'check_database.py',                         # 統合済み
        'check_database_detailed.py',                # 統合済み
        'check_latest_data.py',                      # 統合済み
        'check_full_table_structure.py'             # 統合済み
    ]
    
    print('🗑️ 重複ファイル削除確認:')
    all_deleted = True
    for file_path in deleted_files:
        if Path(file_path).exists():
            print(f'❌ 削除されていません: {file_path}')
            all_deleted = False
        else:
            print(f'✅ 削除確認: {file_path}')
    
    # 統合ファイルの確認
    integrated_files = [
        'tools/database_tools.py',                   # 統合ツール
        'src/core/services/invoice_validator.py',   # 統合バリデーター
        'src/core/workflows/unified_processing.py'  # 統一ワークフロー
    ]
    
    print('\n🔧 統合ファイル存在確認:')
    all_exist = True
    for file_path in integrated_files:
        if Path(file_path).exists():
            print(f'✅ 存在確認: {file_path}')
        else:
            print(f'❌ 存在しません: {file_path}')
            all_exist = False
    
    return all_deleted and all_exist

def main():
    """包括的テスト実行"""
    print('🧪 統合システム包括的テスト')
    print('=' * 60)
    print('目的: 重複解消後のシステム全体動作確認')
    
    test_results = []
    
    # 各テスト実行
    test_results.append(('ファイル構造整合性', test_file_structure_consistency()))
    test_results.append(('データベースツール', test_database_tools()))
    test_results.append(('バリデーションシステム', test_validation_system()))
    test_results.append(('ワークフローコンポーネント', test_workflow_components()))
    test_results.append(('インフラストラクチャ', test_infrastructure_components()))
    
    # 結果サマリー
    print('\n📊 テスト結果サマリー')
    print('=' * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = '✅ PASS' if result else '❌ FAIL'
        print(f'{status} {test_name}')
        if result:
            passed += 1
    
    print(f'\n🎯 総合結果: {passed}/{total} テスト通過')
    
    if passed == total:
        print('🎉 全テスト通過！統合システム正常動作確認')
        return True
    else:
        print('⚠️ 一部テストで問題を検出')
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 