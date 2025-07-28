-- ================================================================
-- Step 5: Phase 3A 最終検証（シンプル版）
-- ================================================================

-- 1. 作成されたビューの確認
SELECT 
    table_name as "作成されたビュー",
    'OK' as "ステータス"
FROM information_schema.views 
WHERE table_name LIKE '%_optimized'
ORDER BY table_name;

-- 2. 作成されたインデックスの確認
SELECT 
    indexname as "作成されたインデックス",
    'OK' as "ステータス"
FROM pg_indexes 
WHERE indexname IN (
    'idx_invoices_user_status_created',
    'idx_ocr_results_session_valid_score'
);

-- 3. 削除されたカラムの確認
SELECT 
    'ocr_test_results.file_size' as "削除対象カラム",
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'ocr_test_results' AND column_name = 'file_size'
        ) THEN '削除成功'
        ELSE '削除失敗'
    END as "削除ステータス";

-- 4. データ整合性確認
SELECT 
    'invoices' as "テーブル名",
    (SELECT COUNT(*) FROM invoices) as "元テーブル件数",
    (SELECT COUNT(*) FROM invoices_optimized) as "最適化ビュー件数",
    CASE 
        WHEN (SELECT COUNT(*) FROM invoices) = (SELECT COUNT(*) FROM invoices_optimized) 
        THEN '整合性OK'
        ELSE '整合性エラー'
    END as "整合性ステータス";

-- 5. OCRテストテーブル整合性確認
SELECT 
    'ocr_test_results' as "テーブル名",
    (SELECT COUNT(*) FROM ocr_test_results) as "元テーブル件数",
    (SELECT COUNT(*) FROM ocr_test_results_optimized) as "最適化ビュー件数",
    CASE 
        WHEN (SELECT COUNT(*) FROM ocr_test_results) = (SELECT COUNT(*) FROM ocr_test_results_optimized) 
        THEN '整合性OK'
        ELSE '整合性エラー'
    END as "整合性ステータス"; 