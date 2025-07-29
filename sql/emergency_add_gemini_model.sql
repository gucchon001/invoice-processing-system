-- 🚨 緊急修正: 本番テーブルにgemini_modelフィールド追加
-- 作成日: 2025-07-28
-- 目的: Streamlitアプリケーションエラー解決

-- Step 1: gemini_modelフィールド追加
ALTER TABLE invoices 
ADD COLUMN gemini_model VARCHAR(50) DEFAULT 'gemini-2.5-flash-lite-preview-06-17';

-- Step 2: 追加確認
SELECT 
    'gemini_model追加確認' as check_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'gemini_model') as invoices_has_gemini_model; 