# 実装ロードマップ & 課題一覧

**作成日**: 2025-07-28  
**目的**: レプリケーション方式に基づく段階的実装計画

## 🎯 レプリケーション方式概要

### **設計方針確定**
```
📋 invoicesテーブル（マスター）
    ↓ レプリケーション
📋 ocr_test_resultsテーブル
    + テスト固有カラム（session_id, gemini_model, file_size）
    - 本番専用カラム（承認ワークフロー、freee連携）
    = 完全一致保証 ✅
```

## 🚨 Phase 1: 緊急対応（即座実行）

### **1️⃣ Streamlitエラー解決**
| 作業項目 | 内容 | 優先度 |
|----------|------|--------|
| **gemini_model削除** | アプリコードから`gemini_model`参照削除 | 🔥 **最高** |
| **スキーマ一致確認** | 現在のDBと設計SQLの差分確認 | 🔥 **最高** |
| **動作確認** | 請求書アップロードテスト | 🔥 **最高** |

### **実行SQL**
```sql
-- 1. 現在テーブル確認
sql/step1_gemini_model_check.sql
sql/step2_unified_fields_check.sql

-- 2. 完全設計適用（要データバックアップ）
sql/complete_invoices_table_design.sql
sql/replicated_test_table_design.sql
```

## 📊 Phase 2: 基盤強化（1-2週間）

### **2️⃣ アプリケーション修正**
| 作業項目 | 内容 | 課題ID |
|----------|------|--------|
| **database.py修正** | 新カラム対応（source_type等） | APP-001 |
| **unified_workflow_engine.py** | key_info構造対応 | APP-002 |
| **画面表示調整** | 新フィールド表示追加 | APP-003 |

### **2️⃣ 明細テーブルレプリケーション**
| 作業項目 | 内容 | 課題ID |
|----------|------|--------|
| **invoice_line_items設計** | マスター明細テーブル設計 | DB-001 |
| **ocr_test_line_items** | レプリケーション設計 | DB-002 |
| **外部キー整合性** | 関連テーブル調整 | DB-003 |

## 🧮 Phase 3: 機能実装（課題積み）

### **3️⃣ 計算ロジック実装**
| 課題ID | 内容 | 優先度 | 仕様策定 |
|--------|------|--------|----------|
| **CALC-001** | `completeness_score`計算ロジック | ⚠️ 中 | **要検討** |
| **CALC-002** | 必須項目定義・重み付け | ⚠️ 中 | **要検討** |
| **CALC-003** | AI精度評価指標 | ⚠️ 中 | **要検討** |

#### **completeness_score仕様候補**
```python
# 案1: 必須項目充足率
def calculate_completeness_score(extracted_data):
    required_fields = [
        'issuer_name', 'main_invoice_number', 'total_amount_tax_included',
        'issue_date', 'currency'
    ]
    filled_count = sum(1 for field in required_fields if extracted_data.get(field))
    return (filled_count / len(required_fields)) * 100

# 案2: 重み付き評価
def calculate_completeness_score_weighted(extracted_data):
    weights = {
        'issuer_name': 0.25,      # 企業名（最重要）
        'main_invoice_number': 0.20,  # 請求書番号
        'total_amount_tax_included': 0.20,  # 金額
        'issue_date': 0.15,       # 発行日
        'currency': 0.10,         # 通貨
        'line_items': 0.10        # 明細
    }
    # 実装要検討
```

### **3️⃣ 新機能実装**
| 課題ID | 内容 | 要件根拠 | 優先度 |
|--------|------|----------|--------|
| **FEAT-001** | Gmail連携機能 | 要件3.10 | 📈 高 |
| **FEAT-002** | 承認ワークフロー | 要件3.6 | 📈 高 |
| **FEAT-003** | 外貨換算機能 | 要件3.9 | ⚠️ 中 |
| **FEAT-004** | freee連携強化 | 要件3.7 | ⚠️ 中 |

## 📋 Phase 4: 品質向上（継続的）

### **4️⃣ 性能・監視**
| 課題ID | 内容 | 目的 |
|--------|------|------|
| **PERF-001** | processing_time分析 | AI性能監視 |
| **PERF-002** | クエリ最適化 | DB性能向上 |
| **PERF-003** | インデックス調整 | 検索速度向上 |

### **4️⃣ データ品質**
| 課題ID | 内容 | 目的 |
|--------|------|------|
| **QUAL-001** | key_info標準化 | データ整合性 |
| **QUAL-002** | バリデーション強化 | 入力品質向上 |
| **QUAL-003** | 重複検出改善 | データクリーニング |

## 🎯 次のアクション

### **即座実行（本日）**
1. **現在のgemini_modelエラー解決**
2. **完全設計SQLの段階実行**
3. **Streamlit動作確認**

### **優先検討（今週）**
1. **completeness_score仕様策定**
2. **key_info活用方針決定**
3. **Gmail連携機能要件詳細化**

### **中長期計画（来月以降）**
1. **承認ワークフロー実装**
2. **外貨換算機能実装**
3. **性能監視ダッシュボード**

## 💾 データ移行計画

### **リスク軽減策**
1. **バックアップ必須**: 既存データ完全バックアップ
2. **段階実行**: テスト環境→本番環境
3. **ロールバック準備**: 旧スキーマ復旧手順

### **移行手順**
```sql
-- 1. データバックアップ
CREATE TABLE invoices_backup AS SELECT * FROM invoices;

-- 2. 新スキーマ適用
-- sql/complete_invoices_table_design.sql

-- 3. データ移行
-- 旧データ→新スキーマ変換SQL（要作成）

-- 4. 動作確認
-- Streamlitテスト実行
```

## 📞 サポート体制

| 課題分類 | 対応者 | 連絡方法 |
|----------|--------|----------|
| **緊急エラー** | 開発チーム | 即座対応 |
| **仕様検討** | プロダクトオーナー | 定期会議 |
| **性能問題** | インフラチーム | チケット管理 |

---

**次のステップ**: Phase 1の緊急対応を開始しますか？ 