@echo off
title FPTester — Flying Probe PCB Tester Server
echo ===================================================
echo   FPTester — Automated Flying Probe PCB Tester
echo ===================================================
echo.
echo Starting FPTester server on http://localhost:8000 ...
python pcb_api_server.py
pause
