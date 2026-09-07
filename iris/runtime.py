from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import Agent, RunResult, Strategy, TaskState


class NIMClient:
    """Dependency-free client for NVIDIA's OpenAI-compatible NIM endpoint."""
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY", "")
        self.base_url = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.model = os.getenv("NIM_MODEL", "meta/llama-3.3-70b-instruct")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and os.getenv("IRIS_RUNTIME", "nim").lower() != "simulated"

    def chat(self, system: str, user: str) -> tuple[str, int]:
        payload = json.dumps({"model": self.model, "temperature": 0.2, "max_tokens": 700,
                              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        request = Request(f"{self.base_url.rstrip('/')}/chat/completions", data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=75) as response:
                data = json.loads(response.read().decode())
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"NIM request failed: {error}") from error
        content = data["choices"][0]["message"].get("content", "").strip()
        return content or "No deliverable returned.", int(data.get("usage", {}).get("total_tokens", 0))


class AgentRuntime:
    """CEO plan → parallel specialist delivery → independent review."""
    def __init__(self): self.client = NIMClient()

    def _prompt(self, agent: Agent, state: TaskState, context: str = "") -> tuple[str, str]:
        system = (f"You are the {agent.name} in an enterprise startup operating system. {agent.mandate} "
                  "Be concrete and concise. State deliverables, assumptions, risks, and dependencies. "
                  "Do not claim to have executed tools, changed files, or contacted people without evidence.")
        user = f"Company task: {state.title}\nRequest: {state.prompt}\nRequired capabilities: {', '.join(state.capabilities)}."
        if context: user += f"\n\nTeam context:\n{context[:9000]}"
        return system, user

    def _run_agent(self, agent: Agent, state: TaskState, context: str = "") -> tuple[str, int, str]:
        if self.client.enabled:
            text, tokens = self.client.chat(*self._prompt(agent, state, context))
            return text, tokens, "nim"
        return f"{agent.name} deliverable: {agent.mandate} Task focus: {state.title}.", 180, "simulated"

    def execute(self, state: TaskState, strategy: Strategy) -> RunResult:
        trace: list[dict] = []; outputs: list[tuple[str, str]] = []
        cost = 0.0; tokens = 0; messages = 0; started = time.perf_counter()
        leader = next((a for a in strategy.agents if a.id == "ceo"), strategy.agents[0])
        plan = ""
        if leader.cost_per_turn <= state.budget:
            plan, used, source = self._run_agent(leader, state)
            outputs.append((leader.name, plan)); tokens += used; cost += leader.cost_per_turn
            trace.append({"event": "agent_completed", "phase": "plan", "agent": leader.id, "provider": source, "tokens": used, "detail": plan})
        else:
            trace.append({"event": "budget_stop", "agent": leader.id, "detail": "budget cannot fund CEO planning"})

        workers = [a for a in strategy.agents if a.id not in (leader.id, "review")]
        affordable = []
        reserved = cost
        for agent in workers:
            if reserved + agent.cost_per_turn <= state.budget:
                affordable.append(agent)
                reserved += agent.cost_per_turn
        if affordable:
            messages += len(affordable)
            with ThreadPoolExecutor(max_workers=min(8, len(affordable))) as pool:
                futures = {pool.submit(self._run_agent, agent, state, plan): agent for agent in affordable}
                for future in as_completed(futures):
                    agent = futures[future]
                    try:
                        text, used, source = future.result()
                        outputs.append((agent.name, text)); tokens += used; cost += agent.cost_per_turn
                        trace.append({"event": "agent_completed", "phase": "parallel_delivery", "agent": agent.id, "provider": source, "tokens": used, "detail": text})
                    except RuntimeError as error:
                        trace.append({"event": "agent_failed", "phase": "parallel_delivery", "agent": agent.id, "detail": str(error)})
        for agent in workers:
            if agent not in affordable: trace.append({"event": "budget_stop", "agent": agent.id, "detail": "remaining budget insufficient"})

        review = next((a for a in strategy.agents if a.id == "review"), None)
        if review and strategy.verification and cost + review.cost_per_turn <= state.budget:
            messages += 1
            packet = "\n\n".join(f"{name}: {text}" for name, text in outputs)
            review_text, used, source = self._run_agent(review, state, packet)
            outputs.append((review.name, review_text)); tokens += used; cost += review.cost_per_turn
            trace.append({"event": "verification", "phase": "independent_review", "agent": review.id, "provider": source, "tokens": used, "detail": review_text})

        confidence = min(.99, .58 + .055 * len(outputs) + (.05 if review and any(n == review.name for n, _ in outputs) else 0))
        success = len(outputs) >= 2 and confidence >= .72
        stopped = cost >= state.budget * .9 or any(e["event"] == "budget_stop" for e in trace)
        trace.append({"event": "stopping", "detail": "budget boundary reached" if stopped else "CEO plan, parallel specialists, and review completed"})
        output = "\n\n".join(f"## {name}\n{text}" for name, text in outputs)
        return RunResult(output, success, confidence, cost, int((time.perf_counter() - started) * 1000), tokens, messages, False, stopped, trace)
