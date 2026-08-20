@echo off
title FPTester — Flying Probe PCB Tester Launcher
echo =========================================================
echo    FPTester — Automated Flying Probe PCB Tester Web App
echo =========================================================
echo.

if exist "dist\FPTester\FPTester.exe" (
    echo [*] Starting FPTester executable from dist\FPTester...
    start "" "dist\FPTester\FPTester.exe"
    goto end
)

if exist "FPTester.exe" (
    echo [*] Starting FPTester.exe...
    start "" "FPTester.exe"
    goto end
)

where py >nul 2>nul
if %errorlevel%==0 (
    if not exist "llm\models\fptester-circuit-llm.gguf" (
        echo [*] Downloading local GGUF LLM Model for offline AI reasoning...
        py download_model.py
    )
    echo [*] Launching FPTester server with py...
    py run_app.py
    goto end
)

where python >nul 2>nul
if %errorlevel%==0 (
    if not exist "llm\models\fptester-circuit-llm.gguf" (
        echo [*] Downloading local GGUF LLM Model for offline AI reasoning...
        python download_model.py
    )
    echo [*] Launching FPTester server with python...
    python run_app.py
    goto end
)

where python3 >nul 2>nul
if %errorlevel%==0 (
    if not exist "llm\models\fptester-circuit-llm.gguf" (
        echo [*] Downloading local GGUF LLM Model for offline AI reasoning...
        python3 download_model.py
    )
    echo [*] Launching FPTester server with python3...
    python3 run_app.py
    goto end
)

echo [ERROR] Could not find FPTester.exe or Python installation.
pause

:end
