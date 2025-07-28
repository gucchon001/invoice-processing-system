-- ================================================================
-- Step 4: file_size カラム削除
-- ================================================================

-- ocr_test_results.file_size 削除
ALTER TABLE ocr_test_results DROP COLUMN IF EXISTS file_size;

-- 削除確認クエリ
SELECT 
    'ocr_test_results.file_size' as deleted_column,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'ocr_test_results' AND column_name = 'file_size'
        ) THEN '削除失敗 - まだ存在'
        ELSE '削除成功 - 不存在'
    END as deletion_status; 