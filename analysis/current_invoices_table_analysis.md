# 現在のinvoicesテーブル詳細分析

**作成日**: 2025-07-28  
**目的**: レプリケーション方式のマスターテーブル設計のための現状分析

## 📋 現在のinvoicesテーブル（28カラム）

### ✅ **要件定義対応済みカラム**

#### **基本識別・管理**
| カラム | データ型 | 要件根拠 | 評価 |
|--------|----------|----------|------|
| `id` | SERIAL | 基本設計 | ✅ **適切** |
| `user_email` | VARCHAR(255) | 3.1 ユーザー認証 | ✅ **適切** |
| `status` | VARCHAR(50) | 3.3 ダッシュボード | ✅ **適切** |
| `uploaded_at` | TIMESTAMPTZ | 3.3 時系列管理 | ✅ **適切** |
| `created_at` | TIMESTAMPTZ | 監査ログ | ✅ **適切** |
| `updated_at` | TIMESTAMPTZ | 更新追跡 | ✅ **適切** |

#### **ファイル管理**  
| カラム | データ型 | 要件根拠 | 評価 |
|--------|----------|----------|------|
| `file_name` | VARCHAR(255) | 3.2 アップロード | ✅ **適切** |
| `gdrive_file_id` | VARCHAR(255) | 4. Google Drive API | ✅ **適切** |
| `file_path` | VARCHAR(500) | ファイル管理 | ⚠️ **要確認** |

#### **請求書基本情報**
| カラム | データ型 | 要件根拠 | 評価 |
|--------|----------|----------|------|
| `issuer_name` | VARCHAR(255) | AI抽出 | ✅ **適切** |
| `recipient_name` | VARCHAR(255) | AI抽出 | ✅ **適切** |
| `main_invoice_number` | VARCHAR(255) | AI抽出 | ✅ **適切** |
| `t_number` | VARCHAR(50) | 適格請求書 | ✅ **適切** |
| `issue_date` | DATE | AI抽出 | ✅ **適切** |
| `due_date` | DATE | AI抽出 | ✅ **適切** |

#### **金額・通貨**
| カラム | データ型 | 要件根拠 | 評価 |
|--------|----------|----------|------|
| `currency` | VARCHAR(10) | 3.9 外貨換算 | ✅ **適切** |
| `total_amount_tax_included` | DECIMAL(15,2) | AI抽出 | ✅ **適切** |
| `total_amount_tax_excluded` | DECIMAL(15,2) | AI抽出 | ✅ **適切** |

#### **AI処理・検証**
| カラム | データ型 | 要件根拠 | 評価 |
|--------|----------|----------|------|
| `extracted_data` | JSONB | AI処理結果 | ✅ **適切** |
| `raw_response` | JSONB | トレーサビリティ | ✅ **適切** |
| `is_valid` | BOOLEAN | 3.4 仕訳確認 | ✅ **適切** |
| `validation_errors` | TEXT[] | 3.4 エラー管理 | ✅ **適切** |
| `validation_warnings` | TEXT[] | 3.4 警告管理 | ✅ **適切** |

### ⚠️ **要確認カラム（具体的用途不明）**

| カラム | データ型 | 課題 | 確認点 |
|--------|----------|------|--------|
| `receipt_number` | VARCHAR(255) | 要件定義に明記なし | 受領書番号の具体的用途は？ |
| `key_info` | JSONB | 格納内容不明 | 契約番号？サービス期間？ |
| `final_accounting_info` | JSONB | freee連携？ | 勘定科目等の最終情報？ |
| `completeness_score` | DECIMAL(5,2) | 計算方法不明 | AI精度評価？必須項目充足率？ |
| `processing_time` | DECIMAL(8,2) | 性能監視？ | 本番運用で必要？ |

### ❌ **不要と判断されるカラム**

| カラム | データ型 | 理由 | アクション |
|--------|----------|------|----------|
| ~~`gemini_model`~~ | ~~VARCHAR(50)~~ | 本番では不要（ユーザー指摘） | **削除** |

## ❗ **重大な不足カラム発見**

### **1. ファイルソース識別（緊急）**
```sql
source_type VARCHAR(20) CHECK (source_type IN ('local', 'gdrive', 'gmail'))
```
**理由**: ローカル・Drive・Gmail を区別できない

### **2. Gmail連携（要件3.10）**
```sql
gmail_message_id VARCHAR(255)    -- Gmail Message ID
attachment_id VARCHAR(255)       -- 添付ファイル ID  
sender_email VARCHAR(255)        -- 送信者メール
```
**理由**: 自動取り込み機能に必須

### **3. 承認ワークフロー（要件3.6）**
```sql
approval_status VARCHAR(50) DEFAULT 'pending'
approved_by VARCHAR(255)
approved_at TIMESTAMP WITH TIME ZONE
```
**理由**: 新規マスタ登録承認

### **4. 外貨換算（要件3.9）**
```sql
exchange_rate DECIMAL(10,4)      -- 為替レート
jpy_amount DECIMAL(15,2)         -- 円換算金額
card_statement_id VARCHAR(255)   -- カード明細連携
```
**理由**: 外貨請求書の円換算

### **5. freee連携強化（要件3.7）**
```sql
exported_to_freee BOOLEAN DEFAULT FALSE
export_date TIMESTAMP WITH TIME ZONE
```
**理由**: 書き出し状況管理

## 📊 カラム統計

| カテゴリ | 現在 | 必要追加 | 削除 | 要確認 |
|----------|------|----------|------|--------|
| **基本識別** | 6 | 1 | 0 | 0 |
| **ファイル管理** | 3 | 4 | 0 | 1 |
| **請求書情報** | 6 | 0 | 0 | 1 |
| **金額・通貨** | 3 | 3 | 0 | 0 |
| **AI・検証** | 7 | 0 | 1 | 2 |
| **ワークフロー** | 0 | 3 | 0 | 1 |
| **外部連携** | 1 | 2 | 0 | 1 |
| **監査** | 2 | 0 | 0 | 0 |
| **合計** | **28** | **+13** | **-1** | **6** |

## 📋 設計方針

### **Phase 1: 緊急修正**
1. `gemini_model`削除
2. `source_type`追加  
3. Gmail連携カラム追加

### **Phase 2: 要確認カラム明確化**
1. `receipt_number`の用途確認
2. `key_info`の格納内容確認
3. `final_accounting_info`の仕様確認
4. `completeness_score`の計算方法確認
5. `processing_time`の必要性確認

### **Phase 3: 機能強化**
1. 承認ワークフロー追加
2. 外貨換算機能追加
3. freee連携強化

## 🎯 次のアクション

**要確認カラムの具体的仕様をお教えください：**

1. **`receipt_number`**: 何の受領書番号？どこで使用？
2. **`key_info`**: どんな情報を格納？（契約番号、期間、etc.）
3. **`final_accounting_info`**: freee連携用？勘定科目？
4. **`completeness_score`**: どう計算？本番で必要？
5. **`processing_time`**: 性能監視？本番で必要？ 