-- 🔧 usersテーブル Foreign Key制約修正SQL
-- 実行環境: Supabase Web UI SQL Editor
-- 目的: invoices.user_emailのForeign Key制約問題を解決

-- ============================================================
-- 1. usersテーブル存在確認
-- ============================================================
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'users'
ORDER BY ordinal_position;

-- ============================================================
-- 2. 現在のusersテーブルデータ確認
-- ============================================================
SELECT 
    *
FROM users 
LIMIT 5;

-- ============================================================
-- 3. invoices.user_email外部キー制約確認
-- ============================================================
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'invoices'
    AND kcu.column_name = 'user_email';

-- ============================================================
-- 4. 必要ユーザーデータ追加
-- ============================================================
-- y-haraguchi@tomonokai-corp.com をusersテーブルに追加
INSERT INTO users (email, created_at, updated_at)
VALUES (
    'y-haraguchi@tomonokai-corp.com',
    NOW(),
    NOW()
)
ON CONFLICT (email) DO NOTHING;  -- 既存の場合は何もしない

-- ============================================================
-- 5. 追加結果確認
-- ============================================================
SELECT 
    email,
    created_at
FROM users 
WHERE email = 'y-haraguchi@tomonokai-corp.com';

-- ============================================================
-- 6. テスト用ユーザーも追加（デバッグ用）
-- ============================================================
INSERT INTO users (email, created_at, updated_at)
VALUES (
    'service-role-test@example.com',
    NOW(),
    NOW()
)
ON CONFLICT (email) DO NOTHING; 