from __future__ import annotations

import re
from dataclasses import asdict
from .firewall import AgentFirewall, FirewallResult
from .models import RunResult, Strategy, TaskState
from .registry import AGENTS, matching
from .runtime import AgentRuntime
from .storage import Store
from .workspace import WorkspaceManager


class IrisController:
    def __init__(self, store: Store, workspace: WorkspaceManager | None = None):
        self.store = store
        self.runtime = AgentRuntime()
        self.workspace = workspace or WorkspaceManager()

    def analyze(self, title: str, prompt: str, budget: float, baseline: str) -> TaskState:
        text = f"{title} {prompt}".lower()
        mapping = {"coding": ("code", "bug", "test", "python", "implement", "app"), "research": ("research", "source", "document", "compare"), "data": ("data", "csv", "analysis", "chart"), "tools": ("api", "browser", "web", "file"), "people": ("hire", "hiring", "employee", "team", "hr"), "security": ("secure", "security", "privacy", "compliance")}
        capabilities = [kind for kind, words in mapping.items() if any(word in text for word in words)] or ["reasoning"]
        if "reasoning" not in capabilities: capabilities.insert(0, "reasoning")
        complexity = min(5, 1 + sum(text.count(word) for word in ("and", "multiple", "complex", "integrate", "verify")))
        risk = min(5, 1 + sum(word in text for word in ("secure", "financial", "medical", "production", "critical")))
        return TaskState(title, prompt, capabilities[1] if len(capabilities)>1 else "reasoning", complexity, risk, capabilities, budget, baseline)

    def plan(self, state: TaskState) -> Strategy:
        flags = {"B0": 0, "B1": 1, "B2": 2, "B3": 3, "B4": 4, "B5": 5, "B6": 6, "B7": 7, "B8": 8}
        level = flags.get(state.baseline, 8)
        by_id = {agent.id: agent for agent in AGENTS}
        team = [by_id["ceo"]]
        if level >= 1:
            for capability in state.capabilities:
                candidates = matching(capability)
                if candidates and candidates[0] not in team: team.append(candidates[0])
        if level >= 3:
            for role in ("resource", "fullstack", "developer", "testing", "review"):
                if by_id[role] not in team: team.append(by_id[role])
        if level == 0: team = team[:1]
        if level < 2: team = team[:min(2, len(team))]
        if level >= 6 and by_id["review"] not in team: team.append(by_id["review"])
        topology = "sequential" if level < 3 else ("parallel" if state.complexity <= 2 else "hierarchical")
        if state.complexity >= 5 and level >= 3: topology = "hybrid"
        experience = self.store.similar(state.capabilities) if level >= 7 else None
        if experience and experience["strategy"].get("topology") in ("sequential", "parallel", "hierarchical", "hybrid"):
            topology = experience["strategy"]["topology"]
        communication = "selective" if level >= 4 else "broadcast"
        verification = level >= 3 or state.risk >= 4
        score = sum(a.reliability for a in team) - sum(a.cost_per_turn for a in team) * 4 - len(team) * .05
        return Strategy(team, topology, communication, verification, experience["id"] if experience else None, score)

    def run(self, title: str, prompt: str, budget: float = .25, baseline: str = "B8") -> dict:
        state = self.analyze(title, prompt, budget, baseline)
        strategy = self.plan(state)
        result = self.runtime.execute(state, strategy)
        saved_files = self.workspace.extract_and_save_artifacts(result.output, prompt)
        public = {"output": result.output, "success": result.success, "confidence": round(result.confidence, 3),
                  "cost": round(result.cost, 4), "latency_ms": result.latency_ms, "tokens": result.tokens,
                  "messages": result.messages, "recovered": result.recovered, "stopped_early": result.stopped_early,
                  "trace": result.trace, "artifacts": saved_files}
        state_data = asdict(state); strategy_data = strategy.public()
        task_id = self.store.save_task(title, prompt, state_data, strategy_data, public)
        lesson = "Reuse topology and verifier for similar tasks" if result.success else "Increase verification or budget"
        self.store.save_experience(state.capabilities, strategy_data, result.confidence, lesson)
        return {"id": task_id, "state": state_data, "strategy": strategy_data, "result": public}

    def run_single_agent(self, agent_id: str, prompt: str) -> dict:
        """Executes a 1-on-1 prompt with a specific agent, enforcing the deterministic Agent Firewall."""
        agent_id = agent_id.lower().strip()
        by_id = {agent.id: agent for agent in AGENTS}
        if agent_id not in by_id:
            return {"error": f"Agent '{agent_id}' not found"}

        # 1. Deterministic Agent Firewall Check
        firewall_check = AgentFirewall.check(agent_id, prompt)
        if not firewall_check.allowed:
            return {
                "blocked": True,
                "agent_id": agent_id,
                "agent_name": by_id[agent_id].name,
                "violation": firewall_check.violation,
                "suggested_agent": firewall_check.suggested_agent,
                "suggested_name": firewall_check.suggested_name,
                "output": firewall_check.message,
                "artifacts": []
            }

        # 2. Allowed: Execute agent
        agent = by_id[agent_id]
        state = self.analyze(f"1-on-1: {agent.name}", prompt, budget=0.10, baseline="B0")
        output, tokens, provider = self.runtime._run_agent(agent, state)

        # 3. Extract any code artifacts to workspace
        artifacts = self.workspace.extract_and_save_artifacts(output, prompt)

        return {
            "blocked": False,
            "agent_id": agent_id,
            "agent_name": agent.name,
            "output": output,
            "tokens": tokens,
            "provider": provider,
            "cost": agent.cost_per_turn,
            "artifacts": artifacts
        }

