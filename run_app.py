#!/usr/bin/env python3
"""
FPTester Standalone Cross-Platform Application Launcher
Runs natively on Windows, macOS, and Linux without requiring pip install or external dependencies.
"""
import os
import sys
import webbrowser
import time
from pcb_api_server import run_server

def main():
    port = 8000
    print("=" * 65)
    print("   FPTester — Automated Flying Probe PCB Tester Web App")
    print("=" * 65)
    print(f"[*] Starting FPTester Web App Server on http://localhost:{port}...")
    print("[*] Compatible with Windows, macOS, and Linux.")
    print("[*] Press Ctrl+C in this terminal window to stop the app.\n")

    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        print(f"[!] Note: Please open http://localhost:{port} manually in your web browser.")

    run_server(port)

if __name__ == "__main__":
    main()
