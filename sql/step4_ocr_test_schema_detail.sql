-- 📋 Step 4: テストテーブル（ocr_test_results）詳細スキーマ
-- 目的: ocr_test_resultsテーブルの全カラム詳細確認

SELECT 
    '📋 テストテーブル (ocr_test_results) スキーマ' as table_info,
    ordinal_position as "順序",
    column_name as "カラム名",
    data_type as "データ型",
    COALESCE(character_maximum_length::text, numeric_precision::text || ',' || numeric_scale::text) as "サイズ/精度",
    CASE 
        WHEN is_nullable = 'YES' THEN 'NULL可'
        ELSE 'NOT NULL'
    END as "NULL制約",
    COALESCE(column_default, 'なし') as "デフォルト値"
FROM information_schema.columns 
WHERE table_name = 'ocr_test_results' 
ORDER BY ordinal_position; 