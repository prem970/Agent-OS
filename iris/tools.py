from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def slugify(text: str) -> str:
    """Converts a title or prompt into a clean folder name."""
    clean = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "-", clean)
    return slug[:40] or "project"


class LocalSystemTools:
    """Real local system execution tools for autonomous IRIS agents."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def create_project_folder(self, project_name: str) -> Path:
        """Creates a dedicated project folder inside the workspace on the local system."""
        slug = slugify(project_name)
        folder = (self.workspace_root / slug).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def write_file_to_project(self, project_name: str, relative_path: str, content: str) -> Dict[str, Any]:
        """Writes a real file to disk within the specified project folder."""
        folder = self.create_project_folder(project_name)
        clean_rel = relative_path.lstrip("/\\")
        target_path = (folder / clean_rel).resolve()

        if not target_path.is_relative_to(folder):
            raise ValueError("Path traversal outside project folder is prohibited")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")

        stat = target_path.stat()
        return {
            "name": clean_rel,
            "full_path": str(target_path),
            "size": stat.st_size,
            "folder": folder.name,
            "relative_workspace_path": f"{folder.name}/{clean_rel}"
        }

    def execute_script(self, project_name: str, script_name: str, timeout: int = 15) -> Dict[str, Any]:
        """Executes a script on the local machine, capturing exit code, stdout, and stderr."""
        folder = self.create_project_folder(project_name)
        target_path = (folder / script_name).resolve()

        if not target_path.is_file():
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"File not found: {script_name}"
            }

        cmd = [sys.executable, str(target_path)] if script_name.endswith(".py") else [str(target_path)]
        try:
            res = subprocess.run(
                cmd,
                cwd=str(folder),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": res.returncode == 0,
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e)
            }

    def verify_project(self, project_name: str) -> Dict[str, Any]:
        """Checks files on disk and verifies local integrity."""
        folder = self.create_project_folder(project_name)
        files = list(folder.glob("**/*"))
        file_count = sum(1 for f in files if f.is_file())

        py_files = [f for f in files if f.is_file() and f.suffix == ".py"]
        py_test_result = None
        if py_files:
            # Run the primary python file to test
            primary_py = py_files[0].name
            py_test_result = self.execute_script(project_name, primary_py, timeout=8)

        html_files = [f for f in files if f.is_file() and f.suffix in (".html", ".htm")]

        return {
            "folder": folder.name,
            "absolute_path": str(folder),
            "file_count": file_count,
            "has_web": len(html_files) > 0,
            "web_entry": f"{folder.name}/{html_files[0].name}" if html_files else None,
            "script_verification": py_test_result
        }
