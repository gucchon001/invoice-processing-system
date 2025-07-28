-- ================================================================
-- Step 3: 不要フィールド存在確認
-- ================================================================

-- 削除対象カラムの存在確認
SELECT 
    'invoices.line_items' as target_column,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'invoices' AND column_name = 'line_items'
        ) THEN '存在 - 削除可能'
        ELSE '不存在 - 削除不要'
    END as status

UNION ALL

SELECT 
    'ocr_test_results.file_size' as target_column,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'ocr_test_results' AND column_name = 'file_size'
        ) THEN '存在 - 削除可能'
        ELSE '不存在 - 削除不要'
    END as status; 