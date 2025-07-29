-- 📋 レプリケーション：テストテーブル設計
-- 作成日: 2025-07-28
-- 目的: invoicesテーブルからocr_test_resultsをレプリケーション作成
-- 方針: 完全一致保証 + テスト固有機能追加

-- 既存テーブル削除
DROP TABLE IF EXISTS ocr_test_results CASCADE;

CREATE TABLE public.ocr_test_results (
    -- 🔑 基本キー・識別（テスト用にUUID）
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES ocr_test_sessions(id) ON DELETE CASCADE,  -- テスト固有
    user_email VARCHAR(255) NOT NULL,
    
    -- 📁 ファイル・ソース管理（invoicesと同一）
    source_type VARCHAR(20) DEFAULT 'local' CHECK (source_type IN ('local', 'gdrive', 'gmail')),
    file_name VARCHAR(255) NOT NULL,
    gdrive_file_id VARCHAR(255),
    file_path VARCHAR(500),
    
    -- 📧 Gmail連携（invoicesと同一）
    gmail_message_id VARCHAR(255),
    attachment_id VARCHAR(255), 
    sender_email VARCHAR(255),
    
    -- 📈 処理状況・時系列（invoicesと同一）
    status VARCHAR(50) DEFAULT 'uploaded' CHECK (status IN (
        'uploaded', 'processing', 'extracted', 'validated', 
        'approved', 'rejected', 'failed', 'exported'
    )),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 📄 請求書基本情報（invoicesと同一）
    issuer_name VARCHAR(255),
    recipient_name VARCHAR(255), 
    main_invoice_number VARCHAR(255),
    receipt_number VARCHAR(255),              -- ✅ 返金処理等で必要
    t_number VARCHAR(50),                     -- 適格請求書発行事業者登録番号
    issue_date DATE,
    due_date DATE,
    
    -- 💰 金額・通貨情報（invoicesと同一）
    currency VARCHAR(10) DEFAULT 'JPY',
    total_amount_tax_included DECIMAL(15,2),
    total_amount_tax_excluded DECIMAL(15,2),
    
    -- 💱 外貨換算（invoicesと同一）
    exchange_rate DECIMAL(10,4),
    jpy_amount DECIMAL(15,2),
    card_statement_id VARCHAR(255),
    
    -- 🤖 AI処理・検証結果（invoicesと同一）
    extracted_data JSONB,
    raw_response JSONB,
    key_info JSONB,                          -- ✅ プロンプト仕様書準拠
    is_valid BOOLEAN DEFAULT TRUE,
    validation_errors TEXT[],
    validation_warnings TEXT[],
    completeness_score DECIMAL(5,2),         -- ✅ 品質評価
    processing_time DECIMAL(8,2),            -- ✅ AI性能監視
    
    -- 🧪 テスト固有カラム
    gemini_model VARCHAR(50) DEFAULT 'gemini-2.5-flash-lite-preview-06-17',  -- テスト用
    file_size BIGINT,                        -- テスト性能分析用
    test_batch_name VARCHAR(255),            -- テストバッチ名
    
    -- ❌ 本番専用カラムは除外
    -- approval_status, approved_by, approved_at (承認ワークフローはテスト不要)
    -- exported_to_freee, export_date, freee_batch_id (freee連携はテスト不要)
    
    -- 📅 監査・追跡（invoicesと同一）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 📊 コメント追加
COMMENT ON TABLE ocr_test_results IS 'OCRテスト結果テーブル。invoicesテーブルからレプリケーション作成。';
COMMENT ON COLUMN ocr_test_results.session_id IS 'OCRテストセッション管理用';
COMMENT ON COLUMN ocr_test_results.gemini_model IS 'テスト用Geminiモデル識別';
COMMENT ON COLUMN ocr_test_results.file_size IS 'テスト性能分析用ファイルサイズ';
COMMENT ON COLUMN ocr_test_results.test_batch_name IS 'テストバッチ名';

-- 🔍 インデックス作成（invoicesベース + テスト固有）
CREATE INDEX idx_ocr_test_results_session_id ON ocr_test_results(session_id);
CREATE INDEX idx_ocr_test_results_user_email ON ocr_test_results(user_email);
CREATE INDEX idx_ocr_test_results_status ON ocr_test_results(status);
CREATE INDEX idx_ocr_test_results_source_type ON ocr_test_results(source_type);
CREATE INDEX idx_ocr_test_results_gemini_model ON ocr_test_results(gemini_model);
CREATE INDEX idx_ocr_test_results_created_at ON ocr_test_results(created_at);
CREATE INDEX idx_ocr_test_results_file_size ON ocr_test_results(file_size) WHERE file_size IS NOT NULL;

-- 🔍 JSONB専用インデックス
CREATE GIN INDEX idx_ocr_test_results_extracted_data ON ocr_test_results USING gin(extracted_data);
CREATE GIN INDEX idx_ocr_test_results_key_info ON ocr_test_results USING gin(key_info);

-- 🔒 RLS設定
ALTER TABLE ocr_test_results ENABLE ROW LEVEL SECURITY;

-- 📝 更新トリガー
CREATE OR REPLACE FUNCTION update_ocr_test_results_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ocr_test_results_updated_at
    BEFORE UPDATE ON ocr_test_results
    FOR EACH ROW
    EXECUTE FUNCTION update_ocr_test_results_updated_at();

-- 📊 レプリケーション検証
SELECT 
    'ocr_test_resultsレプリケーション完了' as status,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'invoices') as invoices_columns,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'ocr_test_results') as ocr_test_columns,
    'レプリケーション成功（テスト固有カラム追加）' as note; 