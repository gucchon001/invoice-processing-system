-- ===================================================
-- 明細テーブル詳細調査スクリプト
-- invoice_line_items vs ocr_test_line_items
-- ===================================================

-- 1. 明細テーブル存在確認
SELECT 
    '=== 明細テーブル存在確認 ===' as section;

SELECT 
    schemaname,
    tablename,
    CASE 
        WHEN tablename LIKE '%line_items%' THEN '📊 明細テーブル'
        ELSE '🔍 その他'
    END as table_type
FROM pg_tables 
WHERE schemaname = 'public'
AND tablename LIKE '%line_items%'
ORDER BY tablename;

-- 2. invoice_line_items テーブル構造詳細
SELECT 
    '=== invoice_line_items テーブル構造 ===' as section;

SELECT 
    ordinal_position,
    column_name,
    data_type,
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'invoice_line_items'
ORDER BY ordinal_position;

-- 3. ocr_test_line_items テーブル構造詳細
SELECT 
    '=== ocr_test_line_items テーブル構造 ===' as section;

SELECT 
    ordinal_position,
    column_name,
    data_type,
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'ocr_test_line_items'
ORDER BY ordinal_position;

-- 4. 明細テーブルのデータ件数とサンプル
SELECT 
    '=== 明細テーブルのデータ件数 ===' as section;

-- データ件数確認
SELECT 
    'invoice_line_items' as table_name,
    COUNT(*) as row_count
FROM invoice_line_items
UNION ALL
SELECT 
    'ocr_test_line_items' as table_name,
    COUNT(*) as row_count
FROM ocr_test_line_items;

-- 5. invoice_line_items サンプルデータ（最新5件）
SELECT 
    '=== invoice_line_items サンプルデータ ===' as section;

SELECT 
    id,
    invoice_id,
    line_number,
    CASE 
        WHEN LENGTH(COALESCE(description, item_description, '')) > 50 
        THEN LEFT(COALESCE(description, item_description, ''), 50) || '...'
        ELSE COALESCE(description, item_description, '')
    END as description_sample,
    quantity,
    unit_price,
    amount,
    tax_rate,
    created_at
FROM invoice_line_items
ORDER BY created_at DESC
LIMIT 5;

-- 6. ocr_test_line_items サンプルデータ（最新5件）
SELECT 
    '=== ocr_test_line_items サンプルデータ ===' as section;

SELECT 
    id,
    result_id,
    line_number,
    CASE 
        WHEN LENGTH(COALESCE(description, item_description, '')) > 50 
        THEN LEFT(COALESCE(description, item_description, ''), 50) || '...'
        ELSE COALESCE(description, item_description, '')
    END as description_sample,
    quantity,
    unit_price,
    amount,
    tax_rate,
    created_at
FROM ocr_test_line_items
ORDER BY created_at DESC
LIMIT 5;

-- 7. 明細テーブル フィールド名比較（重要）
SELECT 
    '=== 明細テーブル フィールド名比較 ===' as section;

WITH invoice_line_cols AS (
    SELECT column_name, ordinal_position, data_type
    FROM information_schema.columns 
    WHERE table_schema = 'public' AND table_name = 'invoice_line_items'
),
ocr_line_cols AS (
    SELECT column_name, ordinal_position, data_type
    FROM information_schema.columns 
    WHERE table_schema = 'public' AND table_name = 'ocr_test_line_items'
)
SELECT 
    'invoice_line_items vs ocr_test_line_items' as comparison,
    COALESCE(i.column_name, '---') as invoice_line_items_column,
    COALESCE(i.data_type, '---') as invoice_type,
    COALESCE(o.column_name, '---') as ocr_test_line_items_column,
    COALESCE(o.data_type, '---') as ocr_type,
    CASE 
        WHEN i.column_name = o.column_name AND i.data_type = o.data_type THEN '✓ 完全一致'
        WHEN i.column_name = o.column_name AND i.data_type != o.data_type THEN '⚠️ 名前一致・型不一致'
        WHEN i.column_name IS NULL THEN '← OCRのみ'
        WHEN o.column_name IS NULL THEN 'invoiceのみ →'
        ELSE '× 名前不一致'
    END as status
FROM invoice_line_cols i
FULL OUTER JOIN ocr_line_cols o ON i.ordinal_position = o.ordinal_position
ORDER BY COALESCE(i.ordinal_position, o.ordinal_position);

-- 8. 重要フィールドの具体的比較
SELECT 
    '=== 重要フィールドの詳細比較 ===' as section;

-- description vs item_description の存在確認
SELECT 
    'description vs item_description 存在確認' as check_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoice_line_items' AND column_name = 'description') as invoice_has_description,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoice_line_items' AND column_name = 'item_description') as invoice_has_item_description,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_line_items' AND column_name = 'description') as ocr_has_description,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'ocr_test_line_items' AND column_name = 'item_description') as ocr_has_item_description;

-- tax_rate データ型の確認
SELECT 
    'tax_rate データ型確認' as check_type,
    (SELECT data_type || '(' || COALESCE(character_maximum_length::text, numeric_precision::text || ',' || numeric_scale::text) || ')' 
     FROM information_schema.columns 
     WHERE table_name = 'invoice_line_items' AND column_name = 'tax_rate') as invoice_tax_rate_type,
    (SELECT data_type || '(' || COALESCE(character_maximum_length::text, numeric_precision::text || ',' || numeric_scale::text) || ')' 
     FROM information_schema.columns 
     WHERE table_name = 'ocr_test_line_items' AND column_name = 'tax_rate') as ocr_tax_rate_type;

-- 9. 外部キー関係の確認
SELECT 
    '=== 明細テーブル外部キー関係 ===' as section;

SELECT
    tc.table_name,
    tc.constraint_name,
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
AND tc.table_name IN ('invoice_line_items', 'ocr_test_line_items');

-- 10. 明細テーブルのインデックス
SELECT 
    '=== 明細テーブルのインデックス ===' as section;

SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
AND tablename IN ('invoice_line_items', 'ocr_test_line_items')
ORDER BY tablename, indexname; 