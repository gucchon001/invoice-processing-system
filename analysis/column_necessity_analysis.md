# カラム必要性分析レポート

**作成日**: 2025-07-28  
**目的**: 要件定義に基づく現在のテーブル設計の最適化

## 📊 分析対象

### 1. **invoices（本番テーブル）** - 28カラム分析

#### ✅ **必須カラム（要件定義より）**
| カラム名 | 要件根拠 | 用途 |
|---------|----------|------|
| `id` | 基本設計 | 主キー |
| `user_email` | 3.1 ユーザー認証 | ユーザー識別 |
| `status` | 3.3 ダッシュボード | 処理状況追跡 |
| `file_name` | 3.2 アップロード | ファイル識別 |
| `gdrive_file_id` | 4. Google Drive API | ファイル保存 |
| `uploaded_at` | 3.3 ダッシュボード | 時系列管理 |
| `issuer_name` | AI抽出 | 請求書基本情報 |
| `recipient_name` | AI抽出 | 請求書基本情報 |
| `main_invoice_number` | AI抽出 | 請求書識別 |
| `t_number` | AI抽出（適格請求書） | 法的要件 |
| `issue_date` | AI抽出 | 請求書基本情報 |
| `due_date` | AI抽出 | 支払管理 |
| `currency` | 3.9 外貨換算 | 通貨処理 |
| `total_amount_tax_included` | AI抽出 | 金額情報 |
| `total_amount_tax_excluded` | AI抽出 | 金額情報 |
| `extracted_data` | AI処理結果 | データ保存 |
| `raw_response` | AI処理結果 | トレーサビリティ |
| `is_valid` | 3.4 仕訳確認 | 検証状態 |
| `validation_errors` | 3.4 仕訳確認 | エラー管理 |
| `validation_warnings` | 3.4 仕訳確認 | 警告管理 |
| `created_at` | 基本設計 | 監査ログ |
| `updated_at` | 基本設計 | 更新追跡 |

#### ⚠️ **要検討カラム（目的・要件不明確）**
| カラム名 | 課題 | 判定 |
|---------|------|------|
| `receipt_number` | 要件定義に明確な記載なし | **要確認** |
| `key_info` | 具体的用途不明 | **要確認** |
| `final_accounting_info` | 3.7 freee連携？ | **要確認** |
| `completeness_score` | AI処理品質管理？ | **要確認** |
| `processing_time` | パフォーマンス監視？ | **要確認** |
| `file_path` | ローカル保存用？ | **要確認** |

#### ❌ **不要と思われるカラム**
| カラム名 | 理由 | 推奨アクション |
|---------|------|---------------|
| `gemini_model` | ユーザー指摘：不要 | **削除検討** |

### 2. **ocr_test_results（テストテーブル）** - 24カラム分析

#### ✅ **必須カラム（テスト要件より）**
| カラム名 | 要件根拠 | 用途 |
|---------|----------|------|
| `gemini_model` | テスト精度検証 | モデル比較用 |
| `processing_time` | パフォーマンス測定 | 性能評価用 |
| `completeness_score` | 精度測定 | 品質評価用 |
| `session_id` | バッチ管理 | テスト管理用 |
| `file_size` | 処理性能分析 | 分析用 |

#### ❌ **テストに不要と思われるカラム**
| カラム名 | 理由 | 推奨アクション |
|---------|------|---------------|
| `final_accounting_info` | テストには不要 | **削除検討** |

## 🔍 ファイルソース別必要カラム

### **ローカルアップロード**
```sql
-- 必須カラム
file_name VARCHAR(255) NOT NULL
gdrive_file_id VARCHAR(255)  -- アップロード後取得
user_email VARCHAR(255) NOT NULL
uploaded_at TIMESTAMPTZ DEFAULT NOW()
```

### **Google Drive連携**
```sql
-- 必須カラム  
gdrive_file_id VARCHAR(255) NOT NULL
file_name VARCHAR(255) NOT NULL
folder_path VARCHAR(500)  -- ←不足？
sync_source VARCHAR(50)   -- ←不足？
```

### **Gmail自動取り込み**
```sql
-- 必須カラム
gmail_message_id VARCHAR(255)  -- ←不足？ 
attachment_id VARCHAR(255)     -- ←不足？
sender_email VARCHAR(255)      -- ←不足？
auto_assigned_user VARCHAR(255) -- ←不足？
```

## ❗ **発見された問題**

### 1. **Gmail連携カラムが不足**
要件3.10「メール自動取り込み」に対応するカラムが存在しない：
- Gmail Message ID
- 添付ファイル ID  
- 送信者メール
- 自動割り当てユーザー

### 2. **ファイルソース識別カラムが不足**
ローカル・Drive・Gmail を区別するカラムがない：
- `source_type ENUM('local', 'gdrive', 'gmail')`

### 3. **承認ワークフローカラムが不足**  
要件3.6「承認ワークフロー」に対応するカラムがない：
- `approval_status`
- `approved_by`
- `approved_at`

### 4. **外貨換算カラムが不足**
要件3.9「外貨換算」に対応するカラムがない：
- `exchange_rate`
- `jpy_amount`
- `card_statement_id`

## 📋 推奨アクション

### **即座実行**
1. **gemini_model削除**: 本番テーブルから削除
2. **source_type追加**: ファイルソース識別
3. **Gmail連携カラム追加**: 自動取り込み対応

### **段階的実装**  
1. **承認ワークフローカラム**: 要件3.6対応
2. **外貨換算カラム**: 要件3.9対応
3. **freee連携強化**: 要件3.7対応

### **要確認項目**
1. `receipt_number`の具体的用途
2. `key_info`の格納内容
3. `completeness_score`の計算方法
4. `file_path`の必要性 