-- 📋 Step 3: 本番テーブル（invoices）詳細スキーマ
-- 目的: invoicesテーブルの全カラム詳細確認

SELECT 
    '📋 本番テーブル (invoices) スキーマ' as table_info,
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
WHERE table_name = 'invoices' 
ORDER BY ordinal_position; 