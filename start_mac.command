#!/bin/bash
cd "$(dirname "$0")"
echo "========================================================="
echo "   FPTester — Automated Flying Probe PCB Tester Web App"
echo "========================================================="
echo ""

# Automatically remove macOS Gatekeeper quarantine flags
xattr -d com.apple.quarantine ./FPTester-App 2>/dev/null || true
xattr -cr . 2>/dev/null || true

if command -v python3 &>/dev/null; then
    echo "[*] Launching FPTester server with python3..."
    python3 run_app.py
elif command -v python &>/dev/null; then
    echo "[*] Launching FPTester server with python..."
    python run_app.py
elif [ -f "./FPTester-App" ]; then
    echo "[*] Launching standalone FPTester-App binary..."
    ./FPTester-App
else
    echo "[ERROR] Python3 was not found on your Mac."
    echo "Please install Python or right-click FPTester-App -> Open."
fi
