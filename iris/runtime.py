from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from .models import Agent, RunResult, Strategy, TaskState


class NIMClient:
    """NVIDIA NIM client with a separately configurable connection per role."""
    def __init__(self, agent_id: str):
        suffix = agent_id.upper()
        self.api_key = os.getenv(f"NVIDIA_API_KEY_{suffix}") or os.getenv("NVIDIA_API_KEY", "")
        self.base_url = os.getenv(f"NIM_BASE_URL_{suffix}") or os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.model = os.getenv(f"NIM_MODEL_{suffix}") or os.getenv("NIM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and OpenAI is not None and os.getenv("IRIS_RUNTIME", "nim").lower() != "simulated"

    def chat(self, system: str, user: str) -> tuple[str, int]:
        client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.4, top_p=0.95, max_tokens=4096,
                extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 4096},
                stream=True,
            )
            answer, tokens = [], 0
            for chunk in completion:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content is not None:
                    answer.append(delta.content)
                if getattr(chunk, "usage", None):
                    tokens = chunk.usage.total_tokens or tokens
        except Exception as error:
            raise RuntimeError(f"NIM request failed: {error}") from error
        return "".join(answer).strip() or "No deliverable returned.", int(tokens)


class AgentRuntime:
    """CEO plan -> parallel specialist delivery -> independent review."""
    def __init__(self): self.clients: dict[str, NIMClient] = {}

    def _client_for(self, agent: Agent) -> NIMClient:
        if agent.id not in self.clients: self.clients[agent.id] = NIMClient(agent.id)
        return self.clients[agent.id]

    def _prompt(self, agent: Agent, state: TaskState, context: str = "") -> tuple[str, str]:
        boundaries = {
            "ceo": "Set priorities and approve scope only; do not claim to code, test, hire, or take external actions.",
            "hr": "Handle people operations, hiring, policies, and organization risks only. Never design software, write code, or make architecture decisions.",
            "resource": "Handle dependencies, research needs, budgets, vendors, and resources only. Never write production code or make final delivery decisions.",
            "fullstack": "Design application architecture, APIs, data flow, and integration plans only. Never claim to implement, test, deploy, or approve people policy.",
            "developer": "Handle implementation, code changes, debugging, and developer handoffs only. Never make HR decisions, approve budgets, invent policy, or sign off quality.",
            "testing": "Handle test strategy, test cases, quality evidence, and defect reports only. Never implement production features, approve scope, or make HR decisions.",
            "review": "Independently assess evidence for quality, security, risks, and acceptance only. Never implement work, change policy, or make unverified claims.",
        }
        system = (f"You are the {agent.name} in an enterprise startup operating system. {agent.mandate} "
                  f"Hard boundary: {boundaries[agent.id]} If asked outside this boundary, name the handoff role instead. "
                  "Be concrete and concise. State deliverables, assumptions, risks, and dependencies. "
                  "Do not claim to have executed tools, changed files, or contacted people without evidence.")
        user = f"Company task: {state.title}\nRequest: {state.prompt}\nRequired capabilities: {', '.join(state.capabilities)}."
        if context: user += f"\n\nTeam context:\n{context[:9000]}"
        return system, user

    def _run_agent(self, agent: Agent, state: TaskState, context: str = "") -> tuple[str, int, str]:
        client = self._client_for(agent)
        if client.enabled:
            text, tokens = client.chat(*self._prompt(agent, state, context))
            return text, tokens, "nim"

        # Rich simulated deliverables for local/offline execution
        pt = state.prompt.lower()
        title = state.title
        if agent.id == "ceo":
            text = (f"### CEO Strategic Scope: {title}\n"
                    f"- **Outcome Goal**: Deliver high-reliability solution for '{state.prompt}'.\n"
                    f"- **Acceptance Criteria**: Functional execution, zero critical security flaws, independent test verification.\n"
                    f"- **Resource Allocation**: Delegating technical architecture to Full-Stack, implementation to Developer, QA to Testing, and final signoff to Review.")
            return text, 240, "simulated"

        elif agent.id == "fullstack":
            text = (f"### Full-Stack Architecture Blueprint: {title}\n"
                    f"- **System Layer**: Modular, component-driven client and backend contract.\n"
                    f"- **File Structure**: `index.html` (DOM/Semantics), `styles.css` (Design System & Theme), `app.js` (Interactivity & State).\n"
                    f"- **Data Flow**: Reactive events, local storage caching, strict input sanitization.\n"
                    f"- **Integration Boundary**: RESTful JSON endpoints with idempotent mutations.")
            return text, 290, "simulated"

        elif agent.id == "developer":
            if any(k in pt for k in ("web", "website", "html", "page", "landing", "frontend")):
                text = (f"### Developer Implementation: {title}\n"
                        f"Deploying production-ready website files to workspace/:\n\n"
                        f"### File: index.html\n"
                        f"```html\n"
                        f"<!DOCTYPE html>\n"
                        f"<html lang=\"en\">\n"
                        f"<head>\n"
                        f"  <meta charset=\"UTF-8\">\n"
                        f"  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
                        f"  <title>{title} — Built by IRIS</title>\n"
                        f"  <link rel=\"stylesheet\" href=\"styles.css\">\n"
                        f"  <link href=\"https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=Inter:wght@400;500;600&display=swap\" rel=\"stylesheet\">\n"
                        f"</head>\n"
                        f"<body>\n"
                        f"  <div class=\"app-wrap\">\n"
                        f"    <header class=\"hero\">\n"
                        f"      <div class=\"badge\">⚡ IRIS Squad Workspace</div>\n"
                        f"      <h1>{title}</h1>\n"
                        f"      <p class=\"lead\">{state.prompt}</p>\n"
                        f"    </header>\n"
                        f"    <main class=\"card-grid\">\n"
                        f"      <article class=\"panel\">\n"
                        f"        <h3>🚀 Enterprise Architecture</h3>\n"
                        f"        <p>Built with modular vanilla web technologies, optimized for performance and lightning fast load times.</p>\n"
                        f"      </article>\n"
                        f"      <article class=\"panel\">\n"
                        f"        <h3>🛡️ Firewall Verified</h3>\n"
                        f"        <p>Strict agent boundaries enforced across all 7 startup squad domains.</p>\n"
                        f"      </article>\n"
                        f"    </main>\n"
                        f"    <div class=\"interactive-box\">\n"
                        f"      <button id=\"demo-btn\" onclick=\"handleClick()\">Run Dynamic Action</button>\n"
                        f"      <div id=\"status-log\">Status: Ready for user interaction.</div>\n"
                        f"    </div>\n"
                        f"  </div>\n"
                        f"  <script src=\"app.js\"></script>\n"
                        f"</body>\n"
                        f"</html>\n"
                        f"```\n\n"
                        f"### File: styles.css\n"
                        f"```css\n"
                        f"* {{ box-sizing: border-box; margin: 0; padding: 0; }}\n"
                        f"body {{ background: #080d1a; color: #e2e8f0; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 24px; }}\n"
                        f".app-wrap {{ max-width: 860px; width: 100%; text-align: center; }}\n"
                        f".hero h1 {{ font-family: 'Outfit', sans-serif; font-size: 2.8rem; font-weight: 800; background: linear-gradient(135deg, #fff 0%, #38bdf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 12px 0; }}\n"
                        f".badge {{ display: inline-block; background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 5px 14px; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; }}\n"
                        f".lead {{ color: #94a3b8; font-size: 1.1rem; margin-bottom: 28px; line-height: 1.6; }}\n"
                        f".card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 28px; }}\n"
                        f".panel {{ background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(51, 65, 85, 0.8); border-radius: 12px; padding: 20px; text-align: left; }}\n"
                        f".panel h3 {{ font-family: 'Outfit', sans-serif; color: #f8fafc; margin-bottom: 8px; font-size: 1.15rem; }}\n"
                        f".panel p {{ color: #94a3b8; font-size: 0.9rem; line-height: 1.5; }}\n"
                        f".interactive-box {{ background: rgba(15, 23, 42, 0.6); border: 1px dashed #334155; border-radius: 12px; padding: 20px; }}\n"
                        f"button {{ background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%); color: #020c15; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 700; cursor: pointer; transition: transform 0.2s; }}\n"
                        f"button:hover {{ transform: scale(1.03); }}\n"
                        f"#status-log {{ margin-top: 12px; font-family: monospace; color: #38bdf8; font-size: 0.9rem; }}\n"
                        f"```\n\n"
                        f"### File: app.js\n"
                        f"```javascript\n"
                        f"function handleClick() {{\n"
                        f"  const log = document.getElementById('status-log');\n"
                        f"  log.innerHTML = '✨ <strong>Success:</strong> Interactive event triggered! Dynamic code execution active at ' + new Date().toLocaleTimeString();\n"
                        f"  log.style.color = '#34d399';\n"
                        f"}}\n"
                        f"console.log('IRIS Workspace Application Initialized.');\n"
                        f"```\n")
            elif any(k in pt for k in ("parser", "python", "script", "backend")):
                text = (f"### Developer Implementation: {title}\n"
                        f"Writing python solution to workspace/:\n\n"
                        f"### File: parser.py\n"
                        f"```python\n"
                        f"import sys\n"
                        f"from typing import Any, Dict\n\n"
                        f"class RobustParser:\n"
                        f"    \"\"\"{title} parser with defensive error handling.\"\"\"\n"
                        f"    def __init__(self, debug: bool = True):\n"
                        f"        self.debug = debug\n\n"
                        f"    def parse(self, raw_input: str) -> Dict[str, Any]:\n"
                        f"        if not raw_input or not isinstance(raw_input, str):\n"
                        f"            raise ValueError('Input must be a non-empty string')\n"
                        f"        tokens = [t.strip() for t in raw_input.split() if t.strip()]\n"
                        f"        return {{'status': 'ok', 'count': len(tokens), 'tokens': tokens}}\n\n"
                        f"if __name__ == '__main__':\n"
                        f"    p = RobustParser()\n"
                        f"    print(p.parse('{state.prompt}'))\n"
                        f"```\n")
            else:
                text = (f"### Developer Implementation: {title}\n"
                        f"Implemented core logic according to CEO plan and Architecture specifications. Code modularized with test fixtures.")
            return text, 480, "simulated"

        elif agent.id == "testing":
            text = (f"### QA Testing Strategy & Evidence: {title}\n"
                    f"- **Unit Test Coverage**: Boundary validation, null input checks, and type coercion.\n"
                    f"- **Edge Cases Checked**: Empty inputs, oversized payloads, concurrent invocations.\n"
                    f"- **Result**: All 6 test suites passed with 0 regressions.")
            return text, 210, "simulated"

        elif agent.id == "review":
            text = (f"### Independent Security & Delivery Review: {title}\n"
                    f"- **Code Quality**: PASSED. Clean modular separation, zero hardcoded secrets.\n"
                    f"- **Firewall Boundary Verification**: PASSED. Specialist roles operated strictly within their designated domains.\n"
                    f"- **Approval**: APPROVED for production delivery.")
            return text, 220, "simulated"

        elif agent.id == "resource":
            text = (f"### Resource & Dependency Assessment: {title}\n"
                    f"- **External Dependencies**: Zero heavy third-party bloat; vanilla HTML5/CSS/JS runtime.\n"
                    f"- **Budget & Latency**: Estimated execution cost well within limits.")
            return text, 190, "simulated"

        elif agent.id == "hr":
            text = (f"### HR & Team Allocation: {title}\n"
                    f"- **Workforce Deployment**: Squad operational with assigned roles and boundary enforcement.\n"
                    f"- **Compliance & Policy**: Working within organizational safety guidelines.")
            return text, 180, "simulated"

        return f"{agent.name} deliverable: {agent.mandate} Task focus: {state.title}.", 180, "simulated"


    def execute(self, state: TaskState, strategy: Strategy) -> RunResult:
        trace: list[dict] = []; outputs: list[tuple[str, str]] = []
        cost = 0.0; tokens = 0; messages = 0; started = time.perf_counter()
        leader = next((a for a in strategy.agents if a.id == "ceo"), strategy.agents[0]); plan = ""
        if leader.cost_per_turn <= state.budget:
            try:
                plan, used, source = self._run_agent(leader, state)
                outputs.append((leader.name, plan)); tokens += used; cost += leader.cost_per_turn
                trace.append({"event": "agent_completed", "phase": "plan", "agent": leader.id, "provider": source, "tokens": used, "detail": plan})
            except RuntimeError as error: trace.append({"event": "agent_failed", "phase": "plan", "agent": leader.id, "detail": str(error)})
        else: trace.append({"event": "budget_stop", "agent": leader.id, "detail": "budget cannot fund CEO planning"})

        workers = [a for a in strategy.agents if a.id not in (leader.id, "review")]; affordable = []; reserved = cost
        for agent in workers:
            if reserved + agent.cost_per_turn <= state.budget: affordable.append(agent); reserved += agent.cost_per_turn
        if affordable:
            messages += len(affordable)
            with ThreadPoolExecutor(max_workers=min(8, len(affordable))) as pool:
                futures = {pool.submit(self._run_agent, agent, state, plan): agent for agent in affordable}
                for future in as_completed(futures):
                    agent = futures[future]
                    try:
                        text, used, source = future.result(); outputs.append((agent.name, text)); tokens += used; cost += agent.cost_per_turn
                        trace.append({"event": "agent_completed", "phase": "parallel_delivery", "agent": agent.id, "provider": source, "tokens": used, "detail": text})
                    except RuntimeError as error: trace.append({"event": "agent_failed", "phase": "parallel_delivery", "agent": agent.id, "detail": str(error)})
        for agent in workers:
            if agent not in affordable: trace.append({"event": "budget_stop", "agent": agent.id, "detail": "remaining budget insufficient"})

        review = next((a for a in strategy.agents if a.id == "review"), None)
        if review and strategy.verification and cost + review.cost_per_turn <= state.budget:
            messages += 1; packet = "\n\n".join(f"{name}: {text}" for name, text in outputs)
            try:
                review_text, used, source = self._run_agent(review, state, packet)
                outputs.append((review.name, review_text)); tokens += used; cost += review.cost_per_turn
                trace.append({"event": "verification", "phase": "independent_review", "agent": review.id, "provider": source, "tokens": used, "detail": review_text})
            except RuntimeError as error: trace.append({"event": "agent_failed", "phase": "independent_review", "agent": review.id, "detail": str(error)})

        confidence = min(.99, .58 + .055 * len(outputs) + (.05 if review and any(n == review.name for n, _ in outputs) else 0))
        success = len(outputs) >= 2 and confidence >= .72; stopped = cost >= state.budget * .9 or any(e["event"] == "budget_stop" for e in trace)
        trace.append({"event": "stopping", "detail": "budget boundary reached" if stopped else "CEO plan, parallel specialists, and review completed"})
        output = "\n\n".join(f"## {name}\n{text}" for name, text in outputs)
        return RunResult(output, success, confidence, cost, int((time.perf_counter() - started) * 1000), tokens, messages, False, stopped, trace)
