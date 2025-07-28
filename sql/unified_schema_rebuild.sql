-- ===================================================
-- 統一スキーマ完全再構築スクリプト
-- master_data/tables.yml 統一定義に基づく
-- ===================================================

-- 【重要】このスクリプトは既存データを完全に削除します
-- 実行前に必要に応じてバックアップを取得してください

BEGIN;

-- ===============================================
-- Phase 1: 既存テーブル削除（依存関係考慮）
-- ===============================================

-- 明細テーブルから削除（外部キー制約のため）
DROP TABLE IF EXISTS invoice_line_items CASCADE;
DROP TABLE IF EXISTS ocr_test_line_items CASCADE;

-- メインテーブル削除
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS ocr_test_results CASCADE;
DROP TABLE IF EXISTS ocr_test_sessions CASCADE;

-- Phase 3で作成された最適化ビューも削除
DROP VIEW IF EXISTS invoices_optimized CASCADE;
DROP VIEW IF EXISTS ocr_test_results_optimized CASCADE;
DROP VIEW IF EXISTS ocr_test_sessions_optimized CASCADE;

-- ===============================================
-- Phase 2: 本番テーブル再作成（統一スキーマ）
-- ===============================================

-- 2.1 invoices テーブル（統一化済みスキーマ）
CREATE TABLE public.invoices (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email),
    status VARCHAR(50) DEFAULT 'uploaded',
    file_name VARCHAR(255) NOT NULL,
    gdrive_file_id VARCHAR(255),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 請求書基本情報（統一化済みフィールド名）
    issuer_name VARCHAR(255),
    recipient_name VARCHAR(255),
    main_invoice_number VARCHAR(255),        -- 統一化: invoice_number → main_invoice_number
    receipt_number VARCHAR(255),             -- 統一化: 新規追加
    t_number VARCHAR(50),                    -- 統一化: registration_number → t_number
    issue_date DATE,
    due_date DATE,
    currency VARCHAR(10) DEFAULT 'JPY',
    
    -- 金額情報
    total_amount_tax_included DECIMAL(15,2),
    total_amount_tax_excluded DECIMAL(15,2),
    
    -- JSON情報（統一化済み）
    key_info JSONB,                          -- 統一化: 新規追加
    final_accounting_info JSONB,
    extracted_data JSONB,
    raw_response JSONB,
    
    -- 検証・品質管理
    is_valid BOOLEAN DEFAULT TRUE,
    validation_errors TEXT[],
    validation_warnings TEXT[],
    completeness_score DECIMAL(5,2),
    processing_time DECIMAL(8,2),
    
    -- システム管理
    file_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Tokyo', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Tokyo', NOW())
);

-- 2.2 invoice_line_items テーブル（統一化済みスキーマ）
CREATE TABLE public.invoice_line_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    item_description TEXT,                   -- 統一化: description → item_description
    quantity DECIMAL(10,3),
    unit_price DECIMAL(15,2),
    amount DECIMAL(15,2),
    tax_rate DECIMAL(5,2),                   -- 統一化: VARCHAR(10) → DECIMAL(5,2)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Tokyo', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Tokyo', NOW()),
    UNIQUE(invoice_id, line_number)
);

-- ===============================================
-- Phase 3: OCRテストテーブル再作成（統一スキーマ）
-- ===============================================

-- 3.1 ocr_test_sessions テーブル（統一化済みスキーマ）
CREATE TABLE IF NOT EXISTS ocr_test_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_name VARCHAR(255) NOT NULL,
    folder_id VARCHAR(255) NOT NULL,
    total_files INTEGER NOT NULL DEFAULT 0,
    processed_files INTEGER NOT NULL DEFAULT 0,
    success_files INTEGER NOT NULL DEFAULT 0,
    failed_files INTEGER NOT NULL DEFAULT 0,
    average_completeness DECIMAL(5,2),
    success_rate DECIMAL(5,2),
    processing_duration DECIMAL(10,2),
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3.2 ocr_test_results テーブル（統一化済みスキーマ）
CREATE TABLE IF NOT EXISTS ocr_test_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES ocr_test_sessions(id) ON DELETE CASCADE,
    file_id VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    
    -- OCR抽出結果（本番テーブルと統一）
    issuer_name VARCHAR(255),
    recipient_name VARCHAR(255),
    main_invoice_number VARCHAR(255),        -- 統一化: invoice_number → main_invoice_number
    receipt_number VARCHAR(255),             -- 統一化: 新規追加
    t_number VARCHAR(50),                    -- 統一化: registration_number → t_number
    currency VARCHAR(10),
    total_amount_tax_included DECIMAL(15,2),
    total_amount_tax_excluded DECIMAL(15,2),
    issue_date DATE,
    due_date DATE,
    key_info JSONB,                          -- 統一化: 新規追加
    
    -- 検証結果
    is_valid BOOLEAN DEFAULT FALSE,
    completeness_score DECIMAL(5,2),
    validation_errors TEXT[],
    validation_warnings TEXT[],
    
    -- メタデータ
    processing_time DECIMAL(8,2),
    gemini_model VARCHAR(50) DEFAULT 'gemini-2.5-flash-lite-preview-06-17',
    raw_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3.3 ocr_test_line_items テーブル（統一化済みスキーマ）
CREATE TABLE IF NOT EXISTS ocr_test_line_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    result_id UUID REFERENCES ocr_test_results(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    item_description TEXT,                   -- 統一化: description → item_description
    quantity DECIMAL(10,3),
    unit_price DECIMAL(15,2),
    amount DECIMAL(15,2),
    tax_rate DECIMAL(5,2),                   -- 統一化: VARCHAR(10) → DECIMAL(5,2)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ===============================================
-- Phase 4: インデックス作成（パフォーマンス最適化）
-- ===============================================

-- 4.1 invoices テーブルインデックス
CREATE INDEX IF NOT EXISTS idx_invoices_user_email ON invoices(user_email);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_uploaded_at ON invoices(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_invoices_currency ON invoices(currency);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(main_invoice_number);  -- 統一化フィールド
CREATE INDEX IF NOT EXISTS idx_invoices_is_valid ON invoices(is_valid);
CREATE INDEX IF NOT EXISTS idx_invoices_issue_date ON invoices(issue_date);
CREATE INDEX IF NOT EXISTS idx_invoices_issuer_name ON invoices(issuer_name);
CREATE INDEX IF NOT EXISTS idx_invoices_total_amount ON invoices(total_amount_tax_included);
CREATE INDEX IF NOT EXISTS idx_invoices_gdrive_file_id ON invoices(gdrive_file_id);

-- JSON インデックス
CREATE INDEX IF NOT EXISTS idx_invoices_key_info_gin ON invoices USING gin (key_info);
CREATE INDEX IF NOT EXISTS idx_invoices_extracted_data_gin ON invoices USING gin (extracted_data);
CREATE INDEX IF NOT EXISTS idx_invoices_raw_response_gin ON invoices USING gin (raw_response);

-- 4.2 invoice_line_items テーブルインデックス
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice_id ON invoice_line_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_line_number ON invoice_line_items(line_number);

-- 4.3 OCRテストテーブルインデックス
CREATE INDEX IF NOT EXISTS idx_ocr_test_sessions_created_by ON ocr_test_sessions(created_by);
CREATE INDEX IF NOT EXISTS idx_ocr_test_sessions_created_at ON ocr_test_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_session_id ON ocr_test_results(session_id);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_filename ON ocr_test_results(filename);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_issuer_name ON ocr_test_results(issuer_name);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_is_valid ON ocr_test_results(is_valid);
CREATE INDEX IF NOT EXISTS idx_ocr_test_line_items_result_id ON ocr_test_line_items(result_id);

-- 複合インデックス（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_invoices_user_status_created ON invoices(user_email, status, created_at);
CREATE INDEX IF NOT EXISTS idx_ocr_results_session_valid_score ON ocr_test_results(session_id, is_valid, completeness_score);

-- ===============================================
-- Phase 5: updated_at 自動更新トリガー設定
-- ===============================================

-- トリガー関数作成
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('Asia/Tokyo', NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- invoices テーブルトリガー
DROP TRIGGER IF EXISTS update_invoices_updated_at ON invoices;
CREATE TRIGGER update_invoices_updated_at
    BEFORE UPDATE ON invoices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- invoice_line_items テーブルトリガー
DROP TRIGGER IF EXISTS update_invoice_line_items_updated_at ON invoice_line_items;
CREATE TRIGGER update_invoice_line_items_updated_at
    BEFORE UPDATE ON invoice_line_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ocr_test_results テーブルトリガー
DROP TRIGGER IF EXISTS update_ocr_test_results_updated_at ON ocr_test_results;
CREATE TRIGGER update_ocr_test_results_updated_at
    BEFORE UPDATE ON ocr_test_results
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ocr_test_line_items テーブルトリガー
DROP TRIGGER IF EXISTS update_ocr_test_line_items_updated_at ON ocr_test_line_items;
CREATE TRIGGER update_ocr_test_line_items_updated_at
    BEFORE UPDATE ON ocr_test_line_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ocr_test_sessions テーブルトリガー
DROP TRIGGER IF EXISTS update_ocr_test_sessions_updated_at ON ocr_test_sessions;
CREATE TRIGGER update_ocr_test_sessions_updated_at
    BEFORE UPDATE ON ocr_test_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===============================================
-- Phase 6: RLS (Row Level Security) 設定
-- ===============================================

-- RLS有効化
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_line_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_test_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_test_line_items ENABLE ROW LEVEL SECURITY;

-- RLSポリシー設定
-- invoices テーブル: ユーザーは自分のデータのみアクセス可能
DROP POLICY IF EXISTS "Users can manage their own invoices" ON invoices;
CREATE POLICY "Users can manage their own invoices" ON invoices
    FOR ALL USING (auth.jwt() ->> 'email' = user_email);

-- invoice_line_items テーブル: 関連するinvoicesの所有者のみアクセス可能
DROP POLICY IF EXISTS "Users can manage their own invoice line items" ON invoice_line_items;
CREATE POLICY "Users can manage their own invoice line items" ON invoice_line_items
    FOR ALL USING (
        invoice_id IN (
            SELECT id FROM invoices 
            WHERE user_email = auth.jwt() ->> 'email'
        )
    );

-- OCRテスト関連ポリシー
DROP POLICY IF EXISTS "Users can manage their own ocr sessions" ON ocr_test_sessions;
CREATE POLICY "Users can manage their own ocr sessions" ON ocr_test_sessions
    FOR ALL USING (auth.jwt() ->> 'email' = created_by);

DROP POLICY IF EXISTS "Users can manage their own ocr results" ON ocr_test_results;
CREATE POLICY "Users can manage their own ocr results" ON ocr_test_results
    FOR ALL USING (
        session_id IN (
            SELECT id FROM ocr_test_sessions 
            WHERE created_by = auth.jwt() ->> 'email'
        )
    );

DROP POLICY IF EXISTS "Users can manage their own ocr line items" ON ocr_test_line_items;
CREATE POLICY "Users can manage their own ocr line items" ON ocr_test_line_items
    FOR ALL USING (
        result_id IN (
            SELECT r.id FROM ocr_test_results r
            JOIN ocr_test_sessions s ON r.session_id = s.id
            WHERE s.created_by = auth.jwt() ->> 'email'
        )
    );

-- ===============================================
-- 統一スキーマ再構築完了確認
-- ===============================================

-- テーブル一覧確認
SELECT 
    '=== 統一スキーマ再構築完了確認 ===' as message,
    COUNT(*) as created_tables
FROM pg_tables 
WHERE schemaname = 'public'
AND tablename IN ('invoices', 'invoice_line_items', 'ocr_test_sessions', 'ocr_test_results', 'ocr_test_line_items');

-- 統一化フィールド確認
SELECT 
    '=== 統一化フィールド確認 ===' as message,
    'invoices' as table_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'main_invoice_number') 
        THEN '✅ main_invoice_number 存在'
        ELSE '❌ main_invoice_number 不存在'
    END as main_invoice_number_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 't_number') 
        THEN '✅ t_number 存在'
        ELSE '❌ t_number 不存在'
    END as t_number_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'receipt_number') 
        THEN '✅ receipt_number 存在'
        ELSE '❌ receipt_number 不存在'
    END as receipt_number_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'key_info') 
        THEN '✅ key_info 存在'
        ELSE '❌ key_info 不存在'
    END as key_info_status;

COMMIT;

-- ===============================================
-- 再構築完了メッセージ
-- ===============================================
SELECT '🎉 統一スキーマ完全再構築が完了しました！' as completion_message; 