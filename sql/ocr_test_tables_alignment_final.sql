-- OCRテストテーブル・本番テーブル統一マイグレーション（最終版）
-- 作成日: 2025年1月24日（税率データクリーニング対応版）
-- 目的: 税率データの異常値を修正してからDECIMAL変換を実行

-- ============================================
-- Phase 1: 緊急統一項目（データ互換性）
-- ============================================

-- 1. ocr_test_results テーブルの統一化
-- ------------------------------------

-- 1-1. 欠損列の追加
ALTER TABLE ocr_test_results 
ADD COLUMN IF NOT EXISTS receipt_number VARCHAR(255),
ADD COLUMN IF NOT EXISTS key_info JSONB;

-- 1-2. カラム名の統一（リネーム）- 存在確認付き
DO $$
BEGIN
    -- registration_number → t_number
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ocr_test_results' AND column_name = 'registration_number'
    ) THEN
        ALTER TABLE ocr_test_results RENAME COLUMN registration_number TO t_number;
        RAISE NOTICE '✅ registration_number → t_number リネーム完了';
    ELSE
        RAISE NOTICE '⚠️ registration_numberカラムが存在しません。t_numberを追加します';
        ALTER TABLE ocr_test_results ADD COLUMN IF NOT EXISTS t_number VARCHAR(50);
    END IF;
    
    -- invoice_number → main_invoice_number
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ocr_test_results' AND column_name = 'invoice_number'
    ) THEN
        ALTER TABLE ocr_test_results RENAME COLUMN invoice_number TO main_invoice_number;
        RAISE NOTICE '✅ invoice_number → main_invoice_number リネーム完了';
    ELSE
        RAISE NOTICE '⚠️ invoice_numberカラムが存在しません。main_invoice_numberを追加します';
        ALTER TABLE ocr_test_results ADD COLUMN IF NOT EXISTS main_invoice_number VARCHAR(255);
    END IF;
END $$;

-- 1-3. データ型の変更（main_invoice_numberの長さ拡張）
ALTER TABLE ocr_test_results 
ALTER COLUMN main_invoice_number TYPE VARCHAR(255);

-- 2. ocr_test_line_items テーブルの統一化
-- ---------------------------------------------

-- 2-1. カラム名の統一 - 存在確認付き
DO $$
BEGIN
    -- description → item_description
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ocr_test_line_items' AND column_name = 'description'
    ) THEN
        ALTER TABLE ocr_test_line_items RENAME COLUMN description TO item_description;
        RAISE NOTICE '✅ description → item_description リネーム完了';
    ELSE
        RAISE NOTICE '⚠️ descriptionカラムが存在しません。item_descriptionを追加します';
        ALTER TABLE ocr_test_line_items ADD COLUMN IF NOT EXISTS item_description TEXT;
    END IF;
END $$;

-- 2-2. 税率データの徹底クリーニング・正規化（型対応版）
DO $$
DECLARE
    cleaned_count INTEGER := 0;
    overflow_count INTEGER := 0;
    total_updated INTEGER := 0;
    current_data_type TEXT;
BEGIN
    RAISE NOTICE '🧹 税率データクリーニング開始';
    
    -- 税率カラムの存在と型確認
    SELECT data_type INTO current_data_type
    FROM information_schema.columns 
    WHERE table_name = 'ocr_test_line_items' AND column_name = 'tax_rate';
    
    IF current_data_type IS NULL THEN
        RAISE NOTICE '⚠️ tax_rateカラムが存在しません。DECIMAL型で新規作成します';
        ALTER TABLE ocr_test_line_items ADD COLUMN tax_rate DECIMAL(5,2) DEFAULT 0.00;
        RETURN;
    END IF;
    
    RAISE NOTICE '📋 現在のtax_rateカラム型: %', current_data_type;
    
    -- VARCHAR型の場合は文字列クリーニング処理
    IF current_data_type = 'character varying' THEN
        RAISE NOTICE '🔤 VARCHAR型のため文字列クリーニングを実行';
        
        -- Step 0: カラムサイズを一時的に拡張（クリーニング作業用）
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'ocr_test_line_items' 
            AND column_name = 'tax_rate'
            AND character_maximum_length <= 20
        ) THEN
            ALTER TABLE ocr_test_line_items ALTER COLUMN tax_rate TYPE VARCHAR(50);
            RAISE NOTICE '📏 税率カラムを一時的に拡張: VARCHAR → VARCHAR(50)';
        END IF;
        
        -- Step 1: 文字列データの異常値修正
        RAISE NOTICE '📊 文字列異常値修正中...';
        
        -- パターン1: 10万以上の異常値を直接修正
        UPDATE ocr_test_line_items 
        SET tax_rate = '10.00'
        WHERE tax_rate IS NOT NULL 
        AND tax_rate::TEXT ~ '^[0-9]+\.?[0-9]*%?$'
        AND REPLACE(tax_rate::TEXT, '%', '')::NUMERIC >= 100000;
        
        GET DIAGNOSTICS overflow_count = ROW_COUNT;
        RAISE NOTICE '  ✅ 異常大値修正（10万以上→10%%）: %件', overflow_count;
        
        -- パターン2: 1000以上の値を100で割る
        UPDATE ocr_test_line_items 
        SET tax_rate = CASE 
            WHEN (REPLACE(tax_rate::TEXT, '%', '')::NUMERIC / 100) > 50 THEN '10.00'
            ELSE (REPLACE(tax_rate::TEXT, '%', '')::NUMERIC / 100)::TEXT
        END
        WHERE tax_rate IS NOT NULL 
        AND tax_rate::TEXT ~ '^[0-9]+\.?[0-9]*%?$'
        AND REPLACE(tax_rate::TEXT, '%', '')::NUMERIC >= 1000
        AND REPLACE(tax_rate::TEXT, '%', '')::NUMERIC < 100000;
        
        GET DIAGNOSTICS cleaned_count = ROW_COUNT;
        RAISE NOTICE '  ✅ 1000以上の値修正: %件', cleaned_count;
        
        -- パターン3: 100-999の値を100で割る
        UPDATE ocr_test_line_items 
        SET tax_rate = CASE 
            WHEN (REPLACE(tax_rate::TEXT, '%', '')::NUMERIC / 100) > 50 THEN '10.00'
            ELSE (REPLACE(tax_rate::TEXT, '%', '')::NUMERIC / 100)::TEXT
        END
        WHERE tax_rate IS NOT NULL 
        AND tax_rate::TEXT ~ '^[0-9]+\.?[0-9]*%?$'
        AND REPLACE(tax_rate::TEXT, '%', '')::NUMERIC >= 100
        AND REPLACE(tax_rate::TEXT, '%', '')::NUMERIC < 1000;
        
        GET DIAGNOSTICS cleaned_count = ROW_COUNT;
        RAISE NOTICE '  ✅ 100-999の値修正: %件', cleaned_count;
        
        -- パターン4: %記号の除去
        UPDATE ocr_test_line_items 
        SET tax_rate = REPLACE(tax_rate::TEXT, '%', '')
        WHERE tax_rate::TEXT LIKE '%'
        AND REPLACE(tax_rate::TEXT, '%', '') ~ '^[0-9]+\.?[0-9]*$'
        AND REPLACE(tax_rate::TEXT, '%', '')::NUMERIC < 100;
        
        GET DIAGNOSTICS cleaned_count = ROW_COUNT;
        RAISE NOTICE '  ✅ %%記号除去: %件', cleaned_count;
        
        -- パターン5: NULL・空文字・非数値を0.00に変換
        UPDATE ocr_test_line_items 
        SET tax_rate = '0.00'
        WHERE tax_rate IS NULL 
        OR tax_rate::TEXT = '' 
        OR NOT (tax_rate::TEXT ~ '^[0-9]+\.?[0-9]*$');
        
        GET DIAGNOSTICS cleaned_count = ROW_COUNT;
        RAISE NOTICE '  ✅ NULL・空文字・非数値修正: %件', cleaned_count;
        
        -- パターン6: 最終範囲チェック
        UPDATE ocr_test_line_items 
        SET tax_rate = '10.00'
        WHERE tax_rate::TEXT ~ '^[0-9]+\.?[0-9]*$'
        AND tax_rate::NUMERIC > 50;
        
        GET DIAGNOSTICS cleaned_count = ROW_COUNT;
        RAISE NOTICE '  ✅ 異常高値修正（50%%超→10%%）: %件', cleaned_count;
        
    -- DECIMAL/NUMERIC型の場合は数値範囲チェックのみ
    ELSIF current_data_type IN ('numeric', 'decimal') THEN
        RAISE NOTICE '🔢 DECIMAL型のため数値範囲チェックを実行';
        
        -- 既にDECIMAL型の場合は範囲外値のみ修正
        UPDATE ocr_test_line_items 
        SET tax_rate = 10.00
        WHERE tax_rate IS NOT NULL 
        AND (tax_rate > 50.00 OR tax_rate < 0.00);
        
        GET DIAGNOSTICS cleaned_count = ROW_COUNT;
        RAISE NOTICE '  ✅ DECIMAL型異常値修正（範囲外→10%%）: %件', cleaned_count;
        
    ELSE
        RAISE NOTICE '⚠️ 予期しない型（%）のため、DECIMAL型で再作成します', current_data_type;
        ALTER TABLE ocr_test_line_items DROP COLUMN tax_rate;
        ALTER TABLE ocr_test_line_items ADD COLUMN tax_rate DECIMAL(5,2) DEFAULT 0.00;
    END IF;
    
    RAISE NOTICE '✅ 税率データクリーニング完了';
    
END $$;

-- 2-3. 安全なDECIMAL型変換（型確認付き）
DO $$
DECLARE
    current_data_type TEXT;
BEGIN
    RAISE NOTICE '🔄 DECIMAL型変換確認開始';
    
    -- 現在のデータ型確認
    SELECT data_type INTO current_data_type
    FROM information_schema.columns 
    WHERE table_name = 'ocr_test_line_items' AND column_name = 'tax_rate';
    
    IF current_data_type IS NULL THEN
        RAISE NOTICE '⚠️ tax_rateカラムが存在しません。DECIMAL型で新規追加します';
        ALTER TABLE ocr_test_line_items ADD COLUMN tax_rate DECIMAL(5,2) DEFAULT 0.00;
        
    ELSIF current_data_type = 'character varying' THEN
        RAISE NOTICE '🔄 VARCHAR型からDECIMAL型に変換します';
        
        -- VARCHAR型からDECIMAL型への安全変換
        ALTER TABLE ocr_test_line_items 
        ALTER COLUMN tax_rate TYPE DECIMAL(5,2) 
        USING CASE 
            WHEN tax_rate IS NULL THEN 0.00
            WHEN tax_rate::TEXT = '' THEN 0.00
            WHEN tax_rate::TEXT ~ '^[0-9]+\.?[0-9]*$' THEN 
                CASE 
                    WHEN tax_rate::NUMERIC > 999.99 THEN 10.00
                    WHEN tax_rate::NUMERIC < 0 THEN 0.00
                    ELSE tax_rate::DECIMAL(5,2)
                END
            ELSE 0.00
        END;
        
        RAISE NOTICE '✅ VARCHAR → DECIMAL(5,2) 型変換完了';
        
    ELSIF current_data_type IN ('numeric', 'decimal') THEN
        RAISE NOTICE '✅ 既にDECIMAL/NUMERIC型です（変換スキップ）';
        
    ELSE
        RAISE NOTICE '⚠️ 予期しない型（%）です。DECIMAL型で再作成します', current_data_type;
        ALTER TABLE ocr_test_line_items DROP COLUMN tax_rate;
        ALTER TABLE ocr_test_line_items ADD COLUMN tax_rate DECIMAL(5,2) DEFAULT 0.00;
        RAISE NOTICE '✅ DECIMAL(5,2)型で再作成完了';
    END IF;
    
    RAISE NOTICE '✅ DECIMAL型変換処理完了';
END $$;

-- 2-4. 欠損列の追加
ALTER TABLE ocr_test_line_items 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- ============================================
-- Phase 2: インデックス最適化
-- ============================================

-- 統一化後の新規インデックス
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_t_number ON ocr_test_results(t_number);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_main_invoice_number ON ocr_test_results(main_invoice_number);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_receipt_number ON ocr_test_results(receipt_number);
CREATE INDEX IF NOT EXISTS idx_ocr_test_results_key_info_gin ON ocr_test_results USING GIN (key_info);

-- ============================================
-- Phase 3: トリガー設定（updated_at自動更新）
-- ============================================

-- update_updated_at_column関数の確認・作成
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ocr_test_line_items用のupdated_atトリガー
DROP TRIGGER IF EXISTS update_ocr_test_line_items_updated_at ON ocr_test_line_items;
CREATE TRIGGER update_ocr_test_line_items_updated_at 
    BEFORE UPDATE ON ocr_test_line_items 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Phase 4: データ検証・確認クエリ
-- ============================================

-- 統一化後のスキーマ・データ確認
DO $$
DECLARE
    ocr_results_columns TEXT[];
    ocr_line_items_columns TEXT[];
    tax_rate_stats RECORD;
BEGIN
    RAISE NOTICE '=== OCRテストテーブル統一化完了 ===';
    
    -- ocr_test_results のカラム確認
    SELECT array_agg(column_name ORDER BY ordinal_position) INTO ocr_results_columns
    FROM information_schema.columns 
    WHERE table_name = 'ocr_test_results';
    
    RAISE NOTICE 'ocr_test_results テーブル構造: %', array_to_string(ocr_results_columns, ', ');
    
    -- ocr_test_line_items のカラム確認
    SELECT array_agg(column_name ORDER BY ordinal_position) INTO ocr_line_items_columns
    FROM information_schema.columns 
    WHERE table_name = 'ocr_test_line_items';
    
    RAISE NOTICE 'ocr_test_line_items テーブル構造: %', array_to_string(ocr_line_items_columns, ', ');
    
    -- 税率データの統計
    SELECT 
        COUNT(*) as total_records,
        COUNT(tax_rate) as non_null_records,
        MIN(tax_rate) as min_tax_rate,
        MAX(tax_rate) as max_tax_rate,
        AVG(tax_rate) as avg_tax_rate
    INTO tax_rate_stats
    FROM ocr_test_line_items;
    
    RAISE NOTICE '📊 税率データ統計:';
    RAISE NOTICE '  総レコード数: %', tax_rate_stats.total_records;
    RAISE NOTICE '  非NULL: %', tax_rate_stats.non_null_records;
    RAISE NOTICE '  最小値: %', tax_rate_stats.min_tax_rate;
    RAISE NOTICE '  最大値: %', tax_rate_stats.max_tax_rate;
    RAISE NOTICE '  平均値: %', ROUND(tax_rate_stats.avg_tax_rate, 2);
    
    -- データ件数確認
    RAISE NOTICE 'データ件数: ocr_test_results=%, ocr_test_line_items=%',
        (SELECT COUNT(*) FROM ocr_test_results),
        (SELECT COUNT(*) FROM ocr_test_line_items);
        
END $$;

-- ============================================
-- Phase 5: 将来的なデータ移行準備
-- ============================================

-- OCRテスト結果を本番テーブルに移行する関数（準備版）
CREATE OR REPLACE FUNCTION migrate_ocr_test_to_production(
    p_session_id UUID,
    p_target_user_email VARCHAR(255)
) RETURNS VOID AS $$
DECLARE
    r_test_result RECORD;
    v_new_invoice_id INTEGER;
BEGIN
    -- OCRテスト結果を本番invoicesテーブルに移行
    FOR r_test_result IN 
        SELECT * FROM ocr_test_results 
        WHERE session_id = p_session_id AND is_valid = TRUE
    LOOP
        -- invoicesテーブルに挿入
        INSERT INTO invoices (
            user_email, status, file_name, 
            issuer_name, recipient_name, main_invoice_number, 
            receipt_number, t_number, issue_date, due_date,
            currency, total_amount_tax_included, total_amount_tax_excluded,
            key_info, raw_response, is_valid, completeness_score,
            processing_time, created_at, updated_at
        ) VALUES (
            p_target_user_email, 'extracted', r_test_result.filename,
            r_test_result.issuer_name, r_test_result.recipient_name, 
            r_test_result.main_invoice_number, r_test_result.receipt_number,
            r_test_result.t_number, r_test_result.issue_date, r_test_result.due_date,
            r_test_result.currency, r_test_result.total_amount_tax_included, 
            r_test_result.total_amount_tax_excluded, r_test_result.key_info,
            r_test_result.raw_response, r_test_result.is_valid, 
            r_test_result.completeness_score, r_test_result.processing_time,
            r_test_result.created_at, r_test_result.updated_at
        ) RETURNING id INTO v_new_invoice_id;
        
        -- 明細データも移行
        INSERT INTO invoice_line_items (
            invoice_id, line_number, item_description, 
            quantity, unit_price, amount, tax_rate, created_at, updated_at
        )
        SELECT 
            v_new_invoice_id, line_number, item_description,
            quantity, unit_price, amount, tax_rate, created_at, updated_at
        FROM ocr_test_line_items 
        WHERE result_id = r_test_result.id;
        
        RAISE NOTICE 'OCRテスト結果 ID:% を 本番請求書 ID:% に移行完了', 
                     r_test_result.id, v_new_invoice_id;
    END LOOP;
    
    RAISE NOTICE 'セッション % の移行処理完了', p_session_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 実行ログ・完了通知
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'OCRテストテーブル統一化マイグレーション完了（最終版）';
    RAISE NOTICE '実行日時: %', NOW();
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE '統一化内容:';
    RAISE NOTICE '✅ receipt_number列追加（IF NOT EXISTS）';
    RAISE NOTICE '✅ key_info列追加（IF NOT EXISTS）';  
    RAISE NOTICE '✅ registration_number → t_number 統一（存在確認付き）';
    RAISE NOTICE '✅ invoice_number → main_invoice_number 統一（存在確認付き）';
    RAISE NOTICE '✅ description → item_description 統一（存在確認付き）';
    RAISE NOTICE '✅ 税率データ徹底クリーニング・正規化';
    RAISE NOTICE '✅ tax_rate データ型: VARCHAR → DECIMAL(5,2)（安全変換）';
    RAISE NOTICE '✅ updated_at列追加（IF NOT EXISTS）';
    RAISE NOTICE '✅ 新規インデックス追加';
    RAISE NOTICE '✅ トリガー関数・設定';
    RAISE NOTICE '✅ データ移行機能準備';
    RAISE NOTICE '';
    RAISE NOTICE '🧹 クリーニング内容（型対応版）:';
    RAISE NOTICE '   • カラム型確認: VARCHAR/DECIMAL/NUMERIC対応';
    RAISE NOTICE '   • VARCHAR型の場合: 文字列クリーニング → DECIMAL変換';
    RAISE NOTICE '     - 10万以上の異常値 → 10.00%%';
    RAISE NOTICE '     - 1000以上の値 → 100で割って正規化（上限50%%）';
    RAISE NOTICE '     - 100-999の値 → 100で割って正規化（上限50%%）';
    RAISE NOTICE '     - %%記号除去';
    RAISE NOTICE '     - NULL・空文字・非数値 → 0.00';
    RAISE NOTICE '   • DECIMAL型の場合: 数値範囲チェックのみ';
    RAISE NOTICE '     - 50%%超または負値 → 10.00%%';
    RAISE NOTICE '   • 型変換: 安全チェック付きDECIMAL(5,2)統一';
    RAISE NOTICE '';
    RAISE NOTICE '次のステップ:';
    RAISE NOTICE '1. アプリケーション側のフィールド名修正（完了済み）';
    RAISE NOTICE '2. OCRテスト画面での新項目対応（完了済み）';
    RAISE NOTICE '3. Phase 3A: スキーマ最適化の実行';
    RAISE NOTICE '========================================';
END $$; 