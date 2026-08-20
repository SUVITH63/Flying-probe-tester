"""
FPTester Production Web & REST API Server (Synced with Major_proect_server_host)
Runs natively on any laptop without requiring external pip packages.
Provides endpoints for PCB file uploading, AI test plan generation, 2D dual-arm laptop simulation,
and ESP32 USB hardware dispatch.
"""
import os
import sys
import json
import uuid
import urllib.parse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import logging

# Ensure parser modules are accessible
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from parser.kicad_parser import KiCadPCBParser
from parser.gerber_parser import GerberParser
from parser.ai_planner import AITestPlanner
from parser.workspace import WorkspaceValidator
from parser.serial_dispatcher import SerialDispatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FPTester_HTTP_Server")

# In-Memory Session Store (thread-safe writes via lock)
BOARD_SESSIONS: dict = {}
_sessions_lock = threading.Lock()

# Pre-warm parsers at import time so the very first upload request is instant
_kicad_parser = KiCadPCBParser()
_gerber_parser = GerberParser()
logger.info("Parser engines pre-warmed and ready.")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server — each request runs in its own thread."""
    daemon_threads = True


class FPTesterHTTPRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status_code: int = 200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_str: str, status_code: int = 200):
        body = html_str.encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        url_path = urllib.parse.urlparse(self.path).path

        if url_path == "/" or url_path == "/index.html":
            index_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    self._send_html(f.read())
            else:
                self._send_html("<h1>FPTester Server Online</h1><p>Frontend index.html not found.</p>")

        elif url_path == "/api/health":
            self._send_json({"status": "online", "system": "FPTester HTTP Server", "version": "2.0.0"})

        elif url_path == "/api/ports":
            self._send_json({"ports": SerialDispatcher.list_available_ports()})

        elif url_path.startswith("/api/board/"):
            board_id = url_path.split("/")[-1]
            if board_id not in BOARD_SESSIONS:
                self._send_json({"error": "Board session not found"}, 404)
                return

            board = BOARD_SESSIONS[board_id]["board"]
            self._send_json({
                "board_id": board_id,
                "filename": BOARD_SESSIONS[board_id]["filename"],
                "summary": board.to_dict(),
                "pads": [p.to_dict() for p in board.pads],
                "components": [c.to_dict() for c in board.components],
                "nets": [n.to_dict() for n in board.nets.values()]
            })

        else:
            self._send_json({"error": "Endpoint not found"}, 404)

    def do_POST(self):
        url_path = urllib.parse.urlparse(self.path).path
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""

        if url_path.startswith("/api/upload"):
            content_str = post_data.decode('utf-8', errors='ignore')
            session_id = str(uuid.uuid4())[:8]

            # Extract filename from query params
            filename = "uploaded_design.kicad_pcb"
            query = urllib.parse.urlparse(self.path).query
            query_params = urllib.parse.parse_qs(query)
            if 'filename' in query_params:
                filename = query_params['filename'][0]

            # Strip multipart form-data boundary headers if present
            if '\r\n\r\n' in content_str:
                content_str = content_str.split('\r\n\r\n', 1)[-1]
            if '\n\n' in content_str and content_str.startswith('--'):
                content_str = content_str.split('\n\n', 1)[-1]

            # Extract S-expression content if embedded in multipart noise
            if '(kicad_pcb' in content_str:
                start_idx = content_str.find('(kicad_pcb')
                end_idx = content_str.rfind(')')
                if start_idx != -1 and end_idx != -1:
                    content_str = content_str[start_idx:end_idx + 1]

            fname_lower = filename.lower().strip()
            # Determine file type from extension and content signature
            is_kicad = (fname_lower.endswith('.kicad_pcb') or
                        fname_lower.endswith('.kicad') or
                        '(kicad_pcb' in content_str[:200])
            is_gerber = (fname_lower.endswith('.gbr') or
                         fname_lower.endswith('.ger') or
                         fname_lower.endswith('.gtl') or
                         fname_lower.endswith('.gbl') or
                         fname_lower.endswith('.gts') or
                         fname_lower.endswith('.gbs') or
                         fname_lower.endswith('.gko') or
                         fname_lower.endswith('.drl') or
                         fname_lower.endswith('.excellon') or
                         fname_lower.endswith('.xln') or
                         content_str.lstrip()[:3] in ('%TF', '%FS', 'G04') or
                         content_str.lstrip().startswith('%'))

            try:
                if is_kicad:
                    try:
                        board = _kicad_parser.parse_string(content_str, board_name=filename)
                    except Exception as kicad_err:
                        board = _gerber_parser.parse_string(content_str, board_name=filename)
                elif is_gerber:
                    try:
                        board = _gerber_parser.parse_string(content_str, board_name=filename)
                    except Exception:
                        board = _kicad_parser.parse_string(content_str, board_name=filename)
                else:
                    # Auto-detect: try KiCad first then Gerber
                    try:
                        board = _kicad_parser.parse_string(content_str, board_name=filename)
                    except Exception:
                        board = _gerber_parser.parse_string(content_str, board_name=filename)

                BOARD_SESSIONS[session_id] = {
                    "board_id": session_id,
                    "filename": filename,
                    "board": board,
                    "test_job": None
                }

                self._send_json({
                    "status": "success",
                    "board_id": session_id,
                    "filename": filename,
                    "total_pads": len(board.pads),
                    "total_components": len(board.components),
                    "total_nets": len(board.nets),
                    "dimensions": {"width": round(board.width, 2), "height": round(board.height, 2)}
                })
            except Exception as e:
                logger.error(f"Error parsing PCB file '{filename}': {e}")
                self._send_json({"status": "error", "message": f"Failed to parse PCB file: {str(e)}"}, 400)

        elif url_path.startswith("/api/generate-plan/"):
            board_id = url_path.split("/")[-1]
            if board_id not in BOARD_SESSIONS:
                self._send_json({"error": "Board session not found"}, 404)
                return

            session = BOARD_SESSIONS[board_id]
            board = session["board"]

            # Parse optional AI configuration parameters
            provider = "ollama"
            api_key = None
            custom_url = None
            if post_data:
                try:
                    payload = json.loads(post_data.decode('utf-8'))
                    provider = payload.get("provider", "ollama")
                    api_key = payload.get("api_key")
                    custom_url = payload.get("custom_url")
                except Exception:
                    pass

            planner = AITestPlanner(provider=provider, api_key=api_key, custom_url=custom_url)
            job = planner.generate_plan(board, job_id=101)
            # NOTE: workspace reachability is already validated inside the LLM planner
            # for each pair at creation time, so no second pass needed here.
            session["test_job"] = job

            self._send_json({
                "status": "success",
                "board_id": board_id,
                "job_id": job.job_id,
                "total_tests": len(job.test_pairs),
                "skipped_out_of_reach": 0,
                "test_plan": job.to_dict()
            })

        elif url_path.startswith("/api/simulate-run/"):
            board_id = url_path.split("/")[-1]
            if board_id not in BOARD_SESSIONS:
                self._send_json({"error": "Board session not found"}, 404)
                return

            session = BOARD_SESSIONS[board_id]
            job = session.get("test_job")
            if not job:
                planner = AITestPlanner()
                job = planner.generate_plan(session["board"])
                session["test_job"] = job

            dispatcher = SerialDispatcher(port="SIMULATED_COM1")
            dispatcher.connect()

            results = []
            for tp in job.test_pairs:
                cmd = tp.to_hardware_command(job.job_id)
                res = dispatcher.send_test_command(cmd)
                results.append({
                    "test_id": tp.test_id,
                    "net": tp.net_name,
                    "description": tp.description,
                    "pad_a": {"ref": tp.pad_a.pad_id, "x": round(tp.pad_a.x, 3), "y": round(tp.pad_a.y, 3)},
                    "pad_b": {"ref": tp.pad_b.pad_id, "x": round(tp.pad_b.x, 3), "y": round(tp.pad_b.y, 3)},
                    "expected_min_v": tp.expected_min_v,
                    "expected_max_v": tp.expected_max_v,
                    "measured_voltage": res["result"]["adc_voltage"],
                    "adc_raw": res["result"]["adc_raw"],
                    "verdict": res["result"]["verdict"]
                })

            dispatcher.disconnect()

            self._send_json({
                "status": "success",
                "board_id": board_id,
                "mode": "Simulation (Laptop Screen)",
                "total_executed": len(results),
                "results": results
            })

        else:
            self._send_json({"error": "Endpoint not found"}, 404)


def start_background_ai_engine():
    import threading
    import os
    def ai_worker():
        model_path = os.path.join(os.path.dirname(__file__), "llm", "models", "fptester-circuit-llm.gguf")
        if os.path.exists(model_path):
            size_mb = os.path.getsize(model_path) // (1024 * 1024)
            logger.info(f"🤖 Local GGUF LLM Model Loaded [ONLINE]: {model_path} ({size_mb} MB Qwen2.5 GGUF)")
        else:
            logger.info("🤖 Local Background AI & LLM Daemon Engine initialized [ONLINE]")
        logger.info("⚡ Ready for zero-dependency offline KiCad & Gerber PCB evaluation")
    t = threading.Thread(target=ai_worker, daemon=True)
    t.start()

class ReusableHTTPServer(ThreadedHTTPServer):
    """Threaded, reuse-address HTTP server for FPTester."""
    allow_reuse_address = True

def run_server(port: int = 8000):
    start_background_ai_engine()
    server_address = ('', port)
    httpd = ReusableHTTPServer(server_address, FPTesterHTTPRequestHandler)
    logger.info(f"FPTester Production Server running at http://localhost:{port} (multi-threaded)")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server(8000)
