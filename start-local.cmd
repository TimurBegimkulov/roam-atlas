@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto launch_error

rem This launcher always uses this folder's local database, never hosting settings.
set "DATABASE_URL="
set "RENDER="
set "DATABASE_PATH=%~dp0data\orbit.sqlite3"
set "PORT=8080"
set "SITE_URL="
set "GOOGLE_SITE_VERIFICATION="
set "ADMIN_USERNAME="
set "ADMIN_PASSWORD_HASH="
set "ROAM_PY_ARGS="
set "ROAM_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%ROAM_PYTHON%" (
  "%ROAM_PYTHON%" -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
  if not errorlevel 1 goto launch
)

where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
  if not errorlevel 1 (
    set "ROAM_PYTHON=py"
    set "ROAM_PY_ARGS=-3"
    goto launch
  )
)

rem Skip the Windows Store stub: a missing interpreter should show a clear error.
for /f "delims=" %%P in ('where python 2^>nul') do (
  echo "%%P" | findstr /i /l /c:"\Microsoft\WindowsApps" >nul
  if errorlevel 1 (
    "%%P" -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
    if not errorlevel 1 (
      set "ROAM_PYTHON=%%P"
      goto launch
    )
  )
)

echo Python 3.10 or newer was not found.
echo Install Python from https://www.python.org/downloads/windows/
echo Enable "Add python.exe to PATH", then run this file again.
pause
endlocal
exit /b 1

:launch
echo Open http://127.0.0.1:8080 after the server starts.
echo Keep this window open. Your local data is stored in this project's data folder.
"%ROAM_PYTHON%" %ROAM_PY_ARGS% app.py
if errorlevel 1 goto launch_error
endlocal
exit /b 0

:launch_error
echo The server could not start or stopped with an error. See the message above.
echo If port 8080 is already in use, close the previous local server and try again.
pause
endlocal
exit /b 1
