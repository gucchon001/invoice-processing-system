-- ================================================================
-- Step 5: Phase 3A 最終検証
-- ================================================================

-- 作成されたビューの確認
SELECT 
    'created_views' as verification_type,
    table_name as object_name,
    'VIEW' as object_type,
    'OK' as status
FROM information_schema.views 
WHERE table_name LIKE '%_optimized'
ORDER BY table_name

UNION ALL

-- 作成されたインデックスの確認
SELECT 
    'created_indexes' as verification_type,
    indexname as object_name,
    'INDEX' as object_type,
    'OK' as status
FROM pg_indexes 
WHERE indexname IN (
    'idx_invoices_user_status_created',
    'idx_ocr_results_session_valid_score'
)

UNION ALL

-- 削除されたカラムの確認
SELECT 
    'deleted_columns' as verification_type,
    'ocr_test_results.file_size' as object_name,
    'COLUMN' as object_type,
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'ocr_test_results' AND column_name = 'file_size'
        ) THEN 'DELETED'
        ELSE 'STILL_EXISTS'
    END as status;

-- データ整合性確認
SELECT 
    'data_integrity' as check_type,
    original_table,
    optimized_view,
    original_count,
    view_count,
    CASE 
        WHEN original_count = view_count THEN 'OK'
        ELSE 'ERROR'
    END as integrity_status
FROM (
    SELECT 
        'invoices' as original_table,
        'invoices_optimized' as optimized_view,
        (SELECT COUNT(*) FROM invoices) as original_count,
        (SELECT COUNT(*) FROM invoices_optimized) as view_count
    
    UNION ALL
    
    SELECT 
        'ocr_test_results' as original_table,
        'ocr_test_results_optimized' as optimized_view,
        (SELECT COUNT(*) FROM ocr_test_results) as original_count,
        (SELECT COUNT(*) FROM ocr_test_results_optimized) as view_count
    
    UNION ALL
    
    SELECT 
        'ocr_test_sessions' as original_table,
        'ocr_test_sessions_optimized' as optimized_view,
        (SELECT COUNT(*) FROM ocr_test_sessions) as original_count,
        (SELECT COUNT(*) FROM ocr_test_sessions_optimized) as view_count
) integrity_check; 