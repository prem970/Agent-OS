from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .firewall import AgentFirewall
from .orchestrator import IrisController
from .registry import AGENTS
from .storage import Store
from .workspace import WorkspaceManager

STORE = Store()
WORKSPACE = WorkspaceManager()
APP = IrisController(STORE, WORKSPACE)
HTML_PATH = Path(__file__).with_name("dashboard.html")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, status: int, payload: Any, content_type: str = "application/json"):
        if isinstance(payload, bytes):
            data = payload
        elif isinstance(payload, str):
            data = payload.encode("utf-8")
        else:
            data = json.dumps(payload).encode("utf-8")

        self.send_response(status)
        if "charset" not in content_type and ("text" in content_type or "json" in content_type):
            content_type = f"{content_type}; charset=utf-8"
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. Dashboard Root HTML
        if path == "/":
            return self.send(200, HTML_PATH.read_text(encoding="utf-8"), "text/html")

        # 2. Workspace Static Files Serving (Live Preview)
        if path.startswith("/workspace/"):
            filename = path.replace("/workspace/", "").strip("/")
            if not filename:
                filename = "index.html"
            content = WORKSPACE.read_file(filename)
            if content is None:
                return self.send(404, {"error": f"File '{filename}' not found in workspace"})
            ctype, _ = mimetypes.guess_type(filename)
            return self.send(200, content, ctype or "text/plain")

        # 3. Tasks & Dashboard Analytics
        if path == "/api/tasks":
            return self.send(200, APP.store.list_tasks())

        if path == "/api/dashboard":
            tasks = APP.store.list_tasks()
            experiences = APP.store.list_experiences()
            files = WORKSPACE.list_files()
            completed = len(tasks)
            success_rate = round(sum(t.get("success", False) for t in tasks) / max(1, completed), 2)
            return self.send(200, {
                "tasks": tasks,
                "completed": completed,
                "success_rate": success_rate,
                "memory_count": len(experiences),
                "workspace_files_count": len(files)
            })

        if path.startswith("/api/tasks/"):
            task_id = int(path.rsplit("/", 1)[1])
            item = APP.store.task(task_id)
            return self.send(200 if item else 404, item or {"error": "not found"})

        # 4. Agents Directory & Firewall Spec
        if path == "/api/agents":
            agents_list = []
            for a in AGENTS:
                rule = AgentFirewall.RULES.get(a.id, {})
                client = APP.runtime._client_for(a)
                agents_list.append({
                    "id": a.id,
                    "name": a.name,
                    "capabilities": list(a.capabilities),
                    "model": a.model,
                    "tools": list(a.tools),
                    "cost_per_turn": a.cost_per_turn,
                    "latency_ms": a.latency_ms,
                    "reliability": a.reliability,
                    "mandate": a.mandate,
                    "firewall_rule": {
                        "mandate": rule.get("mandate", ""),
                        "forbidden_count": len(rule.get("forbidden_patterns", []))
                    },
                    "nim_enabled": client.enabled,
                    "provider": "NVIDIA NIM" if client.enabled else "Simulated"
                })
            return self.send(200, agents_list)

        # 5. Workspace File Management API
        if path == "/api/workspace":
            return self.send(200, {
                "workspace_path": str(WORKSPACE.workspace_dir),
                "files": WORKSPACE.list_files()
            })

        if path == "/api/workspace/file":
            filename = query.get("name", [""])[0]
            if not filename:
                return self.send(400, {"error": "name parameter required"})
            content = WORKSPACE.read_file(filename)
            if content is None:
                return self.send(404, {"error": f"File '{filename}' not found"})
            return self.send(200, {"name": filename, "content": content})

        # 6. Memory & Knowledge Bank
        if path == "/api/memories":
            return self.send(200, APP.store.list_experiences())

        # 7. System Diagnostic
        if path == "/api/system":
            nim_key = bool(os.getenv("NVIDIA_API_KEY"))
            nim_model = os.getenv("NIM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
            runtime_mode = os.getenv("IRIS_RUNTIME", "nim")
            return self.send(200, {
                "python_version": sys.version.split()[0],
                "database_path": str(Path(APP.store.path).resolve()),
                "workspace_dir": str(WORKSPACE.workspace_dir.resolve()),
                "nvidia_api_key_configured": nim_key,
                "nim_model": nim_model,
                "runtime_mode": runtime_mode,
                "active_engine": "NVIDIA NIM (Cloud/On-Prem)" if nim_key and runtime_mode != "simulated" else "Local Autonomous Simulated Engine"
            })

        self.send(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
        except Exception as error:
            return self.send(400, {"error": f"Invalid JSON payload: {error}"})

        # 1. Run Squad Co-work Task
        if path == "/api/tasks":
            title = body.get("title", "Untitled task").strip()
            prompt = body.get("prompt", "").strip()
            if not prompt:
                return self.send(400, {"error": "prompt is required"})
            budget = max(0.02, min(5.0, float(body.get("budget", 0.25))))
            baseline = body.get("baseline", "B8")
            result = APP.run(title, prompt, budget, baseline)
            return self.send(201, result)

        # 2. 1-on-1 Individual Agent Chat with Strict Firewall Enforcement
        if path.startswith("/api/agents/") and path.endswith("/chat"):
            agent_id = path.split("/")[3]
            prompt = body.get("prompt", "").strip()
            if not prompt:
                return self.send(400, {"error": "prompt is required"})
            response = APP.run_single_agent(agent_id, prompt)
            return self.send(200, response)

        # 3. Create or Update Workspace File
        if path == "/api/workspace/file":
            filename = body.get("name", "").strip()
            content = body.get("content", "")
            if not filename:
                return self.send(400, {"error": "name is required"})
            saved = WORKSPACE.write_file(filename, content)
            return self.send(200, {"status": "saved", "name": saved})

        # 4. Teach / Add Organizational Memory
        if path == "/api/memories":
            keywords = body.get("keywords", [])
            lesson = body.get("lesson", "").strip()
            if not lesson:
                return self.send(400, {"error": "lesson is required"})
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",") if k.strip()]
            if not keywords:
                keywords = ["general", "startup"]
            strategy = body.get("strategy", {"topology": "parallel", "communication": "selective", "verification": True})
            outcome = float(body.get("outcome", 0.95))
            APP.store.save_experience(keywords, strategy, outcome, lesson)
            return self.send(201, {"status": "memory_stored", "keywords": keywords, "lesson": lesson})

        # 5. Execute Script in Workspace Locally
        if path == "/api/workspace/run":
            script_path = body.get("path", "").strip()
            if not script_path:
                return self.send(400, {"error": "path is required"})
            parts = script_path.split("/", 1)
            project = parts[0] if len(parts) > 1 else ""
            script = parts[1] if len(parts) > 1 else parts[0]
            result = WORKSPACE.tools.execute_script(project, script)
            return self.send(200, result)

        self.send(404, {"error": "not found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Delete Workspace File
        if path == "/api/workspace/file":
            filename = query.get("name", [""])[0]
            if not filename:
                return self.send(400, {"error": "name parameter required"})
            ok = WORKSPACE.delete_file(filename)
            return self.send(200 if ok else 404, {"success": ok})

        # Delete Memory
        if path.startswith("/api/memories/"):
            exp_id = int(path.rsplit("/", 1)[1])
            ok = APP.store.delete_experience(exp_id)
            return self.send(200 if ok else 404, {"success": ok})

        self.send(404, {"error": "not found"})


def serve():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"==================================================")
    print(f"🚀 IRIS Startup Agent OS (Claude Co-Work Edition)")
    print(f"   Dashboard: http://127.0.0.1:{args.port}")
    print(f"   Workspace: {WORKSPACE.workspace_dir}")
    print(f"==================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
