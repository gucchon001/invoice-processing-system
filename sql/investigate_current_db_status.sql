-- ===================================================
-- 現在のデータベース状況調査スクリプト
-- ===================================================

-- 1. 全テーブル一覧
SELECT 
    '=== 全テーブル一覧 ===' as section;

SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- 2. invoices テーブル構造詳細
SELECT 
    '=== invoices テーブル構造 ===' as section;

SELECT 
    ordinal_position,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'invoices'
ORDER BY ordinal_position;

-- 3. invoice_line_items テーブル構造詳細
SELECT 
    '=== invoice_line_items テーブル構造 ===' as section;

SELECT 
    ordinal_position,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'invoice_line_items'
ORDER BY ordinal_position;

-- 4. ocr_test_results テーブル構造詳細
SELECT 
    '=== ocr_test_results テーブル構造 ===' as section;

SELECT 
    ordinal_position,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'ocr_test_results'
ORDER BY ordinal_position;

-- 5. ocr_test_line_items テーブル構造詳細
SELECT 
    '=== ocr_test_line_items テーブル構造 ===' as section;

SELECT 
    ordinal_position,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'ocr_test_line_items'
ORDER BY ordinal_position;

-- 6. ocr_test_sessions テーブル構造詳細
SELECT 
    '=== ocr_test_sessions テーブル構造 ===' as section;

SELECT 
    ordinal_position,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'ocr_test_sessions'
ORDER BY ordinal_position;

-- 7. 各テーブルのデータ件数
SELECT 
    '=== 各テーブルのデータ件数 ===' as section;

SELECT 
    'invoices' as table_name,
    COUNT(*) as row_count
FROM invoices
UNION ALL
SELECT 
    'invoice_line_items' as table_name,
    COUNT(*) as row_count
FROM invoice_line_items
UNION ALL
SELECT 
    'ocr_test_results' as table_name,
    COUNT(*) as row_count
FROM ocr_test_results
UNION ALL
SELECT 
    'ocr_test_line_items' as table_name,
    COUNT(*) as row_count
FROM ocr_test_line_items
UNION ALL
SELECT 
    'ocr_test_sessions' as table_name,
    COUNT(*) as row_count
FROM ocr_test_sessions;

-- 8. インデックス情報
SELECT 
    '=== インデックス情報 ===' as section;

SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
AND tablename IN ('invoices', 'invoice_line_items', 'ocr_test_results', 'ocr_test_line_items', 'ocr_test_sessions')
ORDER BY tablename, indexname;

-- 9. 外部キー制約
SELECT 
    '=== 外部キー制約 ===' as section;

SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public'
AND tc.table_name IN ('invoices', 'invoice_line_items', 'ocr_test_results', 'ocr_test_line_items', 'ocr_test_sessions');

-- 10. 重要なフィールド名の比較
SELECT 
    '=== 重要フィールド名比較 ===' as section;

-- invoices vs ocr_test_results のフィールド名比較
WITH invoices_cols AS (
    SELECT column_name, ordinal_position 
    FROM information_schema.columns 
    WHERE table_schema = 'public' AND table_name = 'invoices'
),
ocr_cols AS (
    SELECT column_name, ordinal_position 
    FROM information_schema.columns 
    WHERE table_schema = 'public' AND table_name = 'ocr_test_results'
)
SELECT 
    'invoices vs ocr_test_results' as comparison,
    COALESCE(i.column_name, '---') as invoices_column,
    COALESCE(o.column_name, '---') as ocr_test_results_column,
    CASE 
        WHEN i.column_name = o.column_name THEN '✓ 一致'
        WHEN i.column_name IS NULL THEN '← OCRのみ'
        WHEN o.column_name IS NULL THEN 'invoicesのみ →'
        ELSE '× 不一致'
    END as status
FROM invoices_cols i
FULL OUTER JOIN ocr_cols o ON i.ordinal_position = o.ordinal_position
ORDER BY COALESCE(i.ordinal_position, o.ordinal_position); 