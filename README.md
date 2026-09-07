# IRIS — Enterprise Multi-Agent Operating System

IRIS turns a startup task into a CEO-led operating workflow: the CEO defines a
plan, specialist agents work in parallel, and an independent reviewer checks
the combined delivery. Every run has a persisted strategy, output, cost
estimate, and execution trace.

## Run

Requires Python 3.11+. Install the OpenAI SDK used for NVIDIA NIM:

```powershell
uv pip install -r requirements.txt
uv run --python 3.11 python run.py
```

Open `http://127.0.0.1:8000`. The SQLite database is created at `data/iris.db`.

## NVIDIA NIM setup

Set an NVIDIA API key before starting IRIS to use real LLM calls:

```powershell
$env:NVIDIA_API_KEY = "nvapi-..."
$env:NIM_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b" # optional
uv run --python 3.11 python run.py
```

IRIS uses the OpenAI Python SDK against NVIDIA NIM's OpenAI-compatible
`POST /v1/chat/completions` endpoint, with streaming and NVIDIA reasoning
enabled. Each role can use a separate `NVIDIA_API_KEY_<ROLE>` so access, usage,
and rate limits can be isolated; see `.env.example`. For a self-hosted NIM,
configure `NIM_BASE_URL` with its `/v1` URL. If no key is present or the SDK is
not installed, IRIS produces safe local simulated outputs. Set
`IRIS_RUNTIME=simulated` to force local mode.

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
