from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any


from .tools import LocalSystemTools, slugify


class WorkspaceManager:
    """Manages the real workspace/ directory for IRIS agents to develop websites and projects."""

    def __init__(self, workspace_dir: str | Path | None = None):
        if workspace_dir is None:
            # Default to 'workspace' in the project root
            base_dir = Path(__file__).resolve().parent.parent
            self.workspace_dir = base_dir / "workspace"
        else:
            self.workspace_dir = Path(workspace_dir)

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.tools = LocalSystemTools(self.workspace_dir)
        self._seed_default_workspace()

    def _seed_default_workspace(self) -> None:
        """Seeds an initial working demo project if workspace is empty."""
        index_file = self.workspace_dir / "index.html"
        if not index_file.exists():
            index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IRIS Startup Launchpad</title>
    <link rel="stylesheet" href="styles.css">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body>
    <div class="glow-sphere"></div>
    <div class="container">
        <header>
            <div class="badge">🚀 Autonomous Startup Squad Workspace</div>
            <h1>Built by IRIS Agent OS</h1>
            <p class="subtitle">Every file in this workspace folder is generated and maintained live by your AI startup agents.</p>
        </header>

        <section class="grid">
            <div class="card">
                <div class="icon">⚡</div>
                <h3>CEO Roadmap</h3>
                <p>Strategic vision, business scope, acceptance criteria, and executive planning.</p>
                <span class="status active">Active & Deployed</span>
            </div>
            <div class="card">
                <div class="icon">🏗️</div>
                <h3>Full-Stack Blueprint</h3>
                <p>Component architecture, data flows, REST schemas, and responsive UI foundations.</p>
                <span class="status active">Active & Deployed</span>
            </div>
            <div class="card">
                <div class="icon">💻</div>
                <h3>Developer Codebase</h3>
                <p>Clean HTML5, modern vanilla CSS animations, and modular JavaScript execution.</p>
                <span class="status active">Active & Deployed</span>
            </div>
            <div class="card">
                <div class="icon">🛡️</div>
                <h3>Security & Review Gate</h3>
                <p>Strict agent firewall boundaries and independent verification checks.</p>
                <span class="status active">Enforced</span>
            </div>
        </section>

        <div class="action-panel">
            <button id="cta-btn" onclick="triggerInteractivity()">Test Live Workspace Interactivity</button>
            <div id="output-box" class="output-box">Ready. Click above to verify live JS execution.</div>
        </div>
    </div>
    <script src="app.js"></script>
</body>
</html>"""
            self.write_file("index.html", index_html)

        css_file = self.workspace_dir / "styles.css"
        if not css_file.exists():
            css_code = """* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: radial-gradient(circle at 50% 0%, #111d38 0%, #080d1a 100%);
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 32px 16px;
    position: relative;
    overflow-x: hidden;
}
.glow-sphere {
    position: absolute;
    top: -100px;
    left: 50%;
    transform: translateX(-50%);
    width: 600px;
    height: 350px;
    background: radial-gradient(circle, rgba(16, 185, 129, 0.18) 0%, rgba(6, 182, 212, 0.08) 50%, transparent 70%);
    filter: blur(50px);
    pointer-events: none;
}
.container {
    max-width: 960px;
    width: 100%;
    position: relative;
    z-index: 10;
}
header {
    text-align: center;
    margin-bottom: 36px;
}
.badge {
    display: inline-block;
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 14px;
}
h1 {
    font-family: 'Outfit', sans-serif;
    font-size: 2.75rem;
    font-weight: 800;
    background: linear-gradient(135deg, #ffffff 30%, #93c5fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
}
.subtitle {
    color: #94a3b8;
    font-size: 1.1rem;
    max-width: 620px;
    margin: 0 auto;
    line-height: 1.6;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 18px;
    margin-bottom: 32px;
}
.card {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(51, 65, 85, 0.7);
    backdrop-filter: blur(12px);
    border-radius: 14px;
    padding: 22px;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
.card:hover {
    transform: translateY(-4px);
    border-color: rgba(56, 189, 248, 0.5);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);
}
.icon {
    font-size: 1.8rem;
    margin-bottom: 12px;
}
h3 {
    font-family: 'Outfit', sans-serif;
    color: #f8fafc;
    font-size: 1.2rem;
    margin-bottom: 8px;
}
.card p {
    color: #94a3b8;
    font-size: 0.88rem;
    line-height: 1.5;
    margin-bottom: 16px;
}
.status {
    display: inline-block;
    font-size: 0.75rem;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 600;
}
.status.active {
    background: rgba(16, 185, 129, 0.2);
    color: #6ee7b7;
}
.action-panel {
    text-align: center;
    background: rgba(15, 23, 42, 0.5);
    border: 1px dashed rgba(71, 85, 105, 0.6);
    border-radius: 14px;
    padding: 24px;
}
button {
    background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
    color: #03131e;
    font-weight: 700;
    font-size: 0.95rem;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
}
button:hover {
    opacity: 0.92;
    transform: scale(1.02);
}
.output-box {
    margin-top: 14px;
    font-family: monospace;
    color: #38bdf8;
    font-size: 0.9rem;
}"""
            self.write_file("styles.css", css_code)

        js_file = self.workspace_dir / "app.js"
        if not js_file.exists():
            js_code = """function triggerInteractivity() {
    const box = document.getElementById('output-box');
    const timestamp = new Date().toLocaleTimeString();
    box.innerHTML = `✨ <strong>Live Verification Passed:</strong> IRIS Workspace is executing JavaScript locally at ${timestamp}.`;
    box.style.color = '#34d399';
}"""
            self.write_file("app.js", js_code)

    def list_files(self) -> list[dict[str, Any]]:
        """Returns a list of all files in workspace/."""
        files = []
        if not self.workspace_dir.exists():
            return files

        for path in sorted(self.workspace_dir.glob("**/*")):
            if path.is_file():
                rel_path = path.relative_to(self.workspace_dir).as_posix()
                ext = path.suffix.lower().lstrip(".")
                stat = path.stat()
                files.append({
                    "name": rel_path,
                    "size": stat.st_size,
                    "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                    "ext": ext,
                    "is_web": ext in ("html", "htm", "css", "js")
                })
        return files

    def read_file(self, filename: str) -> str | None:
        """Safely reads a file from workspace/."""
        target = (self.workspace_dir / filename).resolve()
        if not target.is_relative_to(self.workspace_dir.resolve()):
            return None
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            return None
        try:
            return target.read_text(encoding="utf-8")
        except Exception:
            return None

    def write_file(self, filename: str, content: str) -> str:
        """Safely writes a file to workspace/."""
        target = (self.workspace_dir / filename).resolve()
        if not target.is_relative_to(self.workspace_dir.resolve()):
            raise ValueError("Path traversal attempt detected")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target.name

    def delete_file(self, filename: str) -> bool:
        """Safely deletes a file from workspace/."""
        target = (self.workspace_dir / filename).resolve()
        if not target.is_relative_to(self.workspace_dir.resolve()) or not target.is_file():
            return False
        target.unlink(missing_ok=True)
        return True

    def extract_and_save_artifacts(self, text: str, prompt_hint: str = "", project_slug: str | None = None) -> list[str]:
        """Extracts code blocks or project files from LLM text and saves them into workspace/<project_slug>/."""
        saved_files = []
        slug = project_slug or slugify(prompt_hint or "project")

        # Create the local project folder on the system
        project_folder = self.tools.create_project_folder(slug)

        # 1. Look for patterns like ```html:index.html or ```python:main.py or ### File: index.html
        code_block_pattern = re.compile(
            r"(?:(?:###|\*\*)\s*File:\s*`?([\w\-./\\]+)`?|(?:```([a-zA-Z0-9_\-]+)[:\s]([\w\-./\\]+)))\s*\n(.*?)(?=```|\Z)",
            re.DOTALL
        )

        matches = code_block_pattern.findall(text)
        for m in matches:
            filename = m[0] or m[2]
            code = m[3] if (m[0] or m[2]) else ""
            if filename and code.strip():
                clean_name = Path(filename.strip()).name
                # Save to project folder
                self.tools.write_file_to_project(slug, clean_name, code.strip())
                # Also save to root workspace for immediate fallback
                self.write_file(clean_name, code.strip())
                saved_files.append(f"{slug}/{clean_name}")

        # 2. If website creation was requested and specific files weren't explicitly marked with filenames:
        prompt_lower = prompt_hint.lower()
        if ("website" in prompt_lower or "web page" in prompt_lower or "landing page" in prompt_lower) and not saved_files:
            html_match = re.search(r"```html\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
            if html_match:
                content = html_match.group(1).strip()
                self.tools.write_file_to_project(slug, "index.html", content)
                self.write_file("index.html", content)
                saved_files.append(f"{slug}/index.html")

            css_match = re.search(r"```css\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
            if css_match:
                content = css_match.group(1).strip()
                self.tools.write_file_to_project(slug, "styles.css", content)
                self.write_file("styles.css", content)
                saved_files.append(f"{slug}/styles.css")

            js_match = re.search(r"```(?:javascript|js)\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
            if js_match:
                content = js_match.group(1).strip()
                self.tools.write_file_to_project(slug, "app.js", content)
                self.write_file("app.js", content)
                saved_files.append(f"{slug}/app.js")

        # 3. If python script was generated:
        if ("python" in prompt_lower or "script" in prompt_lower or "parser" in prompt_lower) and not saved_files:
            py_match = re.search(r"```(?:python|py)\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
            if py_match:
                fname = "parser.py" if "parser" in prompt_lower else "solution.py"
                content = py_match.group(1).strip()
                self.tools.write_file_to_project(slug, fname, content)
                self.write_file(fname, content)
                saved_files.append(f"{slug}/{fname}")

        # Write a README.md in the project folder detailing that it was built by IRIS Agent
        readme_content = f"# {slug.replace('-', ' ').title()}\n\nAutonomously generated and verified on local machine by IRIS Agent OS.\n\nTask Goal: {prompt_hint}\n"
        self.tools.write_file_to_project(slug, "README.md", readme_content)
        saved_files.append(f"{slug}/README.md")

        return saved_files

