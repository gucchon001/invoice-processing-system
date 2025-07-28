-- ===================================================
-- 統一スキーマ完全確認スクリプト
-- 再構築後の詳細検証
-- ===================================================

-- 1. 統一化フィールド詳細確認
SELECT 
    '=== 統一化フィールド詳細確認 ===' as section;

-- invoices テーブルの統一化フィールド
SELECT 
    'invoices' as table_name,
    column_name,
    data_type,
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name IN ('main_invoice_number', 't_number', 'receipt_number', 'key_info') 
        THEN '✅ 統一化フィールド'
        ELSE '📋 標準フィールド'
    END as field_type
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'invoices'
AND column_name IN ('main_invoice_number', 't_number', 'receipt_number', 'key_info', 'invoice_number', 'registration_number')
ORDER BY ordinal_position;

-- invoice_line_items テーブルの統一化フィールド
SELECT 
    'invoice_line_items' as table_name,
    column_name,
    data_type,
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    is_nullable,
    CASE 
        WHEN column_name IN ('item_description', 'tax_rate') 
        THEN '✅ 統一化フィールド'
        ELSE '📋 標準フィールド'
    END as field_type
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'invoice_line_items'
AND column_name IN ('item_description', 'description', 'tax_rate')
ORDER BY ordinal_position;

-- 2. OCRテストテーブルとの統一性確認
SELECT 
    '=== 本番とOCRテーブルの統一性確認 ===' as section;

-- フィールド名比較
WITH production_fields AS (
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'invoices' 
    AND column_name IN ('main_invoice_number', 't_number', 'receipt_number', 'key_info')
),
ocr_fields AS (
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'ocr_test_results' 
    AND column_name IN ('main_invoice_number', 't_number', 'receipt_number', 'key_info')
)
SELECT 
    COALESCE(p.column_name, o.column_name) as field_name,
    COALESCE(p.data_type, 'なし') as production_type,
    COALESCE(o.data_type, 'なし') as ocr_type,
    CASE 
        WHEN p.column_name IS NOT NULL AND o.column_name IS NOT NULL AND p.data_type = o.data_type 
        THEN '✅ 完全統一'
        WHEN p.column_name IS NULL 
        THEN '⚠️ 本番のみ'
        WHEN o.column_name IS NULL 
        THEN '⚠️ OCRのみ'
        ELSE '❌ 型不一致'
    END as unification_status
FROM production_fields p
FULL OUTER JOIN ocr_fields o ON p.column_name = o.column_name
ORDER BY field_name;

-- 3. インデックス確認
SELECT 
    '=== 統一化フィールドのインデックス確認 ===' as section;

SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
AND (
    indexdef LIKE '%main_invoice_number%' OR
    indexdef LIKE '%t_number%' OR
    indexdef LIKE '%receipt_number%' OR
    indexdef LIKE '%key_info%' OR
    indexdef LIKE '%item_description%'
)
ORDER BY tablename, indexname;

-- 4. 制約・外部キー確認
SELECT 
    '=== 外部キー制約確認 ===' as section;

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
AND tc.table_name IN ('invoices', 'invoice_line_items', 'ocr_test_results', 'ocr_test_line_items')
ORDER BY tc.table_name, tc.constraint_name;

-- 5. トリガー確認
SELECT 
    '=== updated_at トリガー確認 ===' as section;

SELECT 
    trigger_name,
    event_object_table,
    action_timing,
    event_manipulation,
    action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public'
AND trigger_name LIKE '%updated_at%'
ORDER BY event_object_table;

-- 6. RLS (Row Level Security) ポリシー確認
SELECT 
    '=== RLS ポリシー確認 ===' as section;

SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE schemaname = 'public'
AND tablename IN ('invoices', 'invoice_line_items', 'ocr_test_results', 'ocr_test_line_items', 'ocr_test_sessions')
ORDER BY tablename, policyname;

-- 7. データ件数確認（空であることの確認）
SELECT 
    '=== データ件数確認（空テーブル確認）===' as section;

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

-- 8. 最終確認：重要な旧フィールド名が存在しないことの確認
SELECT 
    '=== 旧フィールド名削除確認 ===' as section;

SELECT 
    table_name,
    column_name,
    '❌ 旧フィールド名が残存' as warning
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('invoices', 'invoice_line_items', 'ocr_test_results', 'ocr_test_line_items')
AND column_name IN ('invoice_number', 'registration_number', 'description')
AND table_name != 'ocr_test_line_items' -- OCRテーブルは一部descriptionが残る可能性

UNION ALL

SELECT 
    '確認完了' as table_name,
    '旧フィールド名は存在しません' as column_name,
    '✅ 統一化成功' as warning
WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'public' 
    AND table_name IN ('invoices', 'invoice_line_items')
    AND column_name IN ('invoice_number', 'registration_number', 'description')
);

-- 9. 統一スキーマ最終検証結果
SELECT 
    '=== 統一スキーマ最終検証結果 ===' as section;

WITH field_check AS (
    SELECT 
        SUM(CASE WHEN column_name = 'main_invoice_number' THEN 1 ELSE 0 END) as main_invoice_count,
        SUM(CASE WHEN column_name = 't_number' THEN 1 ELSE 0 END) as t_number_count,
        SUM(CASE WHEN column_name = 'receipt_number' THEN 1 ELSE 0 END) as receipt_number_count,
        SUM(CASE WHEN column_name = 'key_info' THEN 1 ELSE 0 END) as key_info_count
    FROM information_schema.columns 
    WHERE table_schema = 'public' 
    AND table_name IN ('invoices', 'ocr_test_results')
)
SELECT 
    '統一スキーマ検証結果' as check_type,
    CASE 
        WHEN main_invoice_count >= 2 AND t_number_count >= 2 AND receipt_number_count >= 2 AND key_info_count >= 2 
        THEN '🎉 統一化完全成功！'
        ELSE '⚠️ 一部フィールドが不足'
    END as final_result,
    main_invoice_count as main_invoice_fields,
    t_number_count as t_number_fields,
    receipt_number_count as receipt_number_fields,
    key_info_count as key_info_fields
FROM field_check; 