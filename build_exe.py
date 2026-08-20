#!/usr/bin/env python3
"""
FPTester Standalone Executable Builder (PyInstaller)
Bundles Python, pcb_api_server.py, frontend/ dashboard, parser/, and llm/ into a single standalone executable.

Features:
- Zero Dependencies: Target machine does NOT require Python or any external packages.
- Auto-Launch: Automatically starts HTTP server on port 8000 and opens default web browser to http://localhost:8000.
"""
import os
import sys
import subprocess

def build_standalone_exe():
    print("=" * 65)
    print("   FPTester Standalone Executable Builder (PyInstaller)")
    print("=" * 65)
    
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Determine executable name based on OS
    is_windows = sys.platform.startswith('win')
    exe_name = "FPTester.exe" if is_windows else "FPTester-App"

    print(f"[*] Building zero-dependency standalone executable: {exe_name}...")

    # PyInstaller Arguments
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name", "FPTester",
        "--add-data", f"frontend{os.pathsep}frontend",
        "--add-data", f"llm{os.pathsep}llm",
        "--hidden-import", "llm",
        "--hidden-import", "llm.local_llm",
        "--hidden-import", "download_model",
        "--hidden-import", "parser",
        "--hidden-import", "pcb_api_server",
        "run_app.py"
    ]

    print(f"[*] Executing PyInstaller command: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    dist_dir = os.path.join(os.getcwd(), "dist")
    
    print("\n" + "=" * 65)
    print(f"[SUCCESS] Standalone Application Build Complete!")
    print(f"[OUTPUT] Binary created at: {dist_dir}")
    print("=" * 65)

if __name__ == "__main__":
    build_standalone_exe()
