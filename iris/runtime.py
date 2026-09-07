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
