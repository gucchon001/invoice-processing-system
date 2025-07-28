-- ================================================================
-- 完全スキーマ検証：実際 vs 期待構造の照合
-- ================================================================

-- ================================================================
-- 1. invoices テーブル完全構造
-- ================================================================
SELECT 
    'invoices' as table_name,
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
-- 2. ocr_test_results テーブル完全構造
-- ================================================================
SELECT 
    'ocr_test_results' as table_name,
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
WHERE table_name = 'ocr_test_results' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- ================================================================
-- 3. ocr_test_line_items テーブル完全構造
-- ================================================================
SELECT 
    'ocr_test_line_items' as table_name,
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
WHERE table_name = 'ocr_test_line_items' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- ================================================================
-- 4. ocr_test_sessions テーブル完全構造
-- ================================================================
SELECT 
    'ocr_test_sessions' as table_name,
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
WHERE table_name = 'ocr_test_sessions' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- ================================================================
-- 5. 作成されたビューの構造確認
-- ================================================================
SELECT 
    table_name as "作成されたビュー名",
    view_definition as "ビュー定義"
FROM information_schema.views 
WHERE table_name LIKE '%_optimized'
ORDER BY table_name;

-- ================================================================
-- 6. 全インデックス一覧
-- ================================================================
SELECT 
    tablename as "テーブル名",
    indexname as "インデックス名",
    indexdef as "インデックス定義"
FROM pg_indexes 
WHERE tablename IN ('invoices', 'ocr_test_results', 'ocr_test_line_items', 'ocr_test_sessions')
ORDER BY tablename, indexname;

-- ================================================================
-- 7. テーブル間カラム比較サマリー
-- ================================================================
SELECT 
    'invoice_number vs main_invoice_number' as "比較項目",
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'invoice_number')
        THEN 'invoices.invoice_number: 存在'
        ELSE 'invoices.invoice_number: 不存在'
    END ||
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'main_invoice_number')
        THEN ' | ocr_test_results.main_invoice_number: 存在'
        ELSE ' | ocr_test_results.main_invoice_number: 不存在'
    END as "存在状況"

UNION ALL

SELECT 
    'registration_number vs t_number' as "比較項目",
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'registration_number')
        THEN 'invoices.registration_number: 存在'
        ELSE 'invoices.registration_number: 不存在'
    END ||
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 't_number')
        THEN ' | ocr_test_results.t_number: 存在'
        ELSE ' | ocr_test_results.t_number: 不存在'
    END as "存在状況"

UNION ALL

SELECT 
    'description vs item_description' as "比較項目",
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_line_items' AND column_name = 'description')
        THEN 'ocr_test_line_items.description: 存在'
        ELSE 'ocr_test_line_items.description: 不存在'
    END ||
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_line_items' AND column_name = 'item_description')
        THEN ' | ocr_test_line_items.item_description: 存在'
        ELSE ' | ocr_test_line_items.item_description: 不存在'
    END as "存在状況"

UNION ALL

SELECT 
    'tax_rate data_type' as "比較項目",
    (SELECT data_type FROM information_schema.columns 
     WHERE table_name = 'ocr_test_line_items' AND column_name = 'tax_rate') as "存在状況"

UNION ALL

SELECT 
    'file_size削除確認' as "比較項目",
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'file_size')
        THEN '✅ 正常削除済み'
        ELSE '❌ まだ存在'
    END as "存在状況";

-- ================================================================
-- 8. 重要フィールドの存在確認
-- ================================================================
SELECT 
    'Phase 2統一化確認' as "検証カテゴリ",
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 't_number') AND
             EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'main_invoice_number') AND
             EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'receipt_number') AND
             EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'key_info') AND
             EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'updated_at') AND
             EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_line_items' AND column_name = 'item_description') AND
             EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_line_items' AND column_name = 'tax_rate' AND data_type IN ('numeric', 'decimal'))
        THEN '✅ Phase 2統一化完全成功'
        ELSE '❌ Phase 2統一化未完了'
    END as "検証結果"

UNION ALL

SELECT 
    'Phase 3A最適化確認' as "検証カテゴリ",
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'invoices_optimized') AND
             EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'ocr_test_results_optimized') AND
             EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'ocr_test_sessions_optimized') AND
             EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_invoices_user_status_created') AND
             EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_ocr_results_session_valid_score') AND
             NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'file_size')
        THEN '✅ Phase 3A最適化完全成功'
        ELSE '❌ Phase 3A最適化未完了'
    END as "検証結果"; 