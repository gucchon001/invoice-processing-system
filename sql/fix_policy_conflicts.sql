-- 🛠️ invoicesテーブル RLSポリシー競合修正SQL
-- 実行環境: Supabase Web UI SQL Editor
-- 目的: 競合ポリシーを削除し、統一ポリシーを再設定

-- ============================================================
-- 1. 競合ポリシー完全削除
-- ============================================================
DROP POLICY IF EXISTS "Users can manage their own invoices" ON invoices;
DROP POLICY IF EXISTS "Users can delete their own invoices" ON invoices;
DROP POLICY IF EXISTS "Users can insert invoices with their email" ON invoices;
DROP POLICY IF EXISTS "Users can view their own invoices" ON invoices;
DROP POLICY IF EXISTS "Users can update their own invoices" ON invoices;

-- ============================================================
-- 2. 統一認証方式でポリシー再作成
-- ============================================================

-- INSERT用ポリシー
CREATE POLICY "invoice_insert_policy"
ON invoices FOR INSERT
WITH CHECK (
    user_email = auth.email()
);

-- SELECT用ポリシー
CREATE POLICY "invoice_select_policy"
ON invoices FOR SELECT
USING (
    user_email = auth.email()
);

-- UPDATE用ポリシー
CREATE POLICY "invoice_update_policy"
ON invoices FOR UPDATE
USING (
    user_email = auth.email()
)
WITH CHECK (
    user_email = auth.email()
);

-- DELETE用ポリシー
CREATE POLICY "invoice_delete_policy"
ON invoices FOR DELETE
USING (
    user_email = auth.email()
);

-- ============================================================
-- 3. 設定確認
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

-- ============================================================
-- 4. 認証状態確認
-- ============================================================
SELECT 
    auth.uid() as "認証済みユーザーID",
    auth.email() as "認証済みメールアドレス",
    auth.role() as "認証済みロール"; 