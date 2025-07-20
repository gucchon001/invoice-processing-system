-- OCRテスト結果保存用テーブル
-- Gemini 2.0-flashによるOCR処理結果を記録

-- OCRテスト実行履歴テーブル
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
    processing_duration DECIMAL(10,2), -- 秒数
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OCR処理結果詳細テーブル
CREATE TABLE IF NOT EXISTS ocr_test_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES ocr_test_sessions(id) ON DELETE CASCADE,
    file_id VARCHAR(255) NOT NULL, -- Google Drive File ID
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT,
    
    -- OCR抽出結果
    issuer_name VARCHAR(255),
    recipient_name VARCHAR(255),
    invoice_number VARCHAR(100),
    registration_number VARCHAR(50),
    currency VARCHAR(10),
    total_amount_tax_included DECIMAL(15,2),
    total_amount_tax_excluded DECIMAL(15,2),
    issue_date DATE,
    due_date DATE,
    
    -- 検証結果
    is_valid BOOLEAN DEFAULT FALSE,
    completeness_score DECIMAL(5,2),
    validation_errors TEXT[], -- エラーメッセージの配列
    validation_warnings TEXT[], -- 警告メッセージの配列
    
    -- メタデータ
    processing_time DECIMAL(8,2), -- 処理時間（秒）
    gemini_model VARCHAR(50) DEFAULT 'gemini-2.0-flash-exp',
    raw_response JSONB, -- 生のGemini APIレスポンス
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OCR抽出明細テーブル
CREATE TABLE IF NOT EXISTS ocr_test_line_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    result_id UUID REFERENCES ocr_test_results(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    description TEXT,
    quantity DECIMAL(10,3),
    unit_price DECIMAL(15,2),
    amount DECIMAL(15,2),
    tax_rate VARCHAR(10),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_ocr_test_sessions_created_by ON ocr_test_sessions(created_by);
CREATE INDEX IF NOT EXISTS idx_ocr_test_sessions_created_at ON ocr_test_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_session_id ON ocr_test_results(session_id);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_filename ON ocr_test_results(filename);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_issuer_name ON ocr_test_results(issuer_name);
CREATE INDEX IF NOT EXISTS idx_ocr_test_line_items_result_id ON ocr_test_line_items(result_id);

-- RLS (Row Level Security) 設定
ALTER TABLE ocr_test_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_test_line_items ENABLE ROW LEVEL SECURITY;

-- ユーザーは自分が作成したデータのみアクセス可能
CREATE POLICY ocr_test_sessions_user_policy ON ocr_test_sessions
    FOR ALL USING (auth.jwt() ->> 'email' = created_by);

CREATE POLICY ocr_test_results_user_policy ON ocr_test_results
    FOR ALL USING (
        session_id IN (
            SELECT id FROM ocr_test_sessions 
            WHERE created_by = auth.jwt() ->> 'email'
        )
    );

CREATE POLICY ocr_test_line_items_user_policy ON ocr_test_line_items
    FOR ALL USING (
        result_id IN (
            SELECT r.id FROM ocr_test_results r
            JOIN ocr_test_sessions s ON r.session_id = s.id
            WHERE s.created_by = auth.jwt() ->> 'email'
        )
    );

-- トリガー関数（updated_atの自動更新）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- トリガー設定
CREATE TRIGGER update_ocr_test_sessions_updated_at 
    BEFORE UPDATE ON ocr_test_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ocr_test_results_updated_at 
    BEFORE UPDATE ON ocr_test_results 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- サンプルデータ挿入用関数
CREATE OR REPLACE FUNCTION insert_sample_ocr_test_data()
RETURNS VOID AS $$
DECLARE
    sample_session_id UUID;
    sample_result_id UUID;
BEGIN
    -- サンプルセッション
    INSERT INTO ocr_test_sessions (
        session_name, folder_id, total_files, processed_files, 
        success_files, failed_files, average_completeness, 
        success_rate, processing_duration, created_by
    ) VALUES (
        'サンプルOCRテスト', '1ZCJsI9j8A9VJcmiY79BcP1jgzsD51X6E', 
        3, 3, 2, 1, 85.5, 66.7, 45.2, 'test@example.com'
    ) RETURNING id INTO sample_session_id;
    
    -- サンプル結果1
    INSERT INTO ocr_test_results (
        session_id, file_id, filename, file_size,
        issuer_name, recipient_name, invoice_number, currency,
        total_amount_tax_included, total_amount_tax_excluded,
        issue_date, is_valid, completeness_score,
        processing_time, raw_response
    ) VALUES (
        sample_session_id, 'sample_file_1', 'sample_invoice_1.pdf', 256000,
        'パーソルキャリア株式会社', '株式会社トモノカイ', '489753-00', 'JPY',
        1178485, 1071350, '2025-05-01', TRUE, 90.0,
        8.5, '{"success": true}'::jsonb
    ) RETURNING id INTO sample_result_id;
    
    -- サンプル明細
    INSERT INTO ocr_test_line_items (
        result_id, line_number, description, quantity, 
        unit_price, amount, tax_rate
    ) VALUES (
        sample_result_id, 1, '報酬 S0516342-01', 1, 
        1071350, 1071350, '10%'
    );
    
    RAISE NOTICE 'サンプルOCRテストデータが挿入されました';
END;
$$ LANGUAGE plpgsql; 