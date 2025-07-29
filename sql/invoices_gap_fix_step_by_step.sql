-- 📊 invoicesテーブル差分修正SQL（段階的実行）
-- 作成日: 2025-07-28
-- 目的: 現在の28カラム → 設計書40カラムへの段階的修正
-- データソース: 実際のinvoicesテーブル差分分析結果

-- 🎯 修正概要
-- 現在: 28カラム
-- 削除: 1カラム (final_accounting_info)
-- 追加: 13カラム (新機能)
-- 最終: 40カラム ✅

-- ⚠️ 重要：段階的実行推奨（一度に全実行も可能）

-- ============================================================
-- 📋 Phase 1: 削除（1個）
-- ============================================================

-- Step 1.1: final_accounting_info削除
ALTER TABLE invoices DROP COLUMN IF EXISTS final_accounting_info;

-- 確認クエリ
SELECT 'Phase 1完了: final_accounting_info削除' as status,
       COUNT(*) as current_column_count
FROM information_schema.columns 
WHERE table_name = 'invoices';

-- ============================================================
-- 📋 Phase 2: 新機能カラム追加（13個）
-- ============================================================

-- Step 2.1: ファイル・ソース管理（4個）
ALTER TABLE invoices ADD COLUMN source_type VARCHAR(20) DEFAULT 'local';
ALTER TABLE invoices ADD COLUMN gmail_message_id VARCHAR(255);
ALTER TABLE invoices ADD COLUMN attachment_id VARCHAR(255);
ALTER TABLE invoices ADD COLUMN sender_email VARCHAR(255);

-- Step 2.2: CHECK制約追加（source_type）
ALTER TABLE invoices ADD CONSTRAINT chk_invoices_source_type 
    CHECK (source_type IN ('local', 'gdrive', 'gmail'));

-- 確認クエリ
SELECT 'Phase 2.1完了: ファイル・ソース管理' as status,
       COUNT(*) as current_column_count
FROM information_schema.columns 
WHERE table_name = 'invoices';

-- Step 2.3: 外貨換算（3個）
ALTER TABLE invoices ADD COLUMN exchange_rate DECIMAL(10,4);
ALTER TABLE invoices ADD COLUMN jpy_amount DECIMAL(15,2);
ALTER TABLE invoices ADD COLUMN card_statement_id VARCHAR(255);

-- 確認クエリ
SELECT 'Phase 2.2完了: 外貨換算' as status,
       COUNT(*) as current_column_count
FROM information_schema.columns 
WHERE table_name = 'invoices';

-- Step 2.4: 承認ワークフロー（3個）
ALTER TABLE invoices ADD COLUMN approval_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE invoices ADD COLUMN approved_by VARCHAR(255);
ALTER TABLE invoices ADD COLUMN approved_at TIMESTAMPTZ;

-- Step 2.5: CHECK制約追加（approval_status）
ALTER TABLE invoices ADD CONSTRAINT chk_invoices_approval_status 
    CHECK (approval_status IN ('pending', 'approved', 'rejected', 'requires_review'));

-- 確認クエリ
SELECT 'Phase 2.3完了: 承認ワークフロー' as status,
       COUNT(*) as current_column_count
FROM information_schema.columns 
WHERE table_name = 'invoices';

-- Step 2.6: freee連携強化（3個）
ALTER TABLE invoices ADD COLUMN exported_to_freee BOOLEAN DEFAULT FALSE;
ALTER TABLE invoices ADD COLUMN export_date TIMESTAMPTZ;
ALTER TABLE invoices ADD COLUMN freee_batch_id VARCHAR(255);

-- 確認クエリ
SELECT 'Phase 2.4完了: freee連携強化' as status,
       COUNT(*) as current_column_count,
       'カラム追加完了！' as note
FROM information_schema.columns 
WHERE table_name = 'invoices';

-- ============================================================
-- 📋 Phase 3: インデックス追加（4個）
-- ============================================================

-- Step 3.1: 新機能カラム用インデックス作成
CREATE INDEX idx_invoices_source_type ON invoices(source_type);

CREATE INDEX idx_invoices_gmail_message_id ON invoices(gmail_message_id) 
    WHERE gmail_message_id IS NOT NULL;

CREATE INDEX idx_invoices_approval_status ON invoices(approval_status);

CREATE INDEX idx_invoices_exported_to_freee ON invoices(exported_to_freee);

-- 確認クエリ
SELECT 'Phase 3完了: インデックス追加' as status,
       COUNT(*) as index_count
FROM pg_indexes 
WHERE tablename = 'invoices';

-- ============================================================
-- 📋 Phase 4: コメント追加（ドキュメンテーション）
-- ============================================================

-- Step 4.1: 新カラムにコメント追加
COMMENT ON COLUMN invoices.source_type IS 'ファイルソース識別（local/gdrive/gmail）';
COMMENT ON COLUMN invoices.gmail_message_id IS 'Gmail自動取り込み時のメッセージID';
COMMENT ON COLUMN invoices.attachment_id IS 'Gmail添付ファイルID';
COMMENT ON COLUMN invoices.sender_email IS 'Gmail送信者メールアドレス';
COMMENT ON COLUMN invoices.exchange_rate IS '外貨換算レート';
COMMENT ON COLUMN invoices.jpy_amount IS '円換算金額';
COMMENT ON COLUMN invoices.card_statement_id IS 'カード明細連携ID';
COMMENT ON COLUMN invoices.approval_status IS '承認ワークフロー状態';
COMMENT ON COLUMN invoices.approved_by IS '承認者ユーザー';
COMMENT ON COLUMN invoices.approved_at IS '承認日時';
COMMENT ON COLUMN invoices.exported_to_freee IS 'freee連携書き出し済みフラグ';
COMMENT ON COLUMN invoices.export_date IS 'freee書き出し日時';
COMMENT ON COLUMN invoices.freee_batch_id IS 'freeeバッチ処理ID';

-- ============================================================
-- 📋 Phase 5: 最終検証
-- ============================================================

-- Step 5.1: 最終カラム数確認
SELECT 
    '🎉 修正完了！最終検証' as status,
    COUNT(*) as final_column_count,
    CASE 
        WHEN COUNT(*) = 40 THEN '✅ 設計書と完全一致'
        ELSE '❌ カラム数不一致'
    END as validation_result
FROM information_schema.columns 
WHERE table_name = 'invoices';

-- Step 5.2: 新機能カラム存在確認
SELECT 
    '新機能カラム存在確認' as check_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'source_type') as has_source_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'gmail_message_id') as has_gmail_message_id,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'approval_status') as has_approval_status,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'exported_to_freee') as has_exported_to_freee;

-- Step 5.3: 削除確認
SELECT 
    '削除確認' as check_type,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = 'invoices' AND column_name = 'final_accounting_info') as has_final_accounting_info,
    CASE 
        WHEN (SELECT COUNT(*) FROM information_schema.columns 
              WHERE table_name = 'invoices' AND column_name = 'final_accounting_info') = 0 
        THEN '✅ 正常に削除済み'
        ELSE '❌ 削除未完了'
    END as deletion_status;

-- Step 5.4: インデックス数確認
SELECT 
    'インデックス数確認' as check_type,
    COUNT(*) as total_indexes,
    '19個のインデックスが期待値' as expected
FROM pg_indexes 
WHERE tablename = 'invoices';

-- ============================================================
-- 📋 実行完了メッセージ
-- ============================================================

SELECT 
    '🎉 invoicesテーブル修正完了！' as message,
    '28カラム → 40カラム達成' as summary,
    'レプリケーション方式準備完了' as next_step; 