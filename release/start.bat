@echo off
cd /d %~dp0
start "" "AL15-Quick-Setup-Tool.exe"
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5010
