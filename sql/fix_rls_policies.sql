-- 🛠️ invoicesテーブル RLSポリシー修正SQL
-- 実行環境: Supabase Web UI SQL Editor
-- 目的: invoicesテーブルに適切なRLSポリシーを設定

-- ============================================================
-- 1. 既存RLSポリシー削除（安全のためオプション）
-- ============================================================
-- 既存のポリシーがある場合は削除（必要に応じて実行）
-- DROP POLICY IF EXISTS "Users can insert their own invoices" ON invoices;
-- DROP POLICY IF EXISTS "Users can view their own invoices" ON invoices;
-- DROP POLICY IF EXISTS "Users can update their own invoices" ON invoices;
-- DROP POLICY IF EXISTS "Users can delete their own invoices" ON invoices;

-- ============================================================
-- 2. RLS有効化
-- ============================================================
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- 3. INSERT用RLSポリシー設定
-- ============================================================
CREATE POLICY "Users can insert invoices with their email"
ON invoices FOR INSERT
WITH CHECK (
    user_email = auth.email()
);

-- ============================================================
-- 4. SELECT用RLSポリシー設定
-- ============================================================
CREATE POLICY "Users can view their own invoices"
ON invoices FOR SELECT
USING (
    user_email = auth.email()
);

-- ============================================================
-- 5. UPDATE用RLSポリシー設定
-- ============================================================
CREATE POLICY "Users can update their own invoices"
ON invoices FOR UPDATE
USING (
    user_email = auth.email()
)
WITH CHECK (
    user_email = auth.email()
);

-- ============================================================
-- 6. DELETE用RLSポリシー設定
-- ============================================================
CREATE POLICY "Users can delete their own invoices"
ON invoices FOR DELETE
USING (
    user_email = auth.email()
);

-- ============================================================
-- 7. 設定確認
-- ============================================================
SELECT 
    tablename,
    policyname as "ポリシー名",
    cmd as "コマンド",
    qual as "条件式",
    with_check as "チェック式"
FROM pg_policies 
WHERE tablename = 'invoices'
ORDER BY cmd, policyname; 