$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'Install failed' }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MemeRadar --exclude-module psycopg --exclude-module psycopg_binary --exclude-module numpy desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
