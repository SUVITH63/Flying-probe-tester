# OpenFPT — Portable Standalone Web Application

This application is **completely self-contained** and can be run on **any laptop** (Windows, macOS, or Linux) with Python 3 installed. It has **ZERO third-party pip dependencies** and **does NOT require Antigravity** or any special IDE tools.

---

## 🚀 How to Run on Any Laptop

### 1. Windows Laptops
Double-click `start_windows.bat` or run in Command Prompt:
```cmd
start_windows.bat
```

### 2. macOS Laptops
Double-click `start_mac_linux.sh` or run in Terminal:
```bash
./start_mac_linux.sh
```

### 3. Cross-Platform (Any OS)
Run directly with Python:
```bash
python3 run_app.py
```

The application will launch an HTTP server on `http://localhost:8000` and automatically open your default browser.

---

## 🤖 Supported AI Providers (No Antigravity Needed)

In the web interface under **"3. AI Engine Configuration"**, you can select any AI provider of your choice:

1. **⚡ Built-in Zero-Dependency AI (Offline & Local)**
   - Runs locally out-of-the-box without internet or API keys.
   - Detects circuit patterns, power rails, I2C pull-ups, and trace continuity.

2. **✨ Google Gemini API**
   - Enter your public Gemini API key directly into the UI.

3. **🤖 OpenAI GPT-4o / GPT-3.5 API**
   - Enter your public OpenAI API key directly into the UI.

4. **🦙 Local Ollama LLM**
   - Connects to a local Ollama instance running at `http://localhost:11434`.

---

## 📁 File Structure & Design Files

- **`frontend/index.html`**: Dual 5-Bar kinematic canvas visualizer with interactive flex handles.
- **`pcb_api_server.py`**: Zero-dependency Python HTTP backend server.
- **`parser/`**: KiCad & Gerber parsers and AI test plan generator.
- **`run_app.py`**: Cross-platform 1-click Python launcher script.
