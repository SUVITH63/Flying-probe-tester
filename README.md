# FPTester

> **Automated Flying Probe PCB Evaluation & Kinematics Engine**

![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-orange?style=flat-square)

**FPTester** is an automated dual-arm flying probe PCB evaluation application. It parses KiCad (`.kicad_pcb`) and Gerber (`.gbr`) design files, generates hardware-ready test plan sequences, and provides a 2D dual 5-bar linkage kinematics visualizer with interactive flex handles.

---

## 💾 Direct 1-Click Downloads & Releases

Click below to download the application for your operating system:

| Operating System | Direct Download Link | Format | Launch Instructions |
| :--- | :--- | :--- | :--- |
| 🪟 **Windows** | [**Download FPTester for Windows (.zip)**](https://github.com/SUVITH63/Flying-probe-tester/releases/download/v1.1.0/FPTester-Windows-x64.zip) | 1-Click Portable `.zip` | Extract zip and double-click `start_windows.bat` or `FPTester-Launcher.bat` |
| 🪟 **Windows** | [**Download Standalone FPTester.exe**](https://github.com/SUVITH63/Flying-probe-tester/releases/download/v1.1.0/FPTester-Windows.exe) | Single Executable `.exe` | Double-click `FPTester-Windows.exe` |
| 🍎 **macOS** | [**Download FPTester for macOS (.zip)**](https://github.com/SUVITH63/Flying-probe-tester/releases/download/v1.1.0/FPTester-macOS-1Click.zip) | Standalone `.zip` | Extract zip and double-click `start_mac.command` |

> 🍎 **Mac Gatekeeper Tip**: If macOS displays *"Apple could not verify FPTester-App"*, double-click **`start_mac.command`** (which automatically unlocks it) OR right-click `FPTester-App` -> select **Open** -> click **Open Anyway**.

---

## ✨ Key Features

- **Embedded Local LLM Engine (`llm/local_llm.py`)**: Zero-dependency offline AI inference for power rails, GND, I2C pull-ups, and signal traces out of the box without requiring API keys or external Ollama setup.
- **Built-in Zero-Dependency Web Engine**: Native HTTP server running out-of-the-box on port 8000.
- **Dual 5-Bar Kinematics Visualizer**: Interactive canvas with real-time inverse kinematics, articulated elbow joints, and drag-and-drop flex handles.
- **Hardware & Simulation Support**: Interactive probe execution and ESP32 USB hardware dispatch protocol.

---

## 🚀 Running from Source

```bash
git clone https://github.com/SUVITH63/Flying-probe-tester.git
cd Flying-probe-tester

# Launch cross-platform application
python3 run_app.py
```

### OS Specific Launchers
- **Windows**: Double-click `start_windows.bat` or `FPTester-Launcher.bat`
- **macOS / Linux**: Double-click `start_mac.command` or `./start_mac_linux.sh`

Application will open automatically in your web browser at **http://localhost:8000**.
