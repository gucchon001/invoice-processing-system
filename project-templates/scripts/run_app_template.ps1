# PowerShellスクリプト - run_app.ps1 テンプレート
# 汎用的なPython/Streamlitアプリケーション実行スクリプト
# Clean Architectureプロジェクト用

# スクリプトの文字コードをUTF-8に設定
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# スクリプトのディレクトリに移動
Set-Location -Path $PSScriptRoot

# 環境変数の初期化
$VENV_PATH = ".\venv"
$DEFAULT_SCRIPT = "app.py"  # メインアプリケーションファイル
$APP_ENV = ""
$SCRIPT_TO_RUN = ""
$DEFAULT_PORT = 8501        # Streamlitデフォルトポート

# プロジェクト固有設定（必要に応じて変更）
$PROJECT_NAME = "My Application"
$PYTHON_PATH_DIRS = @("src", ".")  # PYTHONPATHに追加するディレクトリ

# プロジェクトルートをPYTHONPATHに追加
$env:PYTHONPATH = ($PYTHON_PATH_DIRS | ForEach-Object { Join-Path (Get-Location).Path $_ }) -join [IO.Path]::PathSeparator

# ヘルプメッセージの表示
if ($args -contains "--help") {
    Write-Host "使用方法:"
    Write-Host "  .\run_app.ps1 [オプション]"
    Write-Host ""
    Write-Host "オプション:"
    Write-Host "  --env [dev|prd] : 実行環境を指定します。"
    Write-Host "                     (dev=development, prd=production)"
    Write-Host "  --port [NUMBER] : ポート番号を指定します（デフォルト: $DEFAULT_PORT）"
    Write-Host "  --script [FILE] : 実行するPythonスクリプトを指定します（デフォルト: $DEFAULT_SCRIPT）"
    Write-Host "  --help          : このヘルプを表示します。"
    Write-Host ""
    Write-Host "環境モード:"
    Write-Host "  dev  : 開発環境で実行、詳細なログとデバッグ情報を表示"
    Write-Host "  prd  : 本番運用環境、安定性重視でユーザー向け"
    Write-Host ""
    Write-Host "例:"
    Write-Host "  .\run_app.ps1 --env dev"
    Write-Host "  .\run_app.ps1 --env prd --port 8080"
    Write-Host "  .\run_app.ps1 --env dev --script main.py"
    exit 0
}

# 引数解析
for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        "--env" {
            if ($i + 1 -lt $args.Count) {
                $APP_ENV = $args[$i + 1]
                $i++
            }
        }
        "--port" {
            if ($i + 1 -lt $args.Count) {
                $DEFAULT_PORT = $args[$i + 1]
                $i++
            }
        }
        "--script" {
            if ($i + 1 -lt $args.Count) {
                $SCRIPT_TO_RUN = $args[$i + 1]
                $i++
            }
        }
    }
}

# 引数がない場合はユーザーに選択を促す
if (-not $APP_ENV) {
    Write-Host "実行環境を選択してください:"
    Write-Host "  1. Development (dev)"
    Write-Host "  2. Production (prd)"
    $CHOICE = Read-Host "選択肢を入力してください (1/2)"
    
    $CHOICE = $CHOICE.Trim()
    
    if ($CHOICE -eq "1") {
        $APP_ENV = "development"
        Write-Host "[LOG] 開発環境モードを選択しました。"
    }
    elseif ($CHOICE -eq "2") {
        $APP_ENV = "production"
        Write-Host "[LOG] 本番環境モードを選択しました。"
    }
    else {
        Write-Host "Error: 無効な選択肢です。再実行してください。" -ForegroundColor Red
        exit 1
    }
}

if (-not $SCRIPT_TO_RUN) {
    $SCRIPT_TO_RUN = $DEFAULT_SCRIPT
}

# Pythonがインストールされているか確認
try {
    $pythonVersion = (python --version 2>&1)
    Write-Host "[LOG] Python バージョン: $pythonVersion"
}
catch {
    Write-Host "Error: Python がインストールされていないか、環境パスが設定されていません。" -ForegroundColor Red
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# 仮想環境がなければ作成
if (-not (Test-Path "$VENV_PATH\Scripts\Activate.ps1")) {
    Write-Host "[LOG] 仮想環境が存在しません。作成中..."
    try {
        python -m venv $VENV_PATH
        Write-Host "[LOG] 仮想環境が正常に作成されました。"
    }
    catch {
        Write-Host "Error: 仮想環境の作成に失敗しました。" -ForegroundColor Red
        Write-Host $_.Exception.Message
        Read-Host "続行するには何かキーを押してください..."
        exit 1
    }
}

# 仮想環境を有効化
try {
    if (Test-Path "$VENV_PATH\Scripts\Activate.ps1") {
        . "$VENV_PATH\Scripts\Activate.ps1"
        Write-Host "[LOG] 仮想環境を有効化しました。"
    }
    else {
        Write-Host "Error: 仮想環境の有効化に失敗しました。Activate.ps1 スクリプトが見つかりません。" -ForegroundColor Red
        Read-Host "続行するには何かキーを押してください..."
        exit 1
    }
}
catch {
    Write-Host "Error: 仮想環境の有効化中にエラーが発生しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# requirements.txtの確認
if (-not (Test-Path "requirements.txt")) {
    Write-Host "Error: requirements.txt が見つかりません。" -ForegroundColor Red
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# 必要に応じてパッケージをインストール（ハッシュベース管理）
try {
    $CurrentHash = (Get-FileHash -Path "requirements.txt" -Algorithm SHA256).Hash
    $StoredHash = ""
    if (Test-Path ".req_hash") {
        $StoredHash = Get-Content ".req_hash"
    }

    if ($CurrentHash -ne $StoredHash) {
        Write-Host "[LOG] 必要なパッケージをインストール中..."
        try {
            # 現在のプロジェクトの仮想環境を確実に使用
            & "$VENV_PATH\Scripts\python.exe" -m pip install -r requirements.txt
            $CurrentHash | Out-File -FilePath ".req_hash"
            Write-Host "[LOG] パッケージのインストールが完了しました。"
        }
        catch {
            Write-Host "Error: パッケージのインストールに失敗しました。" -ForegroundColor Red
            Write-Host $_.Exception.Message
            Read-Host "続行するには何かキーを押してください..."
            exit 1
        }
    }
    else {
        Write-Host "[LOG] パッケージは最新です。インストールをスキップします。"
    }
}
catch {
    Write-Host "Error: ハッシュ計算に失敗しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# メインスクリプトの存在確認
if (-not (Test-Path $SCRIPT_TO_RUN)) {
    Write-Host "Error: $SCRIPT_TO_RUN が見つかりません。" -ForegroundColor Red
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# 既存プロセス停止
Write-Host "[LOG] 既存プロセスの確認中..."
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# アプリケーション種別を判定
$isStreamlitApp = $false
$isFastAPIApp = $false
$isDjangoApp = $false

# Streamlitアプリかどうかチェック
if ((Get-Content $SCRIPT_TO_RUN -Raw) -match "streamlit|st\." -or (Get-Content "requirements.txt" -Raw) -match "streamlit") {
    $isStreamlitApp = $true
    Write-Host "[LOG] Streamlitアプリケーションを検出しました。"
}
elseif ((Get-Content $SCRIPT_TO_RUN -Raw) -match "FastAPI|uvicorn" -or (Get-Content "requirements.txt" -Raw) -match "fastapi|uvicorn") {
    $isFastAPIApp = $true
    Write-Host "[LOG] FastAPIアプリケーションを検出しました。"
}
elseif ((Get-Content "requirements.txt" -Raw) -match "django") {
    $isDjangoApp = $true
    Write-Host "[LOG] Djangoアプリケーションを検出しました。"
}

# アプリケーションを実行
Write-Host "[LOG] 環境: $APP_ENV"
Write-Host "[LOG] ポート: $DEFAULT_PORT"
Write-Host "[LOG] スクリプト: $SCRIPT_TO_RUN"
Write-Host "[LOG] アプリケーションを起動中..."

try {
    if ($isStreamlitApp) {
        # Streamlitアプリケーション
        if ($APP_ENV -eq "development") {
            streamlit run $SCRIPT_TO_RUN --server.port $DEFAULT_PORT --logger.level debug
        }
        else {
            streamlit run $SCRIPT_TO_RUN --server.port $DEFAULT_PORT
        }
    }
    elseif ($isFastAPIApp) {
        # FastAPIアプリケーション
        if ($APP_ENV -eq "development") {
            uvicorn main:app --host 0.0.0.0 --port $DEFAULT_PORT --reload
        }
        else {
            uvicorn main:app --host 0.0.0.0 --port $DEFAULT_PORT
        }
    }
    elseif ($isDjangoApp) {
        # Djangoアプリケーション
        if ($APP_ENV -eq "development") {
            python manage.py runserver "0.0.0.0:$DEFAULT_PORT" --settings=settings.development
        }
        else {
            python manage.py runserver "0.0.0.0:$DEFAULT_PORT" --settings=settings.production
        }
    }
    else {
        # 一般的なPythonスクリプト
        python $SCRIPT_TO_RUN
    }
    
    Write-Host "[LOG] アプリケーションが正常に終了しました。"
}
catch {
    Write-Host "Error: アプリケーションの実行に失敗しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# 後処理
Write-Host "[LOG] セッションを終了しています..." 