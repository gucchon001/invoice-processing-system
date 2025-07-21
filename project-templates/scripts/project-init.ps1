# Clean Architecture Python プロジェクト初期化スクリプト
# 新しいプロジェクトを Clean Architecture 構造で作成

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName,
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectType = "streamlit",  # streamlit, fastapi, django, basic
    
    [Parameter(Mandatory=$false)]
    [switch]$WithDocker,
    
    [Parameter(Mandatory=$false)]
    [switch]$WithTests,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# 文字エンコーディングをUTF-8に設定
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Log {
    param($Message, $Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    if ($Verbose -or $Level -eq "ERROR") {
        Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $(
            switch ($Level) {
                "ERROR" { "Red" }
                "WARN"  { "Yellow" }
                "SUCCESS" { "Green" }
                default { "White" }
            }
        )
    }
}

function New-ProjectStructure {
    param($BasePath)
    
    Write-Log "プロジェクト構造を作成中..." "INFO"
    
    # 基本ディレクトリ構造
    $directories = @(
        "src",
        "src/app",
        "src/app/pages",
        "src/app/components",
        "src/core",
        "src/core/models", 
        "src/core/services",
        "src/core/workflows",
        "src/infrastructure",
        "src/infrastructure/database",
        "src/infrastructure/external",
        "src/infrastructure/auth",
        "src/infrastructure/storage",
        "src/utils",
        "tests",
        "tests/unit",
        "tests/unit/core",
        "tests/unit/infrastructure",
        "tests/integration",
        "tests/e2e",
        "tests/fixtures",
        "scripts",
        "sql",
        "sql/migrations",
        "sql/seeds",
        "docs",
        "docs/architecture",
        "docs/api",
        "docs/setup",
        "config"
    )
    
    foreach ($dir in $directories) {
        $fullPath = Join-Path $BasePath $dir
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Log "ディレクトリ作成: $dir" "INFO"
    }
}

function New-InitFiles {
    param($BasePath)
    
    Write-Log "__init__.py ファイルを作成中..." "INFO"
    
    # __init__.py ファイルを作成
    $initFiles = @(
        "src/__init__.py",
        "src/app/__init__.py",
        "src/core/__init__.py",
        "src/core/models/__init__.py",
        "src/core/services/__init__.py", 
        "src/core/workflows/__init__.py",
        "src/infrastructure/__init__.py",
        "src/infrastructure/database/__init__.py",
        "src/infrastructure/external/__init__.py",
        "src/infrastructure/auth/__init__.py",
        "src/infrastructure/storage/__init__.py",
        "src/utils/__init__.py",
        "tests/__init__.py",
        "tests/unit/__init__.py",
        "tests/unit/core/__init__.py",
        "tests/unit/infrastructure/__init__.py",
        "tests/integration/__init__.py",
        "tests/e2e/__init__.py"
    )
    
    foreach ($file in $initFiles) {
        $fullPath = Join-Path $BasePath $file
        $content = '"""' + "`n" + $(Split-Path $file -Parent | Split-Path -Leaf) + " module`n" + '"""'
        Set-Content -Path $fullPath -Value $content -Encoding UTF8
    }
}

function New-BasicFiles {
    param($BasePath, $ProjectType)
    
    Write-Log "基本ファイルを作成中..." "INFO"
    
    # main.py エントリーポイント
    $mainPyContent = @"
"""
$ProjectName - メインエントリーポイント

このファイルは新しいディレクトリ構造のエントリーポイントです。
実際のアプリケーションロジックは src/app/main.py に移動されています。
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# メインアプリケーションを実行
if __name__ == "__main__":
    from app.main import main
    main()
"@
    
    Set-Content -Path (Join-Path $BasePath "main.py") -Value $mainPyContent -Encoding UTF8
    
    # requirements.txt
    $requirementsByType = @{
        "streamlit" = @"
streamlit>=1.28.0
pandas>=2.0.0
requests>=2.31.0
python-dotenv>=1.0.0
"@
        "fastapi" = @"
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.4.0
python-dotenv>=1.0.0
"@
        "django" = @"
Django>=4.2.0
djangorestframework>=3.14.0
python-dotenv>=1.0.0
"@
        "basic" = @"
requests>=2.31.0
python-dotenv>=1.0.0
"@
    }
    
    Set-Content -Path (Join-Path $BasePath "requirements.txt") -Value $requirementsByType[$ProjectType] -Encoding UTF8
    
    # requirements-dev.txt
    $devRequirements = @"
-r requirements.txt
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
coverage>=7.3.0
pytest-cov>=4.1.0
"@
    
    Set-Content -Path (Join-Path $BasePath "requirements-dev.txt") -Value $devRequirements -Encoding UTF8
    
    # .env.example
    $envExample = @"
# データベース設定
DATABASE_URL=sqlite:///./app.db

# API設定
API_KEY=your_api_key_here

# アプリケーション設定
DEBUG=True
LOG_LEVEL=INFO
PORT=8000
"@
    
    Set-Content -Path (Join-Path $BasePath ".env.example") -Value $envExample -Encoding UTF8
    
    # .gitignore
    $gitignore = @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project specific
config/*.json
config/*.yaml
config/*.yml
.env
*.log

# Streamlit
.streamlit/secrets.toml

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Documentation
docs/_build/
"@
    
    Set-Content -Path (Join-Path $BasePath ".gitignore") -Value $gitignore -Encoding UTF8
    
    # run_app.ps1 テンプレートをコピー
    Copy-RunAppTemplate -BasePath $BasePath -ProjectType $ProjectType
}

function Copy-RunAppTemplate {
    param($BasePath, $ProjectType)
    
    Write-Log "run_app.ps1 テンプレートをコピー中..." "INFO"
    
    # テンプレートファイルのパス
    $templatePath = Join-Path $PSScriptRoot "run_app_template.ps1"
    $destinationPath = Join-Path $BasePath "run_app.ps1"
    
    if (Test-Path $templatePath) {
        # テンプレートファイルの内容を読み込み
        $templateContent = Get-Content $templatePath -Raw -Encoding UTF8
        
        # プロジェクト固有の設定を置換
        $customizedContent = $templateContent -replace 'My Application', $ProjectName
        
        # プロジェクトタイプに応じたポート設定
        switch ($ProjectType) {
            "streamlit" { 
                $customizedContent = $customizedContent -replace '\$DEFAULT_PORT = 8501', '$DEFAULT_PORT = 8501'
                $customizedContent = $customizedContent -replace '"app\.py"', '"app.py"'
            }
            "fastapi" { 
                $customizedContent = $customizedContent -replace '\$DEFAULT_PORT = 8501', '$DEFAULT_PORT = 8000'
                $customizedContent = $customizedContent -replace '"app\.py"', '"main.py"'
            }
            "django" { 
                $customizedContent = $customizedContent -replace '\$DEFAULT_PORT = 8501', '$DEFAULT_PORT = 8000'
                $customizedContent = $customizedContent -replace '"app\.py"', '"manage.py"'
            }
            default { 
                $customizedContent = $customizedContent -replace '\$DEFAULT_PORT = 8501', '$DEFAULT_PORT = 8000'
            }
        }
        
        # Clean Architecture構造に対応したPYTHONPATH設定
        if ($ProjectType -eq "streamlit" -or $ProjectType -eq "fastapi") {
            $customizedContent = $customizedContent -replace '@\("src", "."\)', '@("src", ".")'
        }
        
        # ファイルに書き込み
        Set-Content -Path $destinationPath -Value $customizedContent -Encoding UTF8
        Write-Log "run_app.ps1 が正常にコピーされました。" "SUCCESS"
    }
    else {
        Write-Log "警告: run_app_template.ps1 が見つかりません。手動でコピーしてください。" "WARN"
    }
}

function New-AppMainFile {
    param($BasePath, $ProjectType)
    
    Write-Log "アプリケーションファイルを作成中..." "INFO"
    
    $appMainByType = @{
        "streamlit" = @"
"""
$ProjectName - Streamlit アプリケーション

Clean Architecture に基づく Streamlit アプリケーション
"""

import streamlit as st
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def configure_page():
    ""\"ページ設定\"\"\"
    st.set_page_config(
        page_title="$ProjectName",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def main():
    ""\"メイン関数\"\"\"
    configure_page()
    
    st.title("🚀 $ProjectName")
    st.write("Clean Architecture に基づくアプリケーションです。")
    
    # サイドバーメニュー
    with st.sidebar:
        st.title("📋 メニュー")
        page = st.selectbox(
            "ページを選択",
            ["🏠 ホーム", "⚙️ 設定", "🧪 テスト"]
        )
    
    # ページルーティング
    if page == "🏠 ホーム":
        show_home_page()
    elif page == "⚙️ 設定":
        show_settings_page()
    elif page == "🧪 テスト":
        show_test_page()

def show_home_page():
    ""\"ホームページ\"\"\"
    st.header("🏠 ホーム")
    st.write("ここにメイン機能を実装してください。")

def show_settings_page():
    ""\"設定ページ\"\"\"
    st.header("⚙️ 設定")
    st.write("アプリケーション設定をここに実装してください。")

def show_test_page():
    ""\"テストページ\"\"\"
    st.header("🧪 テスト")
    st.write("各種テスト機能をここに実装してください。")

if __name__ == "__main__":
    main()
"@
        "fastapi" = @"
"""
$ProjectName - FastAPI アプリケーション

Clean Architecture に基づく FastAPI アプリケーション
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="$ProjectName",
    description="Clean Architecture に基づく API",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from $ProjectName"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
"@
    }
    
    $content = if ($appMainByType.ContainsKey($ProjectType)) { $appMainByType[$ProjectType] } else { $appMainByType["basic"] }
    Set-Content -Path (Join-Path $BasePath "src/app/main.py") -Value $content -Encoding UTF8
}

function New-DockerFiles {
    param($BasePath, $ProjectType)
    
    if (-not $WithDocker) { return }
    
    Write-Log "Docker ファイルを作成中..." "INFO"
    
    # Dockerfile
    $dockerfileByType = @{
        "streamlit" = @"
FROM python:3.11-slim

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコピー
COPY . .

# ポート公開
EXPOSE 8501

# ヘルスチェック
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# アプリケーション実行
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
"@
        "fastapi" = @"
FROM python:3.11-slim

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコピー
COPY . .

# ポート公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK CMD curl --fail http://localhost:8000/health

# アプリケーション実行
CMD ["python", "main.py"]
"@
    }
    
    $dockerfile = if ($dockerfileByType.ContainsKey($ProjectType)) { $dockerfileByType[$ProjectType] } else { $dockerfileByType["streamlit"] }
    Set-Content -Path (Join-Path $BasePath "Dockerfile") -Value $dockerfile -Encoding UTF8
    
    # docker-compose.yml
    $port = if ($ProjectType -eq "streamlit") { "8501" } else { "8000" }
    $dockerCompose = @"
version: '3.8'

services:
  app:
    build: .
    ports:
      - "$($port):$($port)"
    environment:
      - DEBUG=True
    volumes:
      - .:/app
      - /app/venv
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: $($ProjectName.ToLower() -replace '[^a-z0-9]','_')
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
"@
    
    Set-Content -Path (Join-Path $BasePath "docker-compose.yml") -Value $dockerCompose -Encoding UTF8
}

function New-TestFiles {
    param($BasePath)
    
    if (-not $WithTests) { return }
    
    Write-Log "テストファイルを作成中..." "INFO"
    
    # pytest.ini
    $pytestIni = @"
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
"@
    
    Set-Content -Path (Join-Path $BasePath "pytest.ini") -Value $pytestIni -Encoding UTF8
    
    # conftest.py
    $conftest = @"
"""
Pytest設定ファイル

共通フィクスチャーとテスト設定を定義します。
"""

import pytest
import sys
from pathlib import Path

# テスト用のパス設定
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

@pytest.fixture
def sample_data():
    ""\"テスト用サンプルデータ\"\"\"
    return {
        "id": 1,
        "name": "テストデータ",
        "value": 100
    }

@pytest.fixture
def mock_config():
    ""\"テスト用設定\"\"\"
    return {
        "debug": True,
        "test_mode": True
    }
"@
    
    Set-Content -Path (Join-Path $BasePath "tests/conftest.py") -Value $conftest -Encoding UTF8
    
    # サンプルテスト
    $sampleTest = @"
"""
サンプルテスト

プロジェクト構造のテスト例を示します。
"""

import pytest

class TestSample:
    ""\"サンプルテストクラス\"\"\"
    
    def test_basic_assertion(self):
        ""\"基本的なアサーションテスト\"\"\"
        assert 1 + 1 == 2
    
    def test_with_fixture(self, sample_data):
        ""\"フィクスチャーを使用したテスト\"\"\"
        assert sample_data["id"] == 1
        assert sample_data["name"] == "テストデータ"
    
    @pytest.mark.parametrize("input,expected", [
        (2, 4),
        (3, 9),
        (4, 16),
    ])
    def test_parametrized(self, input, expected):
        ""\"パラメータ化テスト\"\"\"
        assert input ** 2 == expected
"@
    
    Set-Content -Path (Join-Path $BasePath "tests/unit/test_sample.py") -Value $sampleTest -Encoding UTF8
}

function New-README {
    param($BasePath, $ProjectName, $ProjectType)
    
    Write-Log "README.md を作成中..." "INFO"
    
    $readme = @"
# $ProjectName

Clean Architecture に基づく $ProjectType プロジェクトです。

## 🏗️ プロジェクト構造

\`\`\`
$ProjectName/
├── src/                          # メインソースコード
│   ├── app/                      # アプリケーション層
│   ├── core/                     # ビジネスロジック層
│   ├── infrastructure/          # インフラストラクチャ層
│   └── utils/                   # ユーティリティ
├── tests/                       # テストコード
├── scripts/                     # 運用スクリプト
├── docs/                        # ドキュメント
└── main.py                      # エントリーポイント
\`\`\`

## 🚀 セットアップ

### 仮想環境の作成
\`\`\`bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
\`\`\`

### 依存関係のインストール
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 環境変数の設定
\`\`\`bash
cp .env.example .env
# .env ファイルを編集
\`\`\`

## 💻 実行方法

### 開発環境
\`\`\`bash
python main.py
\`\`\`

$(if ($WithDocker) {
@"

### Docker
\`\`\`bash
docker-compose up --build
\`\`\`
"@
})

$(if ($WithTests) {
@"

## 🧪 テスト実行

### 全てのテストを実行
\`\`\`bash
pytest
\`\`\`

### カバレッジレポート付き
\`\`\`bash
pytest --cov=src --cov-report=html
\`\`\`
"@
})

## 📋 機能

- ✅ Clean Architecture 構造
- ✅ 型ヒント対応
- ✅ 包括的なテスト
- ✅ Docker 対応
- ✅ CI/CD 準備

## 🛠️ 開発

### コード品質チェック
\`\`\`bash
# フォーマット
black src/ tests/

# リント
flake8 src/ tests/

# 型チェック
mypy src/
\`\`\`

## 📖 ドキュメント

- [アーキテクチャ](docs/architecture/)
- [API仕様](docs/api/)
- [セットアップガイド](docs/setup/)

## 🤝 コントリビューション

1. フォークする
2. フィーチャーブランチを作成
3. 変更をコミット
4. プルリクエストを作成

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下でライセンスされています。
"@
    
    Set-Content -Path (Join-Path $BasePath "README.md") -Value $readme -Encoding UTF8
}

# メイン処理
try {
    Write-Log "🚀 $ProjectName プロジェクトの初期化を開始します..." "SUCCESS"
    Write-Log "プロジェクトタイプ: $ProjectType" "INFO"
    
    # プロジェクトディレクトリの作成
    if (Test-Path $ProjectName) {
        $response = Read-Host "ディレクトリ '$ProjectName' が既に存在します。続行しますか？ (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Log "初期化をキャンセルしました。" "WARN"
            exit 0
        }
    }
    
    New-Item -ItemType Directory -Path $ProjectName -Force | Out-Null
    $projectPath = Resolve-Path $ProjectName
    
    # 各種ファイル・ディレクトリの作成
    New-ProjectStructure -BasePath $projectPath
    New-InitFiles -BasePath $projectPath
    New-BasicFiles -BasePath $projectPath -ProjectType $ProjectType
    New-AppMainFile -BasePath $projectPath -ProjectType $ProjectType
    New-DockerFiles -BasePath $projectPath -ProjectType $ProjectType
    New-TestFiles -BasePath $projectPath
    New-README -BasePath $projectPath -ProjectName $ProjectName -ProjectType $ProjectType
    
    Write-Log "✅ プロジェクト初期化が完了しました！" "SUCCESS"
    Write-Log "" "INFO"
    Write-Log "次のステップ:" "INFO"
    Write-Log "1. cd $ProjectName" "INFO"
    Write-Log "2. python -m venv venv" "INFO"
    Write-Log "3. venv\Scripts\activate" "INFO"
    Write-Log "4. pip install -r requirements.txt" "INFO"
    Write-Log "5. cp .env.example .env" "INFO"
    Write-Log "6. python main.py" "INFO"
    
    if ($WithTests) {
        Write-Log "7. pytest  # テスト実行" "INFO"
    }
    
    if ($WithDocker) {
        Write-Log "8. docker-compose up --build  # Docker実行" "INFO"
    }
    
} catch {
    Write-Log "エラーが発生しました: $($_.Exception.Message)" "ERROR"
    exit 1
} 