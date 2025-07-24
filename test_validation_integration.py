#!/usr/bin/env python3
"""
統合バリデーションシステム動作確認テスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src"))

from core.services.invoice_validator import InvoiceValidator

def test_unified_validation_system():
    """統合バリデーションシステムのテスト"""
    
    print('🧪 統合バリデーションシステムのテスト')
    print('=' * 60)
    
    # テストケース1: 正常データ（国内取引）
    test_data_1 = {
        'issuer': 'テスト株式会社',
        'amount_inclusive_tax': 1100.0,
        'amount_exclusive_tax': 1000.0,
        'currency': 'JPY',
        'payer': '受注企業株式会社',
        'main_invoice_number': 'JP-TEST-001',
        'issue_date': '2025-01-15',
        'due_date': '2025-02-15'
    }
    
    # テストケース2: 外貨取引データ
    test_data_2 = {
        'issuer': 'Perplexity AI Inc',
        'amount_inclusive_tax': 5.0,
        'amount_exclusive_tax': 5.0,  # 外貨では税込=税抜が正常
        'currency': 'USD',
        'payer': '株式会社テスト',
        'main_invoice_number': 'US-TEST-001',
        'issue_date': '2025-01-15'
    }
    
    # テストケース3: エラーデータ（必須フィールド不足）
    test_data_3 = {
        'payer': '株式会社テスト',
        'main_invoice_number': 'ERROR-TEST-001'
        # issuer, amount_inclusive_tax, currencyが不足
    }
    
    # バリデーター初期化
    try:
        validator = InvoiceValidator()
        print('✅ InvoiceValidator初期化成功')
    except Exception as e:
        print(f'❌ InvoiceValidator初期化失敗: {e}')
        return False
    
    # テストケース1実行
    print('\n📋 テストケース1: 正常データ（国内取引）')
    try:
        result1 = validator.validate_invoice_data(test_data_1)
        print(f'✅ バリデーション実行完了')
        print(f'📊 結果: valid={result1["is_valid"]}, errors={len(result1["errors"])}, warnings={len(result1["warnings"])}')
        
        if result1['warnings']:
            print('⚠️ 警告:')
            for warning in result1['warnings']:
                print(f'  - {warning}')
                
    except Exception as e:
        print(f'❌ テストケース1失敗: {e}')
        return False
    
    # テストケース2実行
    print('\n📋 テストケース2: 外貨取引データ')
    try:
        result2 = validator.validate_invoice_data(test_data_2)
        print(f'✅ バリデーション実行完了')
        print(f'📊 結果: valid={result2["is_valid"]}, errors={len(result2["errors"])}, warnings={len(result2["warnings"])}')
        
        if result2['warnings']:
            print('⚠️ 警告:')
            for warning in result2['warnings']:
                print(f'  - {warning}')
                
    except Exception as e:
        print(f'❌ テストケース2失敗: {e}')
        return False
    
    # テストケース3実行
    print('\n📋 テストケース3: エラーデータ（必須フィールド不足）')
    try:
        result3 = validator.validate_invoice_data(test_data_3)
        print(f'✅ バリデーション実行完了')
        print(f'📊 結果: valid={result3["is_valid"]}, errors={len(result3["errors"])}, warnings={len(result3["warnings"])}')
        
        if result3['errors']:
            print('❌ エラー:')
            for error in result3['errors']:
                print(f'  - {error}')
                
    except Exception as e:
        print(f'❌ テストケース3失敗: {e}')
        return False
    
    # 通貨コード正規化テスト
    print('\n📋 通貨コード正規化テスト')
    test_currencies = ['円', 'ドル', '¥', '$', 'EUR', 'eur']
    
    for currency in test_currencies:
        test_data = {
            'issuer': 'テスト企業',
            'amount_inclusive_tax': 100.0,
            'currency': currency
        }
        
        result = validator.validate_invoice_data(test_data)
        normalized_currency = test_data.get('currency', currency)  # 正規化されて更新される可能性
        print(f'  {currency} → 正規化後: データ内の通貨={normalized_currency}')
    
    print('\n🎉 統合バリデーションシステム動作確認完了！')
    return True

if __name__ == "__main__":
    success = test_unified_validation_system()
    exit(0 if success else 1) 