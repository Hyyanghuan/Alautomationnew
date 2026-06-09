# 启动后端开发服务
$env:PYTHONPATH = "$PSScriptRoot\..\backend"
Set-Location "$PSScriptRoot\..\backend"
if (-not (Test-Path "venv")) { python -m venv venv }
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt -q
python -m app.init_db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
