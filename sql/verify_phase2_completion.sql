-- ================================================================
-- Phase 2マイグレーション完了検証クエリ
-- ================================================================
-- 実行日: 2025年1月22日
-- 目的: ocr_test_tables_alignment_final.sql の実行結果確認

\echo '🔍 Phase 2マイグレーション完了検証開始'
\echo '=============================================='

-- ================================================================
-- 1. テーブル構造確認
-- ================================================================

\echo ''
\echo '📋 1. ocr_test_results テーブル構造確認'
\echo '----------------------------------------'

-- 1-1. 全カラム一覧表示
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'ocr_test_results' 
ORDER BY ordinal_position;

\echo ''
\echo '📋 2. ocr_test_line_items テーブル構造確認'
\echo '--------------------------------------------'

-- 1-2. 全カラム一覧表示
SELECT 
    column_name,
    data_type,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'ocr_test_line_items' 
ORDER BY ordinal_position;

-- ================================================================
-- 2. 特定カラムの存在確認
-- ================================================================

\echo ''
\echo '✅ 3. 重要カラムの存在確認'
\echo '----------------------------'

-- 2-1. ocr_test_results の新規・変更カラム確認
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 't_number') 
        THEN '✅ t_number: 存在'
        ELSE '❌ t_number: 不存在'
    END as t_number_status,
    
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'main_invoice_number') 
        THEN '✅ main_invoice_number: 存在'
        ELSE '❌ main_invoice_number: 不存在'
    END as main_invoice_number_status,
    
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'receipt_number') 
        THEN '✅ receipt_number: 存在'
        ELSE '❌ receipt_number: 不存在'
    END as receipt_number_status,
    
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'key_info') 
        THEN '✅ key_info: 存在'
        ELSE '❌ key_info: 不存在'
    END as key_info_status,
    
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'updated_at') 
        THEN '✅ updated_at: 存在'
        ELSE '❌ updated_at: 不存在'
    END as updated_at_status;

-- 2-2. ocr_test_line_items の変更カラム確認
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_line_items' AND column_name = 'item_description') 
        THEN '✅ item_description: 存在'
        ELSE '❌ item_description: 不存在'
    END as item_description_status,
    
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_line_items' AND column_name = 'tax_rate' AND data_type IN ('numeric', 'decimal')) 
        THEN '✅ tax_rate: DECIMAL型'
        ELSE '❌ tax_rate: DECIMAL型ではない'
    END as tax_rate_type_status;

-- ================================================================
-- 3. 旧カラムの削除確認
-- ================================================================

\echo ''
\echo '🗑️ 4. 旧カラムの削除確認'
\echo '-------------------------'

-- 3-1. 削除されているべき旧カラムの確認
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'registration_number') 
        THEN '✅ registration_number: 正常削除済み'
        ELSE '⚠️ registration_number: まだ存在'
    END as old_registration_number_status,
    
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'invoice_number') 
        THEN '✅ invoice_number: 正常削除済み'
        ELSE '⚠️ invoice_number: まだ存在'
    END as old_invoice_number_status,
    
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_line_items' AND column_name = 'description') 
        THEN '✅ description: 正常削除済み'
        ELSE '⚠️ description: まだ存在'
    END as old_description_status;

-- ================================================================
-- 4. インデックス確認
-- ================================================================

\echo ''
\echo '📊 5. 新規インデックス確認'
\echo '---------------------------'

-- 4-1. 新規追加インデックスの確認
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('ocr_test_results', 'ocr_test_line_items', 'ocr_test_sessions')
AND indexname LIKE '%new%' OR indexname LIKE '%t_number%' OR indexname LIKE '%main_invoice%'
ORDER BY tablename, indexname;

-- ================================================================
-- 5. トリガー確認
-- ================================================================

\echo ''
\echo '⚙️ 6. updated_at トリガー確認'
\echo '------------------------------'

-- 5-1. トリガー関数の存在確認
SELECT 
    routine_name,
    routine_type,
    routine_definition
FROM information_schema.routines 
WHERE routine_name = 'update_updated_at_column';

-- 5-2. トリガーの設定確認
SELECT 
    trigger_name,
    event_manipulation,
    event_object_table,
    action_statement
FROM information_schema.triggers 
WHERE event_object_table = 'ocr_test_results' 
AND trigger_name LIKE '%updated_at%';

-- ================================================================
-- 6. マイグレーション関数確認
-- ================================================================

\echo ''
\echo '🔄 7. マイグレーション関数確認'
\echo '-------------------------------'

-- 6-1. migrate_ocr_test_to_production 関数の確認
SELECT 
    routine_name,
    routine_type,
    external_language
FROM information_schema.routines 
WHERE routine_name = 'migrate_ocr_test_to_production';

-- ================================================================
-- 7. データ整合性確認
-- ================================================================

\echo ''
\echo '📈 8. データ整合性確認'
\echo '-----------------------'

-- 7-1. 基本データ件数
SELECT 
    'ocr_test_sessions' as table_name,
    COUNT(*) as record_count
FROM ocr_test_sessions
UNION ALL
SELECT 
    'ocr_test_results' as table_name,
    COUNT(*) as record_count
FROM ocr_test_results
UNION ALL
SELECT 
    'ocr_test_line_items' as table_name,
    COUNT(*) as record_count
FROM ocr_test_line_items;

-- 7-2. tax_rate データ品質確認
SELECT 
    'tax_rate_stats' as metric,
    COUNT(*) as total_records,
    COUNT(tax_rate) as non_null_count,
    MIN(tax_rate) as min_value,
    MAX(tax_rate) as max_value,
    AVG(tax_rate) as avg_value,
    COUNT(CASE WHEN tax_rate > 50 THEN 1 END) as over_50_count,
    COUNT(CASE WHEN tax_rate < 0 THEN 1 END) as negative_count
FROM ocr_test_line_items;

-- ================================================================
-- 8. 最終判定
-- ================================================================

\echo ''
\echo '🎯 9. Phase 2完了判定'
\echo '----------------------'

-- 8-1. 完了条件チェック
SELECT 
    CASE 
        WHEN (
            -- 必要カラムが全て存在
            EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 't_number') AND
            EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'main_invoice_number') AND
            EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'receipt_number') AND
            EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'key_info') AND
            EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_results' AND column_name = 'updated_at') AND
            EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_line_items' AND column_name = 'item_description') AND
            EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ocr_test_line_items' AND column_name = 'tax_rate' AND data_type IN ('numeric', 'decimal')) AND
            -- マイグレーション関数が存在
            EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_name = 'migrate_ocr_test_to_production')
        ) THEN '🎉 Phase 2: 完全成功 - 全ての変更が適用されました'
        ELSE '⚠️ Phase 2: 未完了 - 一部変更が適用されていません'
    END as phase2_completion_status;

\echo ''
\echo '✅ Phase 2マイグレーション検証完了'
\echo '==============================================' 