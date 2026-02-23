"""Agent Coordinator — LangGraph-style agent orchestration.

Routes tasks to specialized agents, manages conversation state,
and orchestrates multi-agent workflows.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from netopshub.agents.base import BaseAgent
from netopshub.agents.compliance_agent import ComplianceAgent
from netopshub.agents.diagnosis_agent import DiagnosisAgent
from netopshub.agents.discovery_agent import DiscoveryAgent
from netopshub.agents.forecast_agent import ForecastAgent
from netopshub.agents.knowledge_agent import KnowledgeAgent
from netopshub.agents.remediation_agent import RemediationAgent
from netopshub.agents.verification_agent import VerificationAgent
from netopshub.models import AgentMessage, AgentTask

logger = logging.getLogger(__name__)


# Routing patterns — maps user intent to agent
ROUTING_PATTERNS = [
    (r"discover|scan|topology|neighbor|lldp|cdp", "discovery"),
    (r"why|diagnos|root.?cause|rca|anomal|flap|down|error|fail", "diagnosis"),
    (r"what.*(mean|is)|document|vendor|knowledge|explain|how.*(work|config)", "knowledge"),
    (r"complian|audit|nist|cis|pci|security.*(check|scan)|baseline", "compliance"),
    (r"predict|forecast|capacity|trend|when.*will|exhaustion|growth", "forecast"),
    (r"fix|remedia|change|config|propose|rollback|patch", "remediation"),
    (r"verif|check|regression|health|post.?change|validate", "verification"),
]


class AgentCoordinator(BaseAgent):
    """Orchestrates the multi-agent system.

    Routes user messages and tasks to the appropriate specialized agent,
    manages conversation context, and can chain multiple agents for
    complex workflows (e.g., diagnose → remediate → verify).
    """

    def __init__(self, demo_mode: bool = True):
        super().__init__(
            name="coordinator",
            description="Multi-agent orchestration and routing",
        )
        self.demo_mode = demo_mode
        self.agents: dict[str, BaseAgent] = {
            "discovery": DiscoveryAgent(demo_mode=demo_mode),
            "knowledge": KnowledgeAgent(demo_mode=demo_mode),
            "diagnosis": DiagnosisAgent(demo_mode=demo_mode),
            "compliance": ComplianceAgent(demo_mode=demo_mode),
            "forecast": ForecastAgent(demo_mode=demo_mode),
            "remediation": RemediationAgent(demo_mode=demo_mode),
            "verification": VerificationAgent(demo_mode=demo_mode),
        }
        self._conversation: list[AgentMessage] = []

    async def process(self, task: AgentTask) -> AgentTask:
        """Route a task to the appropriate agent."""
        task.status = "running"
        agent_name = task.input_data.get("target_agent", task.agent_name)

        agent = self.agents.get(agent_name)
        if not agent:
            return self._fail_task(task, f"Unknown agent: {agent_name}")

        return await agent.process(task)

    async def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Route a chat message to the appropriate agent."""
        self.log_message("user", message)

        # Store in conversation
        self._conversation.append(AgentMessage(
            role="user",
            content=message,
            agent_name="coordinator",
        ))

        # Route to the best agent
        agent_name = self._route_message(message)
        agent = self.agents.get(agent_name)

        if agent:
            logger.info(f"Routing to {agent_name} agent: {message[:50]}...")
            response = await agent.chat(message, context)
            prefix = f"*[{agent_name.title()} Agent]*\n\n"
        else:
            response = self._default_response()
            prefix = ""

        full_response = prefix + response

        self._conversation.append(AgentMessage(
            role="assistant",
            content=full_response,
            agent_name=agent_name or "coordinator",
        ))

        self.log_message("assistant", full_response)
        return full_response

    async def run_workflow(
        self,
        workflow: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a multi-agent workflow.

        Supported workflows:
        - "diagnose_and_fix": Diagnose → Remediate → Verify
        - "full_audit": Discover → Compliance → Remediate
        - "health_check": Monitor → Diagnose → Forecast
        """
        results: dict[str, Any] = {"workflow": workflow, "steps": []}

        if workflow == "diagnose_and_fix":
            # Step 1: Diagnose
            diag_task = AgentTask(
                agent_name="diagnosis",
                task_type="diagnose",
                description="Diagnose the issue",
                input_data=input_data,
            )
            diag_result = await self.agents["diagnosis"].process(diag_task)
            results["steps"].append({"agent": "diagnosis", "result": diag_result.output_data})

            # Step 2: Remediate
            fix_task = AgentTask(
                agent_name="remediation",
                task_type="propose_fix",
                description="Propose a fix",
                input_data={
                    "issue": input_data.get("issue", "generic"),
                    "device_id": input_data.get("device_id", ""),
                },
            )
            fix_result = await self.agents["remediation"].process(fix_task)
            results["steps"].append({"agent": "remediation", "result": fix_result.output_data})

            # Step 3: Verify
            verify_task = AgentTask(
                agent_name="verification",
                task_type="verify_change",
                description="Verify the fix",
                input_data={
                    "device_id": input_data.get("device_id", ""),
                    "change_type": input_data.get("issue", ""),
                },
            )
            verify_result = await self.agents["verification"].process(verify_task)
            results["steps"].append({"agent": "verification", "result": verify_result.output_data})

        elif workflow == "full_audit":
            # Step 1: Discover
            disc_task = AgentTask(
                agent_name="discovery",
                task_type="scan_subnet",
                description="Discover devices",
                input_data={"subnet": input_data.get("subnet", "10.0.0.0/24")},
            )
            disc_result = await self.agents["discovery"].process(disc_task)
            results["steps"].append({"agent": "discovery", "result": disc_result.output_data})

            # Step 2: Compliance audit
            audit_task = AgentTask(
                agent_name="compliance",
                task_type="audit_all",
                description="Run compliance audit",
                input_data={"framework": input_data.get("framework")},
            )
            audit_result = await self.agents["compliance"].process(audit_task)
            results["steps"].append({"agent": "compliance", "result": audit_result.output_data})

        results["status"] = "completed"
        return results

    def _route_message(self, message: str) -> Optional[str]:
        """Route a message to the best agent based on intent."""
        msg_lower = message.lower()
        best_match: Optional[str] = None
        best_score = 0

        for pattern, agent_name in ROUTING_PATTERNS:
            matches = re.findall(pattern, msg_lower)
            if matches and len(matches) > best_score:
                best_score = len(matches)
                best_match = agent_name

        return best_match

    def _default_response(self) -> str:
        """Default response when no agent matches."""
        return (
            "I'm NetOpsHub's AI assistant. I can help with:\n\n"
            "**Discovery** — 'Discover devices on 10.0.0.0/24'\n"
            "**Diagnosis** — 'Why is BGP flapping on router-core-1?'\n"
            "**Knowledge** — 'What causes OSPF adjacency failures?'\n"
            "**Compliance** — 'Run a NIST 800-53 compliance audit'\n"
            "**Forecasting** — 'When will WAN bandwidth run out?'\n"
            "**Remediation** — 'Fix the compliance failures'\n"
            "**Verification** — 'Verify the last change was successful'\n\n"
            "What would you like to investigate?"
        )

    def get_conversation(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get conversation history."""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "agent": msg.agent_name,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in self._conversation[-limit:]
        ]

    def get_agent_status(self) -> dict[str, Any]:
        """Get status of all agents."""
        return {
            name: {
                "name": agent.name,
                "description": agent.description,
                "tasks_completed": len(agent.get_task_history()),
                "messages": len(agent.get_history()),
            }
            for name, agent in self.agents.items()
        }
