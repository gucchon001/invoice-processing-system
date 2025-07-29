-- 📊 現在のinvoicesテーブル詳細チェック
-- 作成日: 2025-07-28
-- 目的: 実際のテーブルと設計書の差分確認

-- 🔍 Step 1: 現在のinvoicesテーブル全カラム詳細
SELECT 
    '📋 現在のinvoicesテーブル詳細' as table_info,
    ordinal_position as "順序",
    column_name as "カラム名",
    data_type as "データ型",
    CASE 
        WHEN character_maximum_length IS NOT NULL THEN character_maximum_length::text
        WHEN numeric_precision IS NOT NULL THEN numeric_precision::text || ',' || COALESCE(numeric_scale::text, '0')
        ELSE 'N/A'
    END as "サイズ/精度",
    CASE 
        WHEN is_nullable = 'YES' THEN 'NULL可'
        ELSE 'NOT NULL'
    END as "NULL制約",
    COALESCE(column_default, 'なし') as "デフォルト値"
FROM information_schema.columns 
WHERE table_name = 'invoices' 
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- 🔍 Step 2: カラム数統計
SELECT 
    'カラム数統計' as check_type,
    COUNT(*) as current_column_count,
    '設計書では40カラム予定' as design_target
FROM information_schema.columns 
WHERE table_name = 'invoices' 
  AND table_schema = 'public';

-- 🔍 Step 3: 重要カラムの存在確認
SELECT 
    '重要カラム存在確認' as check_type,
    -- 基本識別
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'id') as has_id,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'user_email') as has_user_email,
    
    -- ファイルソース管理
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'source_type') as has_source_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'file_name') as has_file_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'gdrive_file_id') as has_gdrive_file_id,
    
    -- Gmail連携
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'gmail_message_id') as has_gmail_message_id,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'attachment_id') as has_attachment_id,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'sender_email') as has_sender_email,
    
    -- 請求書基本情報
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'main_invoice_number') as has_main_invoice_number,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'receipt_number') as has_receipt_number,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 't_number') as has_t_number,
    
    -- 外貨換算
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'exchange_rate') as has_exchange_rate,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'jpy_amount') as has_jpy_amount,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'card_statement_id') as has_card_statement_id,
    
    -- key_info
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'key_info') as has_key_info,
    
    -- 承認ワークフロー
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'approval_status') as has_approval_status,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'approved_by') as has_approved_by,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'approved_at') as has_approved_at,
    
    -- freee連携
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'exported_to_freee') as has_exported_to_freee,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'export_date') as has_export_date,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'freee_batch_id') as has_freee_batch_id,
    
    -- 削除予定カラム
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'gemini_model') as has_gemini_model,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'final_accounting_info') as has_final_accounting_info;

-- 🔍 Step 4: データ型チェック（重要カラム）
SELECT 
    'データ型チェック' as check_type,
    column_name,
    data_type,
    CASE 
        WHEN character_maximum_length IS NOT NULL THEN character_maximum_length::text
        WHEN numeric_precision IS NOT NULL THEN numeric_precision::text || ',' || COALESCE(numeric_scale::text, '0')
        ELSE 'N/A'
    END as size_precision,
    CASE 
        WHEN column_name = 'source_type' AND data_type = 'character varying' AND character_maximum_length = 20 THEN '✅ 正しい'
        WHEN column_name = 'key_info' AND data_type = 'jsonb' THEN '✅ 正しい'
        WHEN column_name = 'approval_status' AND data_type = 'character varying' AND character_maximum_length = 50 THEN '✅ 正しい'
        WHEN column_name = 'exchange_rate' AND data_type = 'numeric' AND numeric_precision = 10 AND numeric_scale = 4 THEN '✅ 正しい'
        ELSE '要確認'
    END as validation_status
FROM information_schema.columns 
WHERE table_name = 'invoices' 
  AND column_name IN ('source_type', 'key_info', 'approval_status', 'exchange_rate', 'jpy_amount')
ORDER BY column_name;

-- 🔍 Step 5: インデックス確認
SELECT 
    '📊 現在のインデックス一覧' as index_info,
    indexname as "インデックス名",
    indexdef as "インデックス定義"
FROM pg_indexes 
WHERE tablename = 'invoices' 
ORDER BY indexname; 