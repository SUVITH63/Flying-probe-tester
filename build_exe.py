"""
FPTester Single-Click Executable Build Script
Packages FPTester Python Server and Frontend into a standalone .exe for Windows and binary for macOS/Linux.
Usage:
    python build_exe.py
"""
import os
import sys
import subprocess
import shutil

def build():
    print("[*] Building FPTester Standalone Executable...")

    # Ensure pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[*] PyInstaller not found. Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    project_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(project_dir, "frontend")
    parser_dir = os.path.join(project_dir, "parser")

    # PyInstaller command
    pathsep = ";" if sys.platform.startswith("win") else ":"
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name=FPTester",
        f"--add-data={frontend_dir}{pathsep}frontend",
        f"--add-data={parser_dir}{pathsep}parser",
        "--hidden-import=parser.kicad_parser",
        "--hidden-import=parser.gerber_parser",
        "--hidden-import=parser.ai_planner",
        "--hidden-import=parser.workspace",
        "--hidden-import=parser.serial_dispatcher",
        os.path.join(project_dir, "pcb_api_server.py")
    ]

    print(f"[*] Running command: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    dist_dir = os.path.join(project_dir, "dist", "FPTester")
    print(f"\n[SUCCESS] FPTester Build Complete!")
    print(f"[+] Output Directory: {dist_dir}")
    if sys.platform.startswith("win"):
        print(f"[+] Executable: {os.path.join(dist_dir, 'FPTester.exe')}")
    else:
        print(f"[+] Binary: {os.path.join(dist_dir, 'FPTester')}")

if __name__ == "__main__":
    build()
