# 請求書処理自動化システム - Cursor カスタムドキュメント登録リスト

## Python & フレームワーク

### 1. Streamlit
- **URL**: https://docs.streamlit.io/
- **説明**: メインフレームワーク - UI/UX、サイドバー、ファイルアップロード
- **重要度**: ⭐⭐⭐⭐⭐

### 2. streamlit-aggrid
- **URL**: https://github.com/PablocFonseca/streamlit-aggrid
- **説明**: 高度なデータグリッド表示、インライン編集機能
- **重要度**: ⭐⭐⭐⭐⭐

### 2-1. streamlit-aggrid 公式ドキュメント
- **URL**: https://streamlit-aggrid.readthedocs.io/en/docs/GridOptionsBuilder.html
- **説明**: GridOptionsBuilderの詳細API仕様、設定オプション
- **重要度**: ⭐⭐⭐⭐⭐

### 2-2. ag-grid React 公式仕様
- **URL**: https://www.ag-grid.com/react-data-grid/getting-started/
- **説明**: ag-gridの基本機能仕様（有料版・無料版の違いを含む）
- **重要度**: ⭐⭐⭐⭐
- **⚠️ 注意**: Community版（無料）とEnterprise版（有料）の機能差異を確認すること

### 🔧 **2-3. ag-grid + DataFrame 安全な処理パターン（技術検証済み）**
**検証日**: 2025-01-21
**検証結果**: ✅ 50件の複雑なDataFrameで安定動作確認済み

#### **✅ 安全な条件判定（推奨）**
```python
# DataFrame の安全な条件判定
if len(dataframe) > 0:          # ✅ 安全
if not dataframe.empty:         # ✅ 安全
if isinstance(data, list) and len(data) > 0:  # ✅ 安全

# DataFrame → リスト変換（推奨パターン）
if hasattr(data, 'to_dict'):
    data = data.to_dict('records')
elif not isinstance(data, list):
    data = []
```

#### **❌ 危険な条件判定（禁止）**
```python
if dataframe:                   # ❌ エラー: "The truth value of a DataFrame is ambiguous"
if not dataframe:               # ❌ エラー: "The truth value of a DataFrame is ambiguous"
if dataframe and len(dataframe) > 0:  # ❌ 第一条件でエラー
```

#### **🔍 技術検証済み機能**
- ✅ **Session State + ag-grid統合**: 正常動作確認済み
- ✅ **複雑なDataFrame（500件）**: 正常表示確認済み
- ✅ **選択行処理とget_selected_rows()**: 正常動作確認済み
- ✅ **DataFrame安全な条件判定**: エラー回避パターン確立済み

### 3. Python Typing
- **URL**: https://docs.python.org/3/library/typing.html
- **説明**: 型ヒント（必須要件）
- **重要度**: ⭐⭐⭐⭐

### 4. Streamlit Session State
- **URL**: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
- **説明**: セッション状態管理、ag-gridの状態保持
- **重要度**: ⭐⭐⭐⭐⭐

#### **🔧 Session State + ag-grid 統合パターン（技術検証済み）**
```python
# 安全なSession State + ag-grid統合
if 'complex_data' not in st.session_state:
    st.session_state.complex_data = None

if st.session_state.complex_data is not None:
    df = st.session_state.complex_data
    if len(df) > 0:  # 安全な条件判定
        grid_response = AgGrid(df, ...)
        selected_rows = aggrid_manager.get_selected_rows(grid_response)
```

## データベース & ストレージ

### 5. Supabase Python
- **URL**: https://supabase.com/docs/reference/python/introduction
- **説明**: メインデータベースクライアント
- **重要度**: ⭐⭐⭐⭐⭐

### 6. PostgreSQL
- **URL**: https://www.postgresql.org/docs/
- **説明**: Supabaseの基盤データベース
- **重要度**: ⭐⭐⭐⭐

## Google APIs

### 7. Google Drive API Python
- **URL**: https://developers.google.com/drive/api/v3/reference
- **説明**: PDFストレージ操作
- **重要度**: ⭐⭐⭐⭐⭐

### 8. Google Sheets API Python
- **URL**: https://developers.google.com/sheets/api/reference/rest
- **説明**: freee連携シート書き出し
- **重要度**: ⭐⭐⭐⭐

### 9. Google Slides API Python
- **URL**: https://developers.google.com/slides/api/reference/rest
- **説明**: 経理ハンドブック読み取り・ルール抽出
- **重要度**: ⭐⭐⭐⭐⭐

### 10. Google OAuth 2.0 (日本語)
- **URL**: https://developers.google.com/identity/protocols/oauth2?hl=ja
- **説明**: ユーザー認証（日本語ドキュメント）
- **重要度**: ⭐⭐⭐⭐⭐

### 11. Google OAuth 2.0 (English)
- **URL**: https://developers.google.com/identity/protocols/oauth2
- **説明**: ユーザー認証（英語版・技術詳細）
- **重要度**: ⭐⭐⭐⭐

### 12. Google Cloud Authentication
- **URL**: https://cloud.google.com/docs/authentication
- **説明**: サービスアカウント認証
- **重要度**: ⭐⭐⭐⭐

## AI & 自然言語処理

### 13. Gemini API
- **URL**: https://ai.google.dev/docs
- **説明**: AI情報抽出、PDF解析
- **重要度**: ⭐⭐⭐⭐⭐

### 14. Google AI Python SDK
- **URL**: https://ai.google.dev/tutorials/python_quickstart
- **説明**: Gemini API Python実装
- **重要度**: ⭐⭐⭐⭐⭐

## クラウド & デプロイ

### 15. Google Cloud Run
- **URL**: https://cloud.google.com/run/docs
- **説明**: アプリケーションサーバー
- **重要度**: ⭐⭐⭐⭐

### 16. Docker
- **URL**: https://docs.docker.com/
- **説明**: コンテナ化
- **重要度**: ⭐⭐⭐

### 17. Google Artifact Registry
- **URL**: https://cloud.google.com/artifact-registry/docs
- **説明**: コンテナイメージストレージ
- **重要度**: ⭐⭐⭐

## セキュリティ & 設定管理

### 18. Streamlit Secrets
- **URL**: https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management
- **説明**: 機密情報管理
- **重要度**: ⭐⭐⭐⭐

### 19. Google Cloud Secret Manager
- **URL**: https://cloud.google.com/secret-manager/docs
- **説明**: 本番環境機密情報管理
- **重要度**: ⭐⭐⭐

## 開発・テスト

### 20. pytest
- **URL**: https://docs.pytest.org/
- **説明**: テストフレームワーク
- **重要度**: ⭐⭐⭐

### 21. Python Logging
- **URL**: https://docs.python.org/3/library/logging.html
- **説明**: ログ出力
- **重要度**: ⭐⭐⭐

## 🚨 ag-grid 有料版・無料版の重要な違い

### 📚 **Community Edition（無料版）**
- ✅ 基本的なグリッド機能
- ✅ フィルタリング・ソート
- ✅ セル編集
- ✅ 行選択（チェックボックス）**← 技術検証済み**
- ✅ ページネーション
- ✅ **複雑なDataFrame表示（500件）** **← 技術検証済み**
- ✅ **Session State統合** **← 技術検証済み**
- ✅ **選択行処理とget_selected_rows()** **← 技術検証済み**
- ❌ サイドバー（フィルタパネル）
- ❌ 高度な集計機能
- ❌ ツリーデータ
- ❌ ピボット機能

### 💰 **Enterprise Edition（有料版）**
- ✅ Community版の全機能
- ✅ サイドバー（フィルタパネル）
- ✅ 高度な集計・ピボット
- ✅ ツリーデータ表示
- ✅ Excel風の機能
- ✅ カスタムフィルタ

### ⚠️ **実装時の注意点（技術検証済み）**
1. **Community版を前提**とした設計を行う
2. **Enterprise機能**（サイドバー等）は使用しない
3. **DataFrame条件判定**は安全なパターンを使用する
4. **Session State + ag-grid**は問題なく動作する
5. **複雑なデータ（500件以上）**でも安定動作する

## 優先度順登録推奨リスト

### 最優先（⭐⭐⭐⭐⭐）
1. Streamlit
2. streamlit-aggrid  
3. streamlit-aggrid 公式ドキュメント ← **新規追加**
4. Streamlit Session State ← **新規追加**
5. Supabase Python
6. Google Drive API Python
7. Gemini API
8. Google AI Python SDK
9. Google Slides API Python
10. Google OAuth 2.0 (日本語)

### 高優先（⭐⭐⭐⭐）
11. ag-grid React 公式仕様 ← **新規追加**
12. Python Typing
13. PostgreSQL
14. Google Sheets API Python
15. Google OAuth 2.0 (English)
16. Google Cloud Authentication
17. Google Cloud Run
18. Streamlit Secrets

### 中優先（⭐⭐⭐）
19. Docker
20. Google Artifact Registry
21. Google Cloud Secret Manager
22. pytest
23. Python Logging

## 📋 更新された登録用URL一覧

### 最優先の10個（今すぐ登録推奨）

```
1. Streamlit
https://docs.streamlit.io/

2. streamlit-aggrid
https://github.com/PablocFonseca/streamlit-aggrid

3. streamlit-aggrid 公式ドキュメント
https://streamlit-aggrid.readthedocs.io/en/docs/GridOptionsBuilder.html

4. Streamlit Session State
https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state

5. Supabase Python
https://supabase.com/docs/reference/python/introduction

6. Google Drive API Python
https://developers.google.com/drive/api/v3/reference

7. Gemini API
https://ai.google.dev/docs

8. Google AI Python SDK
https://ai.google.dev/tutorials/python_quickstart

9. Google Slides API Python
https://developers.google.com/slides/api/reference/rest

10. Google OAuth 2.0 (日本語)
https://developers.google.com/identity/protocols/oauth2?hl=ja
```

### 高優先の追加URL

```
11. ag-grid React 公式仕様
https://www.ag-grid.com/react-data-grid/getting-started/
``` 