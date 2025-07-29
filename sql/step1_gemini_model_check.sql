-- 📋 Step 1: gemini_model存在確認
-- 目的: 本番・テスト間のgemini_modelフィールド存在確認

SELECT 
    'gemini_model存在確認' as check_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'gemini_model') as invoices_has_gemini_model,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_results' AND column_name = 'gemini_model') as ocr_test_has_gemini_model; 