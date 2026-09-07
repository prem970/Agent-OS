# IRIS — Enterprise Multi-Agent Operating System

IRIS turns a startup task into a CEO-led operating workflow: the CEO defines a
plan, specialist agents work in parallel, and an independent reviewer checks
the combined delivery. Every run has a persisted strategy, output, cost
estimate, and execution trace.

## Run

Requires Python 3.11+ and no third-party packages:

```powershell
uv run --python 3.11 python run.py
```

Open `http://127.0.0.1:8000`. The SQLite database is created at `data/iris.db`.

## NVIDIA NIM setup

Set an NVIDIA API key before starting IRIS to use real LLM calls:

```powershell
$env:NVIDIA_API_KEY = "nvapi-..."
$env:NIM_MODEL = "meta/llama-3.3-70b-instruct" # optional
uv run --python 3.11 python run.py
```

IRIS calls NVIDIA NIM's OpenAI-compatible `POST /v1/chat/completions` endpoint.
For a self-hosted NIM, configure `NIM_BASE_URL` with its `/v1` URL. If no key is
present, IRIS produces safe local simulated outputs so the dashboard and test
suite remain usable. Set `IRIS_RUNTIME=simulated` to force local mode.

## Startup squad

- CEO Agent — scope, priorities, acceptance criteria, and risk ownership
- HR Agent — people, hiring, and policy work when the task needs it
- Resource Agent — dependencies, research, references, and resource planning
- Full-Stack Architect — system and integration design
- Developer Agent — implementation handoff
- Testing Agent — test plan and quality evidence
- Review Agent — independent quality, security, and delivery review

At the Startup Squad (B8) level, IRIS schedules the CEO, Resource,
Full-Stack, Developer, Testing, and Review roles. The delivery roles execute
concurrently after the CEO plan, so a single task has five or more agents
working toward one delivery. HR is added automatically for people-related work.

The system does not grant agents filesystem, browser, deployment, or HR-system
access by itself. Add explicit, audited tool adapters before allowing external
actions.

## API

`POST /api/tasks`

```json
{"title":"Fix a Python parser","prompt":"Implement and test a parser","budget":0.25,"baseline":"B8"}
```

`GET /api/tasks`, `GET /api/tasks/{id}`, and `GET /api/dashboard` expose saved
results.
