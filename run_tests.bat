@echo off
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo Bitte zuerst start_local.bat ausfuehren, um die Umgebung anzulegen.
  exit /b 1
)
.venv\Scripts\python.exe -m unittest discover -s tests -v
