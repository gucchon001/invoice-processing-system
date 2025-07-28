-- ================================================================
-- Step 1: 最適化ビュー作成のみ（RAISE NOTICEなし）
-- ================================================================

-- invoices 最適化ビュー
DROP VIEW IF EXISTS invoices_optimized;

CREATE VIEW invoices_optimized AS
SELECT 
    -- 1. 基本識別情報
    id,
    user_email,
    session_id,
    status,
    file_name,
    file_id,
    filename,
    
    -- 2. 請求書コア情報
    issuer_name,
    recipient_name,
    invoice_number,
    registration_number,
    currency,
    issue_date,
    due_date,
    
    -- 3. 金額・計算情報
    total_amount_tax_included,
    total_amount_tax_excluded,
    
    -- 4. 品質・検証情報
    is_valid,
    completeness_score,
    processing_time,
    validation_errors,
    validation_warnings,
    
    -- 5. JSON・拡張データ
    key_info,
    extracted_data,
    raw_response,
    
    -- 6. ファイル・ストレージ情報
    gdrive_file_id,
    file_path,
    file_size,
    
    -- 7. AI・処理情報
    gemini_model,
    
    -- 8. システム管理情報
    uploaded_at,
    created_at,
    updated_at
FROM invoices;

-- ocr_test_results 最適化ビュー
DROP VIEW IF EXISTS ocr_test_results_optimized;

CREATE VIEW ocr_test_results_optimized AS
SELECT 
    -- 1. 基本識別情報
    id,
    session_id,
    file_id,
    filename,
    
    -- 2. 請求書コア情報
    issuer_name,
    recipient_name,
    main_invoice_number,
    t_number,
    receipt_number,
    currency,
    issue_date,
    due_date,
    
    -- 3. 金額・計算情報
    total_amount_tax_included,
    total_amount_tax_excluded,
    
    -- 4. 品質・検証情報
    is_valid,
    completeness_score,
    processing_time,
    validation_errors,
    validation_warnings,
    
    -- 5. JSON・拡張データ
    key_info,
    raw_response,
    
    -- 6. AI・処理情報
    gemini_model,
    
    -- 7. システム管理情報
    created_at,
    updated_at
FROM ocr_test_results;

-- ocr_test_sessions 最適化ビュー
DROP VIEW IF EXISTS ocr_test_sessions_optimized;

CREATE VIEW ocr_test_sessions_optimized AS
SELECT 
    -- 1. 基本識別情報
    id,
    session_name,
    folder_id,
    created_by,
    
    -- 2. 実行統計情報
    total_files,
    processed_files,
    success_files,
    failed_files,
    
    -- 3. 品質統計情報
    average_completeness,
    success_rate,
    processing_duration,
    
    -- 4. システム管理情報
    created_at,
    updated_at
FROM ocr_test_sessions;

-- 所有者設定
ALTER VIEW invoices_optimized OWNER TO postgres;
ALTER VIEW ocr_test_results_optimized OWNER TO postgres;
ALTER VIEW ocr_test_sessions_optimized OWNER TO postgres;

-- コメント追加
COMMENT ON VIEW invoices_optimized IS 'Step 1: 論理的順序最適化された本番請求書ビュー';
COMMENT ON VIEW ocr_test_results_optimized IS 'Step 1: 論理的順序最適化されたOCRテスト結果ビュー';
COMMENT ON VIEW ocr_test_sessions_optimized IS 'Step 1: 論理的順序最適化されたOCRテストセッションビュー'; 