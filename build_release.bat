@echo off
rem Baut die EXE mit PyInstaller und erstellt das Release-ZIP.
rem Ergebnis: dist\AL15 Quick Setup Tool v<Version>\ und dist\AL15-Quick-Setup-Tool-v<Version>.zip
rem Die Ordner profiles, exports, palettes und backups legt das Tool beim ersten Start selbst an.
setlocal
cd /d %~dp0

rem Zeile in app.py: APP_VERSION = "1.7"  -> drittes Wort ohne Anführungszeichen
for /f "tokens=3" %%v in ('findstr /b "APP_VERSION" app.py') do set VERSION=%%~v
if "%VERSION%"=="" (
  echo Version in app.py nicht gefunden.
  exit /b 1
)
set RELEASE=AL15 Quick Setup Tool v%VERSION%
echo Baue %RELEASE% ...

if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv || goto :error
)
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt || goto :error

echo Tests ...
.venv\Scripts\python.exe -m unittest discover -s tests || goto :error

.venv\Scripts\python.exe -m PyInstaller app.spec --noconfirm --clean || goto :error

set OUT=dist\%RELEASE%
if exist "%OUT%" rmdir /s /q "%OUT%"
move "dist\AL15-Quick-Setup-Tool" "%OUT%" >nul || goto :error
copy /y release\readme.txt "%OUT%\readme.txt" >nul
copy /y release\start.bat "%OUT%\start.bat" >nul
copy /y LICENSE "%OUT%\LICENSE.txt" >nul
copy /y NOTICE "%OUT%\NOTICE.txt" >nul

set ZIP=dist\AL15-Quick-Setup-Tool-v%VERSION%.zip
if exist "%ZIP%" del "%ZIP%"
powershell -NoProfile -Command "Compress-Archive -Path '%OUT%' -DestinationPath '%ZIP%'" || goto :error
echo.
echo Fertig: %ZIP%
exit /b 0

:error
echo.
echo Build fehlgeschlagen.
exit /b 1
