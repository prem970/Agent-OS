from .models import Agent


AGENTS = (
    Agent("ceo", "CEO Agent", ("reasoning", "planning", "strategy"), "NIM", ("roadmap",), .030, 760, .94, "Own the business outcome, prioritize scope, risks, and acceptance criteria."),
    Agent("hr", "HR Agent", ("people", "hiring", "policy"), "NIM", ("policy",), .012, 320, .88, "Define ownership, hiring, process, and people risks when relevant."),
    Agent("resource", "Resource Agent", ("research", "documents", "tools", "execution", "resources"), "NIM", ("research", "api"), .014, 380, .87, "Gather constraints, dependencies, references, and delivery resources."),
    Agent("fullstack", "Full-Stack Architect", ("coding", "architecture", "web"), "NIM", ("code", "git"), .032, 900, .92, "Design the end-to-end technical approach and integration boundaries."),
    Agent("developer", "Developer Agent", ("coding", "implementation"), "NIM", ("code", "git"), .035, 950, .91, "Implement a focused, production-ready solution with clear handoff notes."),
    Agent("testing", "Testing Agent", ("testing", "quality", "verification"), "NIM", ("tests",), .022, 610, .96, "Create test strategy, edge cases, and reproducible quality checks."),
    Agent("review", "Review Agent", ("review", "verification", "security"), "NIM", ("reasoning", "tests"), .024, 640, .97, "Independently review outputs, expose risks, and approve or reject delivery."),
)


def matching(capability: str) -> list[Agent]:
    return [agent for agent in AGENTS if capability in agent.capabilities]
