from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class FirewallResult:
    allowed: bool
    agent_id: str
    violation: Optional[str] = None
    suggested_agent: Optional[str] = None
    suggested_name: Optional[str] = None
    message: Optional[str] = None


class AgentFirewall:
    """Deterministic domain boundary enforcement for IRIS Startup Agents."""

    RULES = {
        "hr": {
            "name": "HR Agent",
            "mandate": "People operations, hiring, organizational policy, employee relations, and team culture.",
            "forbidden_patterns": [
                (r"\b(code|coding|develop|build|program|script|implement|frontend|backend|fullstack|website|web\s*app|html|css|javascript|python|api|database|sql|docker|git|bug|fix\s*bug|patch)\b",
                 "Software engineering & website/code implementation is strictly forbidden for the HR Agent.",
                 "developer", "Developer Agent"),
                (r"\b(architecture|system\s*design|microservices|infrastructure|kubernetes|aws|cloud)\b",
                 "System architecture and infrastructure design is strictly outside HR scope.",
                 "fullstack", "Full-Stack Architect"),
                (r"\b(test\s*plan|qa|test\s*cases|unit\s*test|integration\s*test|load\s*test)\b",
                 "Quality assurance and test verification cannot be performed by the HR Agent.",
                 "testing", "Testing Agent"),
                (r"\b(audit|security\s*review|vulnerability|penetration\s*test|code\s*review)\b",
                 "Security audits and code reviews require an independent security review agent.",
                 "review", "Review Agent"),
            ]
        },
        "developer": {
            "name": "Developer Agent",
            "mandate": "Software development, code implementation, bug fixes, scripts, and technical handoffs.",
            "forbidden_patterns": [
                (r"\b(hire|hiring|fire|firing|interview|salary|compensation|employee|workplace\s*policy|hr\s*policy|benefits)\b",
                 "HR policy, hiring, and personnel decisions are strictly forbidden for the Developer Agent.",
                 "hr", "HR Agent"),
                (r"\b(approve\s*budget|fundraise|pitch\s*deck|business\s*model|investor|p&l)\b",
                 "Executive business decisions and budget approvals belong solely to the CEO.",
                 "ceo", "CEO Agent"),
                (r"\b(final\s*signoff|approve\s*audit|security\s*certification|compliance\s*audit)\b",
                 "Developers cannot independently certify or sign off their own security audits.",
                 "review", "Review Agent"),
            ]
        },
        "fullstack": {
            "name": "Full-Stack Architect",
            "mandate": "System architecture, API specifications, technical integration, and system design.",
            "forbidden_patterns": [
                (r"\b(hire|hiring|fire|firing|employee\s*dispute|payroll|hr\s*policy)\b",
                 "Human resources and personnel matters are outside technical architecture.",
                 "hr", "HR Agent"),
                (r"\b(fundraising|pitch\s*deck|valuation|board\s*meeting|investor)\b",
                 "Corporate fundraising and executive governance are restricted to the CEO.",
                 "ceo", "CEO Agent"),
            ]
        },
        "testing": {
            "name": "Testing Agent",
            "mandate": "Test plans, quality assurance, automated test suites, edge case verification, and QA evidence.",
            "forbidden_patterns": [
                (r"\b(hire|hiring|fire|hr\s*policy|payroll)\b",
                 "Human resources operations are strictly forbidden for the Testing Agent.",
                 "hr", "HR Agent"),
                (r"\b(system\s*architecture|cloud\s*architecture|microservices\s*design)\b",
                 "High-level system architecture must be designed by the Full-Stack Architect.",
                 "fullstack", "Full-Stack Architect"),
            ]
        },
        "review": {
            "name": "Review Agent",
            "mandate": "Independent quality review, security auditing, risk assessment, and delivery sign-off.",
            "forbidden_patterns": [
                (r"\b(write\s*the\s*entire\s*app|implement\s*from\s*scratch|build\s*me\s*a\s*website)\b",
                 "The Review Agent is an independent auditor and cannot be the primary builder of implementations.",
                 "developer", "Developer Agent"),
                (r"\b(hire|hiring|fire|employee\s*policy)\b",
                 "HR operations are outside the review audit mandate.",
                 "hr", "HR Agent"),
            ]
        },
        "resource": {
            "name": "Resource Agent",
            "mandate": "Gathering dependencies, research documents, API references, vendor benchmarks, and resource planning.",
            "forbidden_patterns": [
                (r"\b(write\s*production\s*code|implement\s*backend|implement\s*frontend)\b",
                 "Production implementation must be delegated to the Developer Agent.",
                 "developer", "Developer Agent"),
                (r"\b(hire|firing|hr\s*dispute)\b",
                 "Personnel operations are managed by HR.",
                 "hr", "HR Agent"),
            ]
        },
        "ceo": {
            "name": "CEO Agent",
            "mandate": "Executive strategy, product roadmap, scope prioritization, risk ownership, and acceptance criteria.",
            "forbidden_patterns": [
                (r"\b(write\s*raw\s*code|write\s*python\s*script|debug\s*syntax\s*error)\b",
                 "The CEO Agent sets high-level strategy and scope, leaving detailed code execution to the Developer Agent.",
                 "developer", "Developer Agent"),
            ]
        }
    }

    @classmethod
    def check(cls, agent_id: str, prompt: str) -> FirewallResult:
        agent_id = agent_id.lower().strip()
        rule = cls.RULES.get(agent_id)
        if not rule:
            return FirewallResult(allowed=True, agent_id=agent_id)

        prompt_lower = prompt.lower()
        for pattern, violation_desc, suggested_agent, suggested_name in rule["forbidden_patterns"]:
            if re.search(pattern, prompt_lower):
                message = (
                    f"🛡️ [FIREWALL BLOCKED] Boundary Violation Detected!\n\n"
                    f"Agent: {rule['name']}\n"
                    f"Mandate: {rule['mandate']}\n\n"
                    f"Violation: {violation_desc}\n\n"
                    f"Action Required: You asked {rule['name']} to perform work outside its scope. Please switch or direct this request to the {suggested_name} ({suggested_agent})."
                )
                return FirewallResult(
                    allowed=False,
                    agent_id=agent_id,
                    violation=violation_desc,
                    suggested_agent=suggested_agent,
                    suggested_name=suggested_name,
                    message=message
                )

        return FirewallResult(allowed=True, agent_id=agent_id)
