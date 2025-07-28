-- ================================================================
-- テーブル構造詳細比較クエリ
-- ================================================================
-- 実行日: 2025年1月22日
-- 目的: invoicesテーブル構造確認 & OCRテストテーブルとの比較

-- ================================================================
-- 1. invoices テーブル - 全カラム詳細
-- ================================================================

-- 📋 invoices テーブル全カラム構造
SELECT 
    ordinal_position as "順序",
    column_name as "カラム名",
    data_type as "データ型",
    COALESCE(character_maximum_length::text, 
             CASE WHEN numeric_precision IS NOT NULL 
                  THEN numeric_precision::text || ',' || numeric_scale::text 
                  ELSE 'N/A' END) as "サイズ/精度",
    CASE WHEN is_nullable = 'YES' THEN 'NULL可' ELSE 'NOT NULL' END as "NULL制約",
    COALESCE(column_default, 'なし') as "デフォルト値"
FROM information_schema.columns 
WHERE table_name = 'invoices' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- ================================================================
-- 2. OCRテストテーブル vs 本番テーブル カラム対応表
-- ================================================================

-- 📋 カラム名対応表（OCR → 本番）
WITH ocr_columns AS (
    SELECT 
        'ocr_test_results' as source_table,
        column_name,
        data_type,
        character_maximum_length
    FROM information_schema.columns 
    WHERE table_name = 'ocr_test_results' 
    AND table_schema = 'public'
),
production_columns AS (
    SELECT 
        'invoices' as source_table,
        column_name,
        data_type,
        character_maximum_length
    FROM information_schema.columns 
    WHERE table_name = 'invoices' 
    AND table_schema = 'public'
),
column_mapping AS (
    -- 手動マッピング定義
    SELECT * FROM (VALUES
        ('issuer_name', 'issuer_name', '✅ 一致'),
        ('recipient_name', 'recipient_name', '✅ 一致'),
        ('main_invoice_number', 'invoice_number', '⚠️ 名前違い'),
        ('t_number', 'registration_number', '⚠️ 名前違い'),
        ('receipt_number', 'receipt_number', '✅ 一致'),
        ('total_amount_tax_included', 'total_amount_tax_included', '✅ 一致'),
        ('total_amount_tax_excluded', 'total_amount_tax_excluded', '✅ 一致'),
        ('key_info', 'key_info', '✅ 一致'),
        ('updated_at', 'updated_at', '✅ 一致'),
        ('extracted_data', 'extracted_data', 'OCRのみ'),
        ('raw_response', 'raw_response', 'OCRのみ'),
        ('session_id', 'session_id', '本番のみ'),
        ('file_id', 'file_id', '本番のみ')
    ) AS mapping(ocr_column, production_column, status)
)
SELECT 
    cm.ocr_column as "OCRテーブルカラム",
    cm.production_column as "本番テーブルカラム",
    cm.status as "対応状況",
    ocr.data_type as "OCR型",
    prod.data_type as "本番型",
    CASE 
        WHEN ocr.data_type = prod.data_type THEN '✅ 一致'
        WHEN ocr.data_type IS NULL THEN '❌ OCRに無し'
        WHEN prod.data_type IS NULL THEN '❌ 本番に無し'
        ELSE '⚠️ 型違い'
    END as "型チェック"
FROM column_mapping cm
LEFT JOIN ocr_columns ocr ON ocr.column_name = cm.ocr_column
LEFT JOIN production_columns prod ON prod.column_name = cm.production_column
ORDER BY cm.status, cm.ocr_column;

-- ================================================================
-- 3. カラム存在チェック（Phase 3A用）
-- ================================================================

-- 📋 Phase 3A実行に必要なカラム存在確認
SELECT 
    'invoices テーブル必要カラム確認' as "チェック項目",
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'issuer_name') 
         THEN '✅ issuer_name' ELSE '❌ issuer_name' END ||
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'recipient_name') 
         THEN ', ✅ recipient_name' ELSE ', ❌ recipient_name' END ||
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'invoice_number') 
         THEN ', ✅ invoice_number' ELSE ', ❌ invoice_number' END ||
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'registration_number') 
         THEN ', ✅ registration_number' ELSE ', ❌ registration_number' END ||
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'total_amount_tax_included') 
         THEN ', ✅ total_amount_tax_included' ELSE ', ❌ total_amount_tax_included' END as "結果";

-- ================================================================
-- 4. テーブル間の具体的差分
-- ================================================================

-- 📋 OCRテストテーブルにあって本番テーブルにないカラム
SELECT 
    'OCRテーブル固有カラム' as "分類",
    ocr.column_name as "カラム名",
    ocr.data_type as "データ型"
FROM information_schema.columns ocr
WHERE ocr.table_name = 'ocr_test_results'
AND ocr.table_schema = 'public'
AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns prod
    WHERE prod.table_name = 'invoices' 
    AND prod.table_schema = 'public'
    AND prod.column_name = ocr.column_name
)

UNION ALL

-- 📋 本番テーブルにあってOCRテストテーブルにないカラム
SELECT 
    '本番テーブル固有カラム' as "分類",
    prod.column_name as "カラム名",
    prod.data_type as "データ型"
FROM information_schema.columns prod
WHERE prod.table_name = 'invoices'
AND prod.table_schema = 'public'
AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns ocr
    WHERE ocr.table_name = 'ocr_test_results' 
    AND ocr.table_schema = 'public'
    AND ocr.column_name = prod.column_name
)
ORDER BY "分類", "カラム名";

-- ================================================================
-- 5. データ件数確認
-- ================================================================

-- 📋 各テーブルのデータ件数
SELECT 
    'invoices' as "テーブル名",
    COUNT(*) as "レコード数",
    MIN(id) as "最小ID",
    MAX(id) as "最大ID"
FROM invoices

UNION ALL

SELECT 
    'ocr_test_results' as "テーブル名",
    COUNT(*) as "レコード数",
    'UUID' as "最小ID",
    'UUID' as "最大ID"
FROM ocr_test_results; 