-- 🔍 invoicesテーブル RLSポリシー確認SQL
-- 実行環境: Supabase Web UI SQL Editor
-- 目的: 現在のRLSポリシー設定とユーザー認証状態を確認

-- ============================================================
-- 1. RLS設定状況確認
-- ============================================================
SELECT 
    schemaname,
    tablename,
    rowsecurity as "RLS有効"
FROM pg_tables 
WHERE tablename = 'invoices';

-- ============================================================
-- 2. 現在のRLSポリシー一覧表示
-- ============================================================
SELECT 
    schemaname,
    tablename,
    policyname as "ポリシー名",
    permissive as "許可型",
    roles as "対象ロール",
    cmd as "コマンド",
    qual as "条件式",
    with_check as "チェック式"
FROM pg_policies 
WHERE tablename = 'invoices';

-- ============================================================
-- 3. 現在のユーザー認証状態確認
-- ============================================================
SELECT 
    auth.uid() as "認証済みユーザーID",
    auth.email() as "認証済みメールアドレス",
    auth.role() as "認証済みロール";

-- ============================================================
-- 4. サンプルデータでRLSテスト
-- ============================================================
-- 現在のuser_emailでの挿入テスト（実際には実行しない、構文確認のみ）
EXPLAIN (FORMAT TEXT) 
INSERT INTO invoices (user_email, status, file_name, created_at, updated_at, uploaded_at)
VALUES ('y-haraguchi@tomonokai-corp.com', 'test', 'test.pdf', NOW(), NOW(), NOW());

-- ============================================================
-- 5. invoicesテーブルへの権限確認
-- ============================================================
SELECT 
    table_name,
    privilege_type,
    grantee,
    is_grantable
FROM information_schema.table_privileges 
WHERE table_name = 'invoices'
ORDER BY privilege_type, grantee; 