"""
RMP Dashboard Local Server
==========================
Serves the dashboard and provides API endpoints to run the scraper.

Usage:
    python server.py

Then open:  http://localhost:8765
"""

import http.server
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

PORT = 8766
BASE_DIR = Path(__file__).parent
HTML_FILE = BASE_DIR / "rmp_dashboard.html"
CSV_FILE  = BASE_DIR / "all_schools_rmp_cleaned.csv"
SCRIPT    = BASE_DIR / "all_schools_rmp.py"

# ── Scraper state ──────────────────────────────────────────
_state = {
    "status": "idle",      # idle | running | done | error
    "log":    [],
    "started": None,
    "finished": None,
}
_lock = threading.Lock()


def _run_scraper():
    with _lock:
        _state["status"]   = "running"
        _state["log"]      = []
        _state["started"]  = time.strftime("%H:%M:%S")
        _state["finished"] = None

    try:
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPT)],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in proc.stdout:
            line = line.rstrip()
            with _lock:
                _state["log"].append(line)
                # Keep last 200 lines so memory doesn't grow unbounded
                if len(_state["log"]) > 200:
                    _state["log"] = _state["log"][-200:]

        proc.wait()
        with _lock:
            if proc.returncode == 0:
                _state["status"]   = "done"
            else:
                _state["status"]   = "error"
            _state["finished"] = time.strftime("%H:%M:%S")

    except Exception as e:
        with _lock:
            _state["status"]   = "error"
            _state["log"].append(f"Exception: {e}")
            _state["finished"] = time.strftime("%H:%M:%S")


# ── HTTP handler ───────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress default access logs

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        # ── Dashboard HTML ──────────────────────────────────
        if path in ("/", "/rmp_dashboard.html"):
            try:
                content = HTML_FILE.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self._json(404, {"error": "rmp_dashboard.html not found"})

        # ── CSV data ────────────────────────────────────────
        elif path == "/data":
            if not CSV_FILE.exists():
                self._json(404, {"error": "CSV not found. Run the scraper first."})
                return
            content = CSV_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)

        # ── Scraper status ──────────────────────────────────
        elif path == "/status":
            with _lock:
                snap = dict(_state)
                snap["csv_exists"] = CSV_FILE.exists()
                if CSV_FILE.exists():
                    snap["csv_mtime"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(CSV_FILE.stat().st_mtime)
                    )
                else:
                    snap["csv_mtime"] = None
            self._json(200, snap)

        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        path = self.path.split("?")[0]

        # ── Trigger scraper ─────────────────────────────────
        if path == "/run":
            with _lock:
                if _state["status"] == "running":
                    self._json(409, {"error": "Scraper is already running"})
                    return
            t = threading.Thread(target=_run_scraper, daemon=True)
            t.start()
            self._json(200, {"message": "Scraper started"})
        else:
            self._json(404, {"error": "Not found"})


# ── Entry point ────────────────────────────────────────────
if __name__ == "__main__":
    server = http.server.HTTPServer(("localhost", PORT), Handler)
    print(f"")
    print(f"  RMP Dashboard server running")
    print(f"  Open:  http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop")
    print(f"")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
