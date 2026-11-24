@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

echo ==^> Setting up Python virtual environment in %BACKEND%\.venv
pushd "%BACKEND%"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || goto :error
)

echo ==^> Activating virtual environment (.venv\Scripts\activate.bat)
call ".venv\Scripts\activate.bat" || goto :error

echo ==^> Installing backend dependencies from requirements.txt
python -m pip install -r requirements.txt || goto :error
popd

echo ==^> Switching to frontend inside active .venv
pushd "%FRONTEND%"
if not exist "node_modules" (
    echo ==^> Installing frontend npm packages
    call npm install || goto :error
)

if /i "%~1"=="--dev" (
    echo ==^> Starting backend + frontend in dev mode ^(npm run dev:all^)
    call npm run dev:all
) else (
    if not exist ".next\BUILD_ID" (
        echo ==^> Building Next.js production bundle ^(npm run build^)
        call npm run build || goto :error
    )
    echo ==^> Starting backend + frontend in production mode ^(npm run start:all^)
    call npm run start:all
)
popd
exit /b %ERRORLEVEL%

:error
echo Setup or startup failed with exit code %ERRORLEVEL%.
popd 2>nul
exit /b %ERRORLEVEL%
