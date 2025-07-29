-- 📊 スキーマ不整合詳細調査
-- 作成日: 2025-07-28
-- 目的: 本番・テスト間の統一スキーマ状況確認

-- 🔍 Step 1: 本番テーブル（invoices）スキーマ詳細
SELECT 
    '📋 本番テーブル (invoices) スキーマ' as table_info,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'invoices' 
ORDER BY ordinal_position;

-- 🔍 Step 2: テストテーブル（ocr_test_results）スキーマ詳細
SELECT 
    '📋 テストテーブル (ocr_test_results) スキーマ' as table_info,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns 
WHERE table_name = 'ocr_test_results' 
ORDER BY ordinal_position;

-- 🔍 Step 3: gemini_modelフィールド存在確認
SELECT 
    'gemini_model存在確認' as check_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'gemini_model') as invoices_has_gemini_model,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 'gemini_model') as ocr_test_has_gemini_model;

-- 🔍 Step 4: 統一化対象フィールド存在確認
SELECT 
    '統一化対象フィールド存在確認' as check_type,
    -- main_invoice_number
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'main_invoice_number') as invoices_main_invoice_number,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 'main_invoice_number') as ocr_test_main_invoice_number,
    -- t_number
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 't_number') as invoices_t_number,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 't_number') as ocr_test_t_number,
    -- receipt_number
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'receipt_number') as invoices_receipt_number,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 'receipt_number') as ocr_test_receipt_number;

-- 🔍 Step 5: 旧フィールド残存確認
SELECT 
    '旧フィールド残存確認' as check_type,
    -- invoice_number (旧)
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'invoice_number') as invoices_old_invoice_number,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 'invoice_number') as ocr_test_old_invoice_number,
    -- registration_number (旧)
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'registration_number') as invoices_old_registration_number,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 'registration_number') as ocr_test_old_registration_number; 