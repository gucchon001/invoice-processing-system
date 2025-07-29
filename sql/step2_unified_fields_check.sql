-- 📋 Step 2: 統一化対象フィールド存在確認
-- 目的: 新統一フィールドの存在確認

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