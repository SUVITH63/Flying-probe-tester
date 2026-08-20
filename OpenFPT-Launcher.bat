@echo off
title OpenFPT — Flying Probe PCB Tester Server
echo ===================================================
echo   OpenFPT — Automated Flying Probe PCB Tester
echo ===================================================
echo.
echo Starting OpenFPT server on http://localhost:8000 ...
python pcb_api_server.py
pause
