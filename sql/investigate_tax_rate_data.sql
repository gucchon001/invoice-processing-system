-- 税率データ調査・クリーニング用SQL
-- 目的: DECIMAL変換前に異常値を特定・修正

-- ============================================
-- 1. 現在の税率データ調査
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '=== 税率データ調査開始 ===';
    RAISE NOTICE '実行日時: %', NOW();
END $$;

-- 税率カラムの存在確認
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ocr_test_line_items' AND column_name = 'tax_rate'
    ) THEN
        RAISE NOTICE '✅ tax_rateカラムが存在します';
    ELSE
        RAISE NOTICE '❌ tax_rateカラムが存在しません';
        RETURN;
    END IF;
END $$;

-- 現在の税率データの分析
DO $$
DECLARE
    total_records INTEGER;
    null_records INTEGER;
    empty_records INTEGER;
    max_length INTEGER;
    sample_values TEXT;
BEGIN
    -- 総レコード数
    SELECT COUNT(*) INTO total_records FROM ocr_test_line_items;
    
    -- NULL値の数
    SELECT COUNT(*) INTO null_records FROM ocr_test_line_items WHERE tax_rate IS NULL;
    
    -- 空文字の数
    SELECT COUNT(*) INTO empty_records FROM ocr_test_line_items WHERE tax_rate = '';
    
    -- 最大文字数
    SELECT MAX(LENGTH(tax_rate::TEXT)) INTO max_length FROM ocr_test_line_items WHERE tax_rate IS NOT NULL;
    
    -- サンプル値（重複除去、上位10件）
    SELECT string_agg(DISTINCT tax_rate::TEXT, ', ' ORDER BY tax_rate::TEXT) INTO sample_values 
    FROM (
        SELECT tax_rate FROM ocr_test_line_items 
        WHERE tax_rate IS NOT NULL AND tax_rate != ''
        LIMIT 10
    ) t;
    
    RAISE NOTICE '📊 税率データサマリー:';
    RAISE NOTICE '  総レコード数: %', total_records;
    RAISE NOTICE '  NULL値: %件', null_records;
    RAISE NOTICE '  空文字: %件', empty_records;
    RAISE NOTICE '  最大文字数: %', max_length;
    RAISE NOTICE '  サンプル値: %', sample_values;
END $$;

-- 具体的な異常値の特定
DO $$
DECLARE
    large_values TEXT;
    percentage_values TEXT;
    non_numeric_values TEXT;
BEGIN
    -- 1000以上の値
    SELECT string_agg(DISTINCT tax_rate::TEXT, ', ') INTO large_values
    FROM ocr_test_line_items 
    WHERE tax_rate IS NOT NULL 
    AND tax_rate ~ '^[0-9]+\.?[0-9]*$' 
    AND tax_rate::NUMERIC >= 1000;
    
    -- %記号を含む値
    SELECT string_agg(DISTINCT tax_rate::TEXT, ', ') INTO percentage_values
    FROM ocr_test_line_items 
    WHERE tax_rate LIKE '%'
    LIMIT 20;
    
    -- 数値以外の値
    SELECT string_agg(DISTINCT tax_rate::TEXT, ', ') INTO non_numeric_values
    FROM ocr_test_line_items 
    WHERE tax_rate IS NOT NULL 
    AND tax_rate != ''
    AND NOT (tax_rate ~ '^[0-9]+\.?[0-9]*%?$')
    LIMIT 20;
    
    RAISE NOTICE '🔍 異常値詳細:';
    RAISE NOTICE '  1000以上の値: %', COALESCE(large_values, 'なし');
    RAISE NOTICE '  %%記号付き値: %', COALESCE(percentage_values, 'なし');
    RAISE NOTICE '  非数値値: %', COALESCE(non_numeric_values, 'なし');
END $$;

-- 値ごとの件数集計
DO $$
DECLARE
    rec RECORD;
BEGIN
    RAISE NOTICE '📈 税率値別件数（上位20件）:';
    
    FOR rec IN 
        SELECT tax_rate::TEXT as value, COUNT(*) as count
        FROM ocr_test_line_items 
        WHERE tax_rate IS NOT NULL
        GROUP BY tax_rate::TEXT
        ORDER BY COUNT(*) DESC, tax_rate::TEXT
        LIMIT 20
    LOOP
        RAISE NOTICE '  %: %件', rec.value, rec.count;
    END LOOP;
END $$;

-- 数値変換可能性の確認
DO $$
DECLARE
    convertible_count INTEGER;
    problematic_count INTEGER;
BEGIN
    -- 数値変換可能な件数
    SELECT COUNT(*) INTO convertible_count
    FROM ocr_test_line_items 
    WHERE tax_rate IS NOT NULL 
    AND (
        tax_rate ~ '^[0-9]+\.?[0-9]*$' 
        OR (tax_rate LIKE '%' AND REPLACE(tax_rate, '%', '') ~ '^[0-9]+\.?[0-9]*$')
    );
    
    -- 問題のある件数
    SELECT COUNT(*) INTO problematic_count
    FROM ocr_test_line_items 
    WHERE tax_rate IS NOT NULL 
    AND tax_rate != ''
    AND NOT (
        tax_rate ~ '^[0-9]+\.?[0-9]*$' 
        OR (tax_rate LIKE '%' AND REPLACE(tax_rate, '%', '') ~ '^[0-9]+\.?[0-9]*$')
    );
    
    RAISE NOTICE '🔢 変換可能性:';
    RAISE NOTICE '  変換可能: %件', convertible_count;
    RAISE NOTICE '  問題あり: %件', problematic_count;
END $$;

-- 調査完了メッセージ
DO $$
BEGIN
    RAISE NOTICE '=== 税率データ調査完了 ===';
END $$; 