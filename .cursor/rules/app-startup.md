# 請求書処理自動化システム - アプリケーション起動ルール

## 必須起動方法

### ✅ 推奨：run_app.ps1の使用
```powershell
# 対話式起動（推奨）
.\run_app.ps1

# 開発環境指定
.\run_app.ps1 --env dev

# 本番環境指定
.\run_app.ps1 --env prd
```

### ❌ 禁止：直接streamlitコマンド
```powershell
# これらのコマンドは使用禁止
python -m streamlit run app.py
streamlit run app.py
python app.py
```

## run_app.ps1の自動処理

### 環境管理
- Python仮想環境の自動作成・アクティベート
- requirements.txtの変更検出と自動インストール
- 適切なPYTHONPATH設定

### 文字エンコーディング
- UTF-8エンコーディングの強制設定
- PowerShellコンソール出力の文字化け防止

### エラーハンドリング
- 依存関係エラーの自動検出
- わかりやすいエラーメッセージ表示
- エラー時の手動介入待機

### ポート管理
- デフォルトポート: 8701
- 自動プロセス終了による競合回避

## 開発フロー
1. `.\run_app.ps1`を実行
2. 環境選択（dev/prd）
3. 自動で仮想環境アクティベート
4. 依存関係の自動確認・更新
5. Streamlitアプリケーション起動
6. ブラウザでhttp://localhost:8701にアクセス

## トラブルシューティング
- エラー時は必ずrun_app.ps1を使用
- 直接streamlitコマンドは依存関係やエンコーディング問題を引き起こす
- 仮想環境の問題がある場合は`venv`フォルダを削除してrun_app.ps1を再実行 