-- 📋 完全なinvoicesテーブル設計（レプリケーション元）
-- 作成日: 2025-07-28
-- 目的: 要件定義+仕様確定に基づく完全なマスターテーブル
-- 重要: このテーブルからocr_test_resultsをレプリケーション作成

-- 既存テーブル削除（CASCADE で関連テーブルも削除）
DROP TABLE IF EXISTS invoices CASCADE;

CREATE TABLE public.invoices (
    -- 🔑 基本キー・識別
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    
    -- 📁 ファイル・ソース管理（要件3.2 + 3.10対応）
    source_type VARCHAR(20) DEFAULT 'local' CHECK (source_type IN ('local', 'gdrive', 'gmail')),
    file_name VARCHAR(255) NOT NULL,
    gdrive_file_id VARCHAR(255),
    file_path VARCHAR(500),
    
    -- 📧 Gmail連携（要件3.10メール自動取り込み対応）
    gmail_message_id VARCHAR(255),
    attachment_id VARCHAR(255), 
    sender_email VARCHAR(255),
    
    -- 📈 処理状況・時系列（要件3.3ダッシュボード対応）
    status VARCHAR(50) DEFAULT 'uploaded' CHECK (status IN (
        'uploaded', 'processing', 'extracted', 'validated', 
        'approved', 'rejected', 'failed', 'exported'
    )),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 📄 請求書基本情報（AI抽出）
    issuer_name VARCHAR(255),
    recipient_name VARCHAR(255), 
    main_invoice_number VARCHAR(255),
    receipt_number VARCHAR(255),              -- ✅ 返金処理等で必要
    t_number VARCHAR(50),                     -- 適格請求書発行事業者登録番号
    issue_date DATE,
    due_date DATE,
    
    -- 💰 金額・通貨情報
    currency VARCHAR(10) DEFAULT 'JPY',
    total_amount_tax_included DECIMAL(15,2),
    total_amount_tax_excluded DECIMAL(15,2),
    
    -- 💱 外貨換算（要件3.9外貨換算機能対応）
    exchange_rate DECIMAL(10,4),
    jpy_amount DECIMAL(15,2),
    card_statement_id VARCHAR(255),
    
    -- 🤖 AI処理・検証結果
    extracted_data JSONB,
    raw_response JSONB,
    key_info JSONB,                          -- ✅ プロンプト仕様書準拠（企業特定・重複判定・ファイル管理）
    is_valid BOOLEAN DEFAULT TRUE,
    validation_errors TEXT[],
    validation_warnings TEXT[],
    completeness_score DECIMAL(5,2),         -- ✅ 品質評価（ロジックは課題積み）
    processing_time DECIMAL(8,2),            -- ✅ AI性能監視・テーブル表示用
    
    -- ✅ 承認ワークフロー（要件3.6新規マスタ登録ワークフロー対応）
    approval_status VARCHAR(50) DEFAULT 'pending' CHECK (approval_status IN (
        'pending', 'approved', 'rejected', 'requires_review'
    )),
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE,
    
    -- 📊 freee連携強化（要件3.7freee連携シート書き出し対応）
    exported_to_freee BOOLEAN DEFAULT FALSE,
    export_date TIMESTAMP WITH TIME ZONE,
    freee_batch_id VARCHAR(255),
    
    -- 📅 監査・追跡
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Tokyo', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Tokyo', NOW())
);

-- 📊 コメント追加（ドキュメンテーション）
COMMENT ON TABLE invoices IS '請求書処理ワークフローの中核テーブル。本番・テストテーブルのレプリケーション元。';
COMMENT ON COLUMN invoices.source_type IS 'ファイルソース識別（local/gdrive/gmail）';
COMMENT ON COLUMN invoices.gmail_message_id IS 'Gmail自動取り込み時のメッセージID';
COMMENT ON COLUMN invoices.receipt_number IS '受領書番号（返金処理等で使用）';
COMMENT ON COLUMN invoices.key_info IS 'プロンプト仕様書準拠のキー情報JSONB（企業特定・重複判定・ファイル管理）';
COMMENT ON COLUMN invoices.completeness_score IS 'データ完全性スコア（計算ロジックは課題として後実装）';
COMMENT ON COLUMN invoices.processing_time IS 'AI処理時間（性能監視・テーブル表示用）';
COMMENT ON COLUMN invoices.approval_status IS '承認ワークフロー状態';
COMMENT ON COLUMN invoices.exported_to_freee IS 'freee連携書き出し済みフラグ';

-- 🔍 インデックス作成（検索性能最適化）
CREATE INDEX idx_invoices_user_email ON invoices(user_email);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_source_type ON invoices(source_type);
CREATE INDEX idx_invoices_gdrive_file_id ON invoices(gdrive_file_id) WHERE gdrive_file_id IS NOT NULL;
CREATE INDEX idx_invoices_gmail_message_id ON invoices(gmail_message_id) WHERE gmail_message_id IS NOT NULL;
CREATE INDEX idx_invoices_approval_status ON invoices(approval_status);
CREATE INDEX idx_invoices_exported_to_freee ON invoices(exported_to_freee);
CREATE INDEX idx_invoices_created_at ON invoices(created_at);
CREATE INDEX idx_invoices_main_invoice_number ON invoices(main_invoice_number) WHERE main_invoice_number IS NOT NULL;

-- 🔍 JSONB専用インデックス（高速検索）
CREATE GIN INDEX idx_invoices_extracted_data ON invoices USING gin(extracted_data);
CREATE GIN INDEX idx_invoices_key_info ON invoices USING gin(key_info);

-- 🔒 RLS（Row Level Security）設定
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- 📝 更新トリガー（updated_at自動更新）
CREATE OR REPLACE FUNCTION update_invoices_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('Asia/Tokyo', NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_invoices_updated_at
    BEFORE UPDATE ON invoices
    FOR EACH ROW
    EXECUTE FUNCTION update_invoices_updated_at();

-- 📊 テーブル統計
SELECT 
    'invoicesテーブル作成完了' as status,
    COUNT(*) as column_count
FROM information_schema.columns 
WHERE table_name = 'invoices'; 