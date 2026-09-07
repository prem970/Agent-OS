from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: str = "data/iris.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connection() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, prompt TEXT,
                state TEXT, strategy TEXT, result TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS experiences (id INTEGER PRIMARY KEY, keywords TEXT, strategy TEXT,
                outcome REAL, lesson TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            """)

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def connection(self):
        db = self.connect()
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def save_task(self, title: str, prompt: str, state: dict, strategy: dict, result: dict) -> int:
        with self.connection() as db:
            cursor = db.execute("INSERT INTO tasks(title,prompt,state,strategy,result) VALUES(?,?,?,?,?)",
                (title, prompt, json.dumps(state), json.dumps(strategy), json.dumps(result)))
            return cursor.lastrowid

    def list_tasks(self) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT id,title,created_at,result FROM tasks ORDER BY id DESC LIMIT 50").fetchall()
        return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"], **json.loads(r["result"])} for r in rows]

    def task(self, task_id: int) -> dict | None:
        with self.connection() as db:
            r = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not r: return None
        return {k: (json.loads(r[k]) if k in ("state", "strategy", "result") else r[k]) for k in r.keys()}

    def save_experience(self, keywords: list[str], strategy: dict, outcome: float, lesson: str) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO experiences(keywords,strategy,outcome,lesson) VALUES(?,?,?,?)",
                (json.dumps(keywords), json.dumps(strategy), outcome, lesson))

    def similar(self, keywords: list[str]) -> dict | None:
        wanted = set(keywords)
        with self.connection() as db:
            rows = db.execute("SELECT * FROM experiences WHERE outcome >= .65 ORDER BY id DESC LIMIT 100").fetchall()
        scored = [(len(wanted & set(json.loads(r["keywords"]))) / max(1, len(wanted | set(json.loads(r["keywords"])))), r) for r in rows]
        scored = [item for item in scored if item[0] > 0]
        if not scored: return None
        _, row = max(scored, key=lambda x: x[0])
        return {"id": row["id"], "strategy": json.loads(row["strategy"]), "lesson": row["lesson"]}
