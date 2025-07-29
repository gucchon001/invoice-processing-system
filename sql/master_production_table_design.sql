-- 📋 マスター本番テーブル設計
-- 作成日: 2025-07-28
-- 目的: 要件定義に基づく完全な本番テーブル設計（レプリケーション元）

-- 🚨 重要: このテーブルがテストテーブルのレプリケーション元となる

DROP TABLE IF EXISTS invoices CASCADE;

CREATE TABLE public.invoices (
    -- 基本キー・識別
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    
    -- ファイル・ソース管理
    source_type VARCHAR(20) DEFAULT 'local' CHECK (source_type IN ('local', 'gdrive', 'gmail')),
    file_name VARCHAR(255) NOT NULL,
    gdrive_file_id VARCHAR(255),
    file_path VARCHAR(500),
    
    -- Gmail連携（要件3.10対応）
    gmail_message_id VARCHAR(255),
    attachment_id VARCHAR(255), 
    sender_email VARCHAR(255),
    
    -- 処理状況・時系列
    status VARCHAR(50) DEFAULT 'uploaded',
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 請求書基本情報（AI抽出）
    issuer_name VARCHAR(255),
    recipient_name VARCHAR(255), 
    main_invoice_number VARCHAR(255),
    receipt_number VARCHAR(255),
    t_number VARCHAR(50),
    issue_date DATE,
    due_date DATE,
    
    -- 金額・通貨情報
    currency VARCHAR(10) DEFAULT 'JPY',
    total_amount_tax_included DECIMAL(15,2),
    total_amount_tax_excluded DECIMAL(15,2),
    
    -- 外貨換算（要件3.9対応）
    exchange_rate DECIMAL(10,4),
    jpy_amount DECIMAL(15,2),
    card_statement_id VARCHAR(255),
    
    -- AI処理・検証結果
    extracted_data JSONB,
    raw_response JSONB,
    key_info JSONB,
    is_valid BOOLEAN DEFAULT TRUE,
    validation_errors TEXT[],
    validation_warnings TEXT[],
    completeness_score DECIMAL(5,2),
    processing_time DECIMAL(8,2),
    
    -- 承認ワークフロー（要件3.6対応）
    approval_status VARCHAR(50) DEFAULT 'pending',
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE,
    
    -- freee連携（要件3.7対応）
    final_accounting_info JSONB,
    exported_to_freee BOOLEAN DEFAULT FALSE,
    export_date TIMESTAMP WITH TIME ZONE,
    
    -- 監査・追跡
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Tokyo', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('Asia/Tokyo', NOW())
);

-- インデックス作成
CREATE INDEX idx_invoices_user_email ON invoices(user_email);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_source_type ON invoices(source_type);
CREATE INDEX idx_invoices_gdrive_file_id ON invoices(gdrive_file_id);
CREATE INDEX idx_invoices_gmail_message_id ON invoices(gmail_message_id);
CREATE INDEX idx_invoices_approval_status ON invoices(approval_status);
CREATE INDEX idx_invoices_created_at ON invoices(created_at);
CREATE GIN INDEX idx_invoices_extracted_data ON invoices USING gin(extracted_data);
CREATE GIN INDEX idx_invoices_key_info ON invoices USING gin(key_info);

-- RLS設定
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- 更新トリガー
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