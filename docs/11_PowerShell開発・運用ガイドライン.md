# PowerShell開発・運用ガイドライン

## 📋 概要

本ドキュメントは、PowerShellスクリプトの開発・運用において、特に**日本語文字化け問題**を防止し、安定した多言語対応を実現するためのガイドラインです。

### 対象者
- PowerShellスクリプト開発者
- システム運用担当者
- プロジェクト管理者

### 適用範囲
- Windows PowerShell 5.1
- PowerShell 7.x
- 日本語を含むスクリプト開発
- 自動化・運用スクリプト

## 🔍 問題の背景

### 発生する問題
1. **日本語文字化け**: `繧｢繝励Μ繧定ｵｷ蜍輔＠縺ｾ縺・..`
2. **構文エラー**: パラメーター一覧に引数が存在しません
3. **実行時エラー**: Try ステートメントに Catch ブロックがありません

### 根本原因
- **文字エンコーディングの不一致**
- **BOM（Byte Order Mark）の有無**
- **改行コードの違い**
- **PowerShellバージョン依存の問題**

## ✅ 解決方法

### 1. 正しいファイル作成方法

#### 🏆 推奨方法: PowerShell + .NET Framework

```powershell
# スクリプト内容を定義
$content = @'
# 日本語PowerShellスクリプト
Write-Host "アプリケーションを起動します..." -ForegroundColor Green

# 実際の処理をここに記述
if (Test-Path "app.py") {
    Write-Host "ファイルが見つかりました" -ForegroundColor Blue
}

Write-Host "処理完了" -ForegroundColor Cyan
'@

# UTF-16LE + BOMで保存
[System.IO.File]::WriteAllText(".\新しいスクリプト.ps1", $content, [System.Text.Encoding]::Unicode)
```

#### 📊 文字エンコーディング比較

| エンコーディング | Windows PowerShell 5.1 | PowerShell 7.x | 推奨度 |
|-----------------|------------------------|----------------|--------|
| **UTF-16LE + BOM** | ✅ 完全対応 | ✅ 完全対応 | 🏆 **最推奨** |
| UTF-8 + BOM | ✅ 対応 | ✅ 完全対応 | ⭐ 良い |
| UTF-8 (BOMなし) | ❌ 文字化け | ✅ 対応 | ❌ 避ける |

### 2. エディター別設定方法

#### PowerShell ISE
1. 新規ファイル作成
2. 「ファイル」→「名前を付けて保存」
3. エンコーディング: **「Unicode (UTF-16 LE)」** を選択

#### Visual Studio Code
1. 新規 `.ps1` ファイル作成
2. 右下のエンコーディング表示をクリック
3. **「UTF-16 LE」** を選択
4. **「Save with Encoding」**

#### Notepad++
1. 新規ファイル作成
2. 「エンコーディング」→「UTF-16LE BOM」選択
3. `.ps1` 拡張子で保存

## 🚫 避けるべき方法

```powershell
# ❌ これらは日本語で文字化けする
Out-File -FilePath "script.ps1" -Encoding UTF8
Set-Content -Path "script.ps1" -Value $content
"内容" | Out-File "script.ps1"  # デフォルトエンコーディング

# ❌ 既存ファイルの変換（文字化けリスク）
Get-Content .\existing.ps1 -Raw | Out-File -FilePath .\converted.ps1 -Encoding Unicode
```

## 📝 実用的なテンプレート

### 基本テンプレート

```powershell
# PowerShellスクリプトテンプレート - 日本語対応版
# 作成方法: [System.IO.File]::WriteAllText("ファイル名.ps1", $content, [System.Text.Encoding]::Unicode)

# 文字エンコーディング設定
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 基本的な日本語メッセージ
Write-Host "アプリケーションを開始します..." -ForegroundColor Green

# ヘルプ表示
if ($args -contains "--help") {
    Write-Host "使用方法:"
    Write-Host "  .\スクリプト名.ps1 [オプション]"
    Write-Host ""
    Write-Host "オプション:"
    Write-Host "  --help : このヘルプを表示"
    exit 0
}

# エラーハンドリングの例
try {
    Write-Host "処理を実行中..." -ForegroundColor Yellow
    # ここに実際の処理を記述
    Write-Host "処理が正常に完了しました。" -ForegroundColor Green
}
catch {
    Write-Host "エラーが発生しました: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

Write-Host "スクリプトが終了しました。" -ForegroundColor Cyan
```

### Streamlit起動スクリプトテンプレート

```powershell
# Streamlit起動スクリプト - 日本語対応版

# 文字エンコーディング設定
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 環境変数の初期化
$VENV_PATH = ".\venv"
$APP_FILE = "app.py"
$DEFAULT_PORT = 8701

Write-Host "アプリケーションを起動します..." -ForegroundColor Green

# 既存プロセス停止
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# 仮想環境アクティベート
if (Test-Path "$VENV_PATH\Scripts\Activate.ps1") {
    . "$VENV_PATH\Scripts\Activate.ps1"
    Write-Host "仮想環境を有効化しました" -ForegroundColor Green
} else {
    Write-Host "仮想環境が見つかりません" -ForegroundColor Red
    exit 1
}

# Streamlit起動
Write-Host "Streamlitを起動中..." -ForegroundColor Yellow
streamlit run $APP_FILE --server.port $DEFAULT_PORT
```

## 🔧 トラブルシューティング

### 問題1: 日本語が文字化けする

**症状**: `繧｢繝励Μ繧定ｵｷ蜍輔＠縺ｾ縺・..`

**解決方法**:
1. ファイルのエンコーディングを確認
   ```powershell
   Get-Content .\script.ps1 -Encoding Byte -TotalCount 10 | ForEach-Object { "{0:X2}" -f $_ }
   ```
2. `FF FE` (UTF-16LE BOM) が先頭にあることを確認
3. ない場合は正しい方法で再作成

### 問題2: 構文エラーが発生する

**症状**: `パラメーター一覧に引数が存在しません`

**解決方法**:
1. 文字エンコーディングの問題（上記参照）
2. 既存ファイルの変換ではなく、新規作成を推奨

### 問題3: PowerShellバージョン依存

**症状**: Windows PowerShell 5.1 で問題が発生

**解決方法**:
1. UTF-16LE + BOM を使用
2. PowerShell 7.x へのアップグレード検討
   ```powershell
   winget install Microsoft.PowerShell
   ```

## 📋 検証方法

### 1. エンコーディング確認

```powershell
# バイトヘッダー確認
Get-Content .\script.ps1 -Encoding Byte -TotalCount 10 | ForEach-Object { "{0:X2}" -f $_ }

# 期待値: FF FE 23 00 20 00 ... (UTF-16LE + BOM)
```

### 2. 実行テスト

```powershell
# 基本実行テスト
.\script.ps1

# ヘルプ表示テスト
.\script.ps1 --help

# 構文チェック
PowerShell -NoProfile -Command "& {.\script.ps1}" -WhatIf
```

## 🎯 ベストプラクティス

### 開発時
1. **最初から正しいエンコーディングで作成**
2. **既存ファイルの変換は避ける**
3. **動作確認済みファイルを直接コピーして調整**
4. **テンプレートを活用**

### 運用時
1. **複数のPowerShellバージョンでテスト**
2. **文字化け問題の早期発見**
3. **バックアップとバージョン管理**

### チーム開発
1. **エンコーディング規約の統一**
2. **テンプレートの共有**
3. **レビュー時のエンコーディング確認**

## 📚 関連資料

### Microsoft公式ドキュメント
- [PowerShell文字エンコーディング](https://learn.microsoft.com/ja-jp/powershell/module/microsoft.powershell.core/about/about_character_encoding)
- [PowerShell実行ポリシー](https://learn.microsoft.com/ja-jp/powershell/module/microsoft.powershell.security/set-executionpolicy)

### 参考記事
- [PowerShellでps1ファイルに使う文字コードと改行コードについて](https://qiita.com/SAITO_Keita/items/573e1b0274942947a9fe)

## 🔄 更新履歴

| 日付 | バージョン | 更新内容 | 担当者 |
|------|-----------|----------|--------|
| 2025-01-20 | 1.0 | 初版作成、基本ガイドライン策定 | 開発チーム |

---

**注意**: 本ガイドラインは実際のプロジェクト経験に基づいて作成されており、継続的な改善を行っています。問題や改善提案がある場合は、プロジェクトチームにご連絡ください。 