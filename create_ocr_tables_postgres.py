#!/usr/bin/env python3
"""
Supabase OCRテスト用テーブル作成スクリプト (PostgreSQL直接接続版)
psycopg2を使用してPostgreSQLに直接接続してテーブルを作成
"""
import os
import sys
from pathlib import Path
from typing import Optional
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import toml
from urllib.parse import quote_plus

def load_service_key() -> Optional[str]:
    """Service Role Keyを複数の方法で取得"""
    service_key = None
    
    # 1. Streamlit secrets.tomlから取得を試行
    try:
        import streamlit as st
        service_key = st.secrets["database"]["supabase_service_key"]
        print("✅ secrets.tomlからService Role Keyを取得しました")
        return service_key
    except Exception as e:
        print(f"ℹ️  secrets.toml読み込みエラー: {e}")
    
    # 2. 環境変数から取得を試行
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if service_key:
        print("✅ 環境変数からService Role Keyを取得しました")
        return service_key
    
    # 3. 手動入力
    print("🔐 Supabase Service Role Keyを入力してください")
    service_key = input("Service Role Key: ").strip()
    return service_key if service_key else None

def load_postgres_password() -> Optional[str]:
    """PostgreSQLパスワードを複数の方法で取得"""
    password = None
    
    # 1. Streamlit secrets.tomlから取得を試行
    try:
        import streamlit as st
        password = st.secrets["database"]["postgres_password"]
        print("✅ secrets.tomlからPostgreSQLパスワードを取得しました")
        return password
    except Exception:
        pass
    
    # 2. 直接secrets.tomlファイルから取得を試行
    try:
        secrets_path = Path(".streamlit/secrets.toml")
        if secrets_path.exists():
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets = toml.load(f)
            password = secrets["database"]["postgres_password"]
            print("✅ secrets.tomlファイルからPostgreSQLパスワードを取得しました")
            return password
    except Exception as e:
        print(f"⚠️ secrets.tomlファイル読み込みエラー: {e}")
    
    # 3. 環境変数から取得を試行
    try:
        password = os.environ.get("POSTGRES_PASSWORD")
        if password:
            print("✅ 環境変数からPostgreSQLパスワードを取得しました")
            return password
    except Exception:
        pass
    
    return password

def get_postgres_connection_string(service_key: str, password: Optional[str] = None) -> str:
    """SupabaseのPostgreSQL接続文字列を取得"""
    # SupabaseのPostgreSQL接続情報
    host = "aws-0-ap-northeast-1.pooler.supabase.com"
    port = "6543"  # Supabase Pooler Port
    database = "postgres"
    username = "postgres.jniykkhalkpwuuxdscio"
    
    # パスワードを自動取得 または 手動入力
    if password is None:
        password = load_postgres_password()
    
    if password is None:
        print("🔑 PostgreSQL接続用のパスワードが必要です")
        print("Supabaseダッシュボード > Settings > Database > Connection Pooling")
        print("「Connection string」からパスワードを確認してください")
        password = input("PostgreSQL パスワード: ").strip()
    
    # パスワードをURLエンコード（特殊文字対応）
    encoded_password = quote_plus(password)
    
    return f"postgresql://{username}:{encoded_password}@{host}:{port}/{database}"

def create_ocr_tables_with_postgres():
    """PostgreSQL直接接続でOCRテーブルを作成"""
    try:
        service_key = load_service_key()
        if not service_key:
            print("❌ Service Role Keyが必要です")
            return False
        
        # 接続文字列取得（パスワードを自動取得）
        connection_string = get_postgres_connection_string(service_key)
        
        print("🔗 PostgreSQLに直接接続中...")
        
        # PostgreSQLに接続
        conn = psycopg2.connect(connection_string)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ PostgreSQL接続成功")
        
        # テーブル作成SQL
        table_sqls = [
            # 1. OCRテストセッションテーブル
            """
            CREATE TABLE IF NOT EXISTS public.ocr_test_sessions (
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
            """,
            
            # 2. OCR結果詳細テーブル  
            """
            CREATE TABLE IF NOT EXISTS public.ocr_test_results (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                session_id UUID REFERENCES public.ocr_test_sessions(id) ON DELETE CASCADE,
                file_id VARCHAR(255) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_size BIGINT,
                issuer_name VARCHAR(255),
                recipient_name VARCHAR(255),
                receipt_number VARCHAR(100),  -- 領収書番号を追加
                invoice_number VARCHAR(100),
                registration_number VARCHAR(50),
                currency VARCHAR(10),
                total_amount_tax_included DECIMAL(15,2),
                total_amount_tax_excluded DECIMAL(15,2),
                issue_date DATE,
                due_date DATE,
                is_valid BOOLEAN DEFAULT FALSE,
                completeness_score DECIMAL(5,2),
                validation_errors TEXT[],
                validation_warnings TEXT[],
                processing_time DECIMAL(8,2),
                gemini_model VARCHAR(50) DEFAULT 'gemini-2.0-flash-exp',
                raw_response JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """,
            
            # 3. 明細情報テーブル
            """
            CREATE TABLE IF NOT EXISTS public.ocr_test_line_items (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                result_id UUID REFERENCES public.ocr_test_results(id) ON DELETE CASCADE,
                line_number INTEGER,
                item_description TEXT,
                quantity DECIMAL(10,3),
                unit_price DECIMAL(15,2),
                amount DECIMAL(15,2),
                tax_rate DECIMAL(5,2),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
        ]
        
        # インデックス作成SQL
        index_sqls = [
            "CREATE INDEX IF NOT EXISTS idx_ocr_test_sessions_created_by ON public.ocr_test_sessions(created_by);",
            "CREATE INDEX IF NOT EXISTS idx_ocr_test_sessions_created_at ON public.ocr_test_sessions(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_ocr_test_results_session_id ON public.ocr_test_results(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_ocr_test_results_filename ON public.ocr_test_results(filename);",
            "CREATE INDEX IF NOT EXISTS idx_ocr_test_line_items_result_id ON public.ocr_test_line_items(result_id);"
        ]
        
        # RLS設定SQL
        rls_sqls = [
            "ALTER TABLE public.ocr_test_sessions ENABLE ROW LEVEL SECURITY;",
            "ALTER TABLE public.ocr_test_results ENABLE ROW LEVEL SECURITY;", 
            "ALTER TABLE public.ocr_test_line_items ENABLE ROW LEVEL SECURITY;"
        ]
        
        # RLSポリシー作成SQL
        policy_sqls = [
            """
            DROP POLICY IF EXISTS "ocr_sessions_user_policy" ON public.ocr_test_sessions;
            CREATE POLICY "ocr_sessions_user_policy" ON public.ocr_test_sessions
                FOR ALL USING (auth.jwt() ->> 'email' = created_by);
            """,
            """
            DROP POLICY IF EXISTS "ocr_results_user_policy" ON public.ocr_test_results;
            CREATE POLICY "ocr_results_user_policy" ON public.ocr_test_results
                FOR ALL USING (
                    session_id IN (
                        SELECT id FROM public.ocr_test_sessions 
                        WHERE created_by = auth.jwt() ->> 'email'
                    )
                );
            """,
            """
            DROP POLICY IF EXISTS "ocr_line_items_user_policy" ON public.ocr_test_line_items;
            CREATE POLICY "ocr_line_items_user_policy" ON public.ocr_test_line_items
                FOR ALL USING (
                    result_id IN (
                        SELECT r.id FROM public.ocr_test_results r
                        JOIN public.ocr_test_sessions s ON r.session_id = s.id
                        WHERE s.created_by = auth.jwt() ->> 'email'
                    )
                );
            """
        ]
        
        # SQLを順次実行
        all_sqls = [
            ("テーブル作成", table_sqls),
            ("インデックス作成", index_sqls),
            ("RLS有効化", rls_sqls),
            ("ポリシー作成", policy_sqls)
        ]
        
        total_success = 0
        total_count = sum(len(sqls) for _, sqls in all_sqls)
        
        for category, sqls in all_sqls:
            print(f"\n📋 {category}中...")
            for i, sql in enumerate(sqls, 1):
                try:
                    cursor.execute(sql)
                    print(f"  ✅ {category} {i}/{len(sqls)} 成功")
                    total_success += 1
                except Exception as e:
                    print(f"  ⚠️ {category} {i}/{len(sqls)}: {str(e)[:100]}...")
        
        print(f"\n🎯 実行結果: {total_success}/{total_count} のSQL文が正常実行されました")
        
        # テーブル存在確認
        print("\n🔍 テーブル存在確認...")
        tables_to_check = ['ocr_test_sessions', 'ocr_test_results', 'ocr_test_line_items']
        existing_tables = []
        
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}';")
                count = cursor.fetchone()[0]
                if count > 0:
                    existing_tables.append(table)
                    print(f"  ✅ {table} テーブルが存在します")
                else:
                    print(f"  ❌ {table} テーブルが見つかりません")
            except Exception as e:
                print(f"  ❌ {table} テーブル確認エラー: {str(e)[:50]}...")
        
        success_rate = len(existing_tables) / len(tables_to_check) * 100
        print(f"\n📊 テーブル作成成功率: {success_rate:.1f}% ({len(existing_tables)}/{len(tables_to_check)})")
        
        # 接続を閉じる
        cursor.close()
        conn.close()
        
        if len(existing_tables) > 0:
            # Supabase Python Clientでのアクセステスト
            verify_supabase_client_access()
        
        return len(existing_tables) > 0
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL接続エラー: {e}")
        print("💡 接続文字列やパスワードを確認してください")
        return False
    except Exception as e:
        print(f"❌ テーブル作成エラー: {e}")
        return False

def verify_supabase_client_access():
    """Supabase Python Clientでのアクセステスト"""
    try:
        from supabase import create_client
        
        # secrets.tomlからANON keyを取得
        try:
            import streamlit as st
            supabase_url = st.secrets["database"]["supabase_url"]
            anon_key = st.secrets["database"]["supabase_anon_key"]
        except:
            supabase_url = "https://jniykkhalkpwuuxdscio.supabase.co"
            anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpuaXlra2hhbGtwd3V1eGRzY2lvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI5MjA5OTQsImV4cCI6MjA2ODQ5Njk5NH0.MODNcAWW9YHWtgZamiad_WYAr-pfuhb3UWXYY51jcXk"
        
        supabase = create_client(supabase_url, anon_key)
        
        print("\n🔍 Supabase Python Clientでのアクセステスト...")
        
        try:
            # RLSが設定されているため、認証なしではアクセスできないはず
            result = supabase.table('ocr_test_sessions').select('count').limit(1).execute()
            print("  ✅ ocr_test_sessions テーブルにアクセス可能です")
        except Exception as e:
            if "RLS" in str(e) or "policy" in str(e) or "PGRST116" in str(e):
                print("  ✅ RLS (Row Level Security) が正常に動作しています")
                print("  ℹ️  アプリケーションでの認証後にデータアクセスが可能になります")
            else:
                print(f"  ❌ 予期しないアクセスエラー: {str(e)[:50]}...")
        
    except Exception as e:
        print(f"❌ Supabase Clientアクセステストエラー: {e}")

if __name__ == "__main__":
    print("🚀 Supabase OCRテスト用テーブル作成 (PostgreSQL直接接続版)")
    print("=" * 70)
    print("psycopg2を使用してPostgreSQLに直接接続してテーブルを作成します")
    print()
    
    # psycopg2の確認
    try:
        import psycopg2
        print("✅ psycopg2ライブラリが利用可能です")
    except ImportError:
        print("❌ psycopg2ライブラリが見つかりません")
        print("pip install psycopg2-binary でインストールしてください")
        sys.exit(1)
    
    # テーブル作成実行
    success = create_ocr_tables_with_postgres()
    
    if success:
        print("\n🎉 OCRテスト用テーブル作成が完了しました!")
        print("\n✅ アプリケーションでOCRテスト結果の保存・履歴表示が利用可能になりました")
        print("📱 ブラウザでOCRテストを実行して動作確認してください")
        
        # 一時ファイルを削除
        temp_files = ["create_ocr_tables.py", "create_ocr_tables_v2.py", "create_ocr_tables_final.py"]
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"🗑️ 一時ファイル {temp_file} を削除しました")
        
    else:
        print("\n❌ テーブル作成に失敗しました")
        print("💡 Supabaseダッシュボードでの手動作成をご検討ください") 