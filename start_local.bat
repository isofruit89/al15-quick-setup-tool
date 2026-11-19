@echo off
cd /d %~dp0

rem Umgebung nur beim ersten Start oder nach geaenderter requirements.txt einrichten.
rem Danach startet das Tool auch ohne Internetverbindung.
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv || goto :error
)

fc /b requirements.txt .venv\requirements.installed >nul 2>&1
if errorlevel 1 (
  echo Pakete werden installiert ...
  .venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error
  copy /y requirements.txt .venv\requirements.installed >nul
)

rem Browser erst oeffnen, wenn der Server gestartet ist (ca. 2 s).
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:5010'"
.venv\Scripts\python.exe app.py
goto :eof

:error
echo.
echo Einrichtung fehlgeschlagen. Fuer die erste Installation wird eine Internetverbindung benoetigt.
pause
exit /b 1
