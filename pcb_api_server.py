"""
OpenFPT Production Web & REST API Server (Built-in Zero-Dependency HTTP Engine)
Runs natively on any laptop without requiring external pip packages.
Provides endpoints for PCB file uploading, AI test plan generation, 2D dual-arm laptop simulation,
and ESP32 USB hardware dispatch.
"""
import os
import sys
import json
import uuid
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

# Ensure parser modules are accessible
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from parser.kicad_parser import KiCadPCBParser
from parser.gerber_parser import GerberParser
from parser.ai_planner import AITestPlanner
from parser.workspace import WorkspaceValidator
from parser.serial_dispatcher import SerialDispatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OpenFPT_HTTP_Server")

# In-Memory Session Store
BOARD_SESSIONS: dict = {}

class OpenFPTHTTPRequestHandler(BaseHTTPRequestHandler):
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
                self._send_html("<h1>OpenFPT Server Online</h1><p>Frontend index.html not found.</p>")

        elif url_path == "/api/health":
            self._send_json({"status": "online", "system": "OpenFPT HTTP Server", "version": "2.0.0"})

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

            # Extract filename from query or MIME header if present
            filename = "uploaded_design.kicad_pcb"
            query = urllib.parse.urlparse(self.path).query
            query_params = urllib.parse.parse_qs(query)
            if 'filename' in query_params:
                filename = query_params['filename'][0]

            # Strip multi-part form-data headers if present
            if '(kicad_pcb' in content_str:
                start_idx = content_str.find('(kicad_pcb')
                end_idx = content_str.rfind(')')
                if start_idx != -1 and end_idx != -1:
                    content_str = content_str[start_idx:end_idx + 1]

            try:
                if 'kicad_pcb' in content_str:
                    parser = KiCadPCBParser()
                    board = parser.parse_string(content_str, board_name=filename)
                else:
                    parser = GerberParser()
                    board = parser.parse_string(content_str, board_name=filename)

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

            planner = AITestPlanner()
            job = planner.generate_plan(board, job_id=101)

            # Reachability filter
            validator = WorkspaceValidator()
            valid_pairs = []
            skipped = 0
            for tp in job.test_pairs:
                if tp.pad_a.y > tp.pad_b.y:
                    tp.pad_a, tp.pad_b = tp.pad_b, tp.pad_a
                ok, _ = validator.validate_pad_pair(tp.pad_a, tp.pad_b)
                if ok:
                    valid_pairs.append(tp)
                else:
                    skipped += 1

            job.test_pairs = valid_pairs
            session["test_job"] = job

            self._send_json({
                "status": "success",
                "board_id": board_id,
                "job_id": job.job_id,
                "total_tests": len(job.test_pairs),
                "skipped_out_of_reach": skipped,
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


def run_server(port: int = 8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, OpenFPTHTTPRequestHandler)
    logger.info(f"OpenFPT Production Server running at http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server(8000)
