from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from .orchestrator import IrisController
from .storage import Store


APP = IrisController(Store())
HTML = Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send(self, status, payload, content_type="application/json"):
        data = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
        self.send_response(status); self.send_header("Content-Type", f"{content_type}; charset=utf-8"); self.send_header("Content-Length", len(data)); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/": return self.send(200, HTML, "text/html")
        if path == "/api/tasks": return self.send(200, APP.store.list_tasks())
        if path == "/api/dashboard":
            tasks = APP.store.list_tasks(); return self.send(200, {"tasks": tasks, "completed": len(tasks), "success_rate": round(sum(t["success"] for t in tasks)/max(1,len(tasks)), 2)})
        if path.startswith("/api/tasks/"):
            item = APP.store.task(int(path.rsplit("/", 1)[1])); return self.send(200 if item else 404, item or {"error":"not found"})
        self.send(404, {"error": "not found"})
    def do_POST(self):
        if urlparse(self.path).path != "/api/tasks": return self.send(404, {"error":"not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            title, prompt = body.get("title", "Untitled task").strip(), body.get("prompt", "").strip()
            if not prompt: return self.send(400, {"error":"prompt is required"})
            budget = max(.02, min(5.0, float(body.get("budget", .25))))
            return self.send(201, APP.run(title, prompt, budget, body.get("baseline", "B8")))
        except (ValueError, json.JSONDecodeError) as error: self.send(400, {"error": str(error)})


def serve():
    parser = argparse.ArgumentParser(); parser.add_argument("--port", type=int, default=8000); args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"IRIS dashboard: http://127.0.0.1:{args.port}")
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
