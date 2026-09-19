param(
    [int]$Port = 8765,
    [string]$BindAddress = "127.0.0.1"
)

$PythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    python -m venv (Join-Path $PSScriptRoot ".venv")
}

& $PythonPath -c "import piper" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $PythonPath -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
}

& $PythonPath (Join-Path $PSScriptRoot "app.py") --host $BindAddress --port $Port
