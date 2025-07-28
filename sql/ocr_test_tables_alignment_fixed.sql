-- OCRテストテーブル・本番テーブル統一マイグレーション（修正版）
-- 作成日: 2025年1月24日（修正版）
-- 目的: OCRテストテーブルのスキーマを本番テーブルに合わせて統一化
-- 修正: カラム存在確認を追加してエラー回避

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

-- 2-2. 税率データ型の変更（VARCHAR → DECIMAL）- 存在確認付き
DO $$
BEGIN
    -- 税率カラムの存在と型確認
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ocr_test_line_items' 
        AND column_name = 'tax_rate'
        AND data_type = 'character varying'
    ) THEN
        -- 既存データの変換処理
        UPDATE ocr_test_line_items 
        SET tax_rate = CASE 
            WHEN tax_rate LIKE '%' THEN REPLACE(tax_rate, '%', '')::TEXT
            WHEN tax_rate ~ '^[0-9]+\.?[0-9]*$' THEN tax_rate
            ELSE '0.00'
        END
        WHERE tax_rate IS NOT NULL;
        
        -- データ型変更
        ALTER TABLE ocr_test_line_items 
        ALTER COLUMN tax_rate TYPE DECIMAL(5,2) 
        USING CASE 
            WHEN tax_rate ~ '^[0-9]+\.?[0-9]*$' THEN tax_rate::DECIMAL(5,2)
            ELSE 0.00
        END;
        
        RAISE NOTICE '✅ tax_rate データ型変更完了: VARCHAR → DECIMAL(5,2)';
        
    ELSIF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ocr_test_line_items' 
        AND column_name = 'tax_rate'
    ) THEN
        RAISE NOTICE '✅ tax_rateカラムは既にDECIMAL型です';
        
    ELSE
        RAISE NOTICE '⚠️ tax_rateカラムが存在しません。DECIMAL型で追加します';
        ALTER TABLE ocr_test_line_items ADD COLUMN IF NOT EXISTS tax_rate DECIMAL(5,2);
    END IF;
END $$;

-- 2-3. 欠損列の追加
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

-- 統一化後のスキーマ確認
DO $$
DECLARE
    ocr_results_columns TEXT[];
    ocr_line_items_columns TEXT[];
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
    RAISE NOTICE 'OCRテストテーブル統一化マイグレーション完了（修正版）';
    RAISE NOTICE '実行日時: %', NOW();
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE '統一化内容:';
    RAISE NOTICE '✅ receipt_number列追加（IF NOT EXISTS）';
    RAISE NOTICE '✅ key_info列追加（IF NOT EXISTS）';  
    RAISE NOTICE '✅ registration_number → t_number 統一（存在確認付き）';
    RAISE NOTICE '✅ invoice_number → main_invoice_number 統一（存在確認付き）';
    RAISE NOTICE '✅ description → item_description 統一（存在確認付き）';
    RAISE NOTICE '✅ tax_rate データ型統一（存在・型確認付き）';
    RAISE NOTICE '✅ updated_at列追加（IF NOT EXISTS）';
    RAISE NOTICE '✅ 新規インデックス追加';
    RAISE NOTICE '✅ トリガー関数・設定';
    RAISE NOTICE '✅ データ移行機能準備';
    RAISE NOTICE '';
    RAISE NOTICE '次のステップ:';
    RAISE NOTICE '1. アプリケーション側のフィールド名修正（完了済み）';
    RAISE NOTICE '2. OCRテスト画面での新項目対応（完了済み）';
    RAISE NOTICE '3. Phase 3A: スキーマ最適化の実行';
    RAISE NOTICE '========================================';
END $$; 