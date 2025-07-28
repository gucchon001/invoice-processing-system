-- ================================================================
-- 本番テーブル構造調査クエリ
-- ================================================================
-- 実行日: 2025年1月22日
-- 目的: Phase 3A実行前の実際のテーブル構造確認

-- 🔍 本番テーブル構造調査開始
-- ====================================

-- ================================================================
-- 1. invoices テーブル構造確認
-- ================================================================

-- 📋 1. invoices テーブル - 全カラム構造
-- --------------------------------------

-- 1-1. 全カラム詳細情報
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
WHERE table_name = 'invoices' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- ================================================================
-- 2. invoice_line_items テーブル構造確認
-- ================================================================

-- 📋 2. invoice_line_items テーブル - 全カラム構造
-- ------------------------------------------------

-- 2-1. invoice_line_itemsテーブルの存在確認
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'invoice_line_items' AND table_schema = 'public') 
        THEN '✅ invoice_line_items: 存在'
        ELSE '❌ invoice_line_items: 不存在'
    END as table_status;

-- 2-2. 存在する場合の詳細構造
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
WHERE table_name = 'invoice_line_items' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- ================================================================
-- 3. 全テーブル一覧確認
-- ================================================================

-- 📋 3. public スキーマ内全テーブル一覧
-- ------------------------------------

SELECT 
    table_name,
    table_type
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- ================================================================
-- 4. OCRテストテーブルとの比較用データ
-- ================================================================

-- 📋 4. OCRテストテーブル vs 本番テーブル カラム比較
-- ---------------------------------------------------

-- 4-1. ocr_test_results の基本情報カラム
SELECT 
    'ocr_test_results' as table_name,
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'ocr_test_results' 
AND column_name IN (
    'issuer_name', 'recipient_name', 'main_invoice_number', 't_number', 
    'receipt_number', 'total_amount_tax_included', 'total_amount_tax_excluded'
)
UNION ALL
-- 4-2. invoices の対応カラム
SELECT 
    'invoices' as table_name,
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'invoices' 
AND column_name IN (
    'issuer', 'issuer_name', 'payer', 'recipient_name', 
    'invoice_number', 'main_invoice_number', 'registration_number', 't_number',
    'receipt_number', 'amount_inclusive_tax', 'total_amount_tax_included',
    'amount_exclusive_tax', 'total_amount_tax_excluded'
)
ORDER BY table_name, column_name;

-- ================================================================
-- 5. インデックス確認
-- ================================================================

-- 📋 5. invoices テーブルインデックス確認
-- --------------------------------------

SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'invoices'
ORDER BY indexname;

-- ✅ 本番テーブル構造調査完了
-- ==================================== 