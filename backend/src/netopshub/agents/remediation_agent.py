"""Remediation Agent — config change proposals with HITL approval.

Generates configuration changes to fix identified issues, with
diff previews, rollback plans, and human-in-the-loop approval gates.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from netopshub.agents.base import BaseAgent
from netopshub.models import AgentTask, RemediationProposal

logger = logging.getLogger(__name__)


class RemediationAgent(BaseAgent):
    """Proposes configuration changes to remediate issues.

    All proposals require human approval before execution.
    Includes rollback plans for every change.
    """

    def __init__(self, demo_mode: bool = True):
        super().__init__(
            name="remediation",
            description="Configuration change proposals with HITL approval",
        )
        self.demo_mode = demo_mode
        self._proposals: list[RemediationProposal] = []

    async def process(self, task: AgentTask) -> AgentTask:
        """Process a remediation task."""
        task.status = "running"

        try:
            if task.task_type == "propose_fix":
                issue = task.input_data.get("issue", "")
                device_id = task.input_data.get("device_id", "")
                proposal = self._generate_proposal(issue, device_id)
                self._proposals.append(proposal)
                return self._complete_task(task, {
                    "proposal": proposal.model_dump(),
                    "status": "awaiting_approval",
                })

            elif task.task_type == "approve":
                proposal_id = task.input_data.get("proposal_id", "")
                approved_by = task.input_data.get("approved_by", "admin")
                result = self._approve_proposal(proposal_id, approved_by)
                return self._complete_task(task, result)

            elif task.task_type == "list_proposals":
                return self._complete_task(task, {
                    "proposals": [p.model_dump() for p in self._proposals],
                    "pending": sum(1 for p in self._proposals if not p.approved),
                })

            else:
                return self._fail_task(task, f"Unknown task type: {task.task_type}")

        except Exception as e:
            return self._fail_task(task, str(e))

    async def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Handle remediation chat queries."""
        self.log_message("user", message)
        msg_lower = message.lower()

        if "fix" in msg_lower and "bgp" in msg_lower:
            proposal = self._generate_proposal("bgp_flapping", "router-core-1")
            self._proposals.append(proposal)
            response = self._format_proposal(proposal)
        elif "fix" in msg_lower and ("compliance" in msg_lower or "security" in msg_lower):
            proposal = self._generate_proposal("compliance_failure", "switch-access-1")
            self._proposals.append(proposal)
            response = self._format_proposal(proposal)
        elif "rollback" in msg_lower:
            response = self._show_rollback()
        elif "pending" in msg_lower or "proposals" in msg_lower:
            pending = [p for p in self._proposals if not p.approved]
            if pending:
                response = f"**{len(pending)} Pending Proposals:**\n\n"
                for p in pending:
                    response += f"- [{p.risk_level.upper()}] {p.title} on {p.device_hostname}\n"
            else:
                response = "No pending remediation proposals."
        else:
            response = (
                "I generate configuration change proposals to fix network issues.\n\n"
                "All changes require human approval before execution.\n\n"
                "Try:\n"
                "- 'Fix BGP flapping on router-core-1'\n"
                "- 'Fix compliance failures'\n"
                "- 'Show pending proposals'\n"
                "- 'Show rollback plan'"
            )

        self.log_message("assistant", response)
        return response

    def _generate_proposal(self, issue: str, device_id: str) -> RemediationProposal:
        """Generate a remediation proposal for an issue."""
        proposals = {
            "bgp_flapping": RemediationProposal(
                device_id=device_id,
                device_hostname=device_id,
                title="Stabilize BGP session with dampening and BFD",
                description=(
                    "BGP flapping detected due to physical layer instability. "
                    "Applying BGP dampening to prevent route churn, and enabling BFD "
                    "for faster failure detection."
                ),
                config_commands=[
                    "router bgp 65001",
                    " address-family ipv4 unicast",
                    "  bgp dampening 15 750 2000 60",
                    " neighbor 10.0.0.2 bfd",
                    " neighbor 10.0.0.2 fall-over bfd",
                ],
                rollback_commands=[
                    "router bgp 65001",
                    " address-family ipv4 unicast",
                    "  no bgp dampening",
                    " no neighbor 10.0.0.2 bfd",
                    " no neighbor 10.0.0.2 fall-over bfd",
                ],
                risk_level="medium",
            ),
            "compliance_failure": RemediationProposal(
                device_id=device_id,
                device_hostname=device_id,
                title="Fix compliance failures on switch-access-1",
                description=(
                    "Multiple compliance failures detected: default SNMP community, "
                    "missing password encryption, missing console timeout, and missing "
                    "VTY access control."
                ),
                config_commands=[
                    "service password-encryption",
                    "no snmp-server community public",
                    "snmp-server community N3tOps$ecure RO",
                    "banner login ^C",
                    "*** AUTHORIZED ACCESS ONLY ***",
                    "^C",
                    "line con 0",
                    " exec-timeout 5 0",
                    "line vty 0 15",
                    " access-class ACL_VTY in",
                    " transport input ssh",
                    "aaa new-model",
                    "aaa authentication login default local",
                ],
                rollback_commands=[
                    "no service password-encryption",
                    "snmp-server community public RO",
                    "no snmp-server community N3tOps$ecure",
                    "no banner login",
                    "line con 0",
                    " no exec-timeout",
                    "line vty 0 15",
                    " no access-class ACL_VTY in",
                    " transport input ssh telnet",
                ],
                risk_level="low",
            ),
        }

        return proposals.get(issue, RemediationProposal(
            device_id=device_id,
            device_hostname=device_id,
            title=f"Remediation for {issue}",
            description=f"Auto-generated fix for {issue}",
            config_commands=["! No automated fix available"],
            rollback_commands=["! No rollback needed"],
            risk_level="low",
        ))

    def _approve_proposal(self, proposal_id: str, approved_by: str) -> dict[str, Any]:
        """Approve a remediation proposal."""
        for proposal in self._proposals:
            if proposal.id == proposal_id:
                proposal.approved = True
                proposal.approved_by = approved_by
                return {
                    "status": "approved",
                    "proposal_id": proposal_id,
                    "approved_by": approved_by,
                    "message": f"Proposal '{proposal.title}' approved by {approved_by}",
                }
        return {"status": "not_found", "message": f"Proposal {proposal_id} not found"}

    def _format_proposal(self, proposal: RemediationProposal) -> str:
        """Format a proposal for display."""
        commands = "\n".join(f"  {cmd}" for cmd in proposal.config_commands)
        rollback = "\n".join(f"  {cmd}" for cmd in proposal.rollback_commands)
        return (
            f"**Remediation Proposal** [{proposal.risk_level.upper()} RISK]\n\n"
            f"**Title:** {proposal.title}\n"
            f"**Device:** {proposal.device_hostname}\n"
            f"**Description:** {proposal.description}\n\n"
            f"**Proposed Changes:**\n```\n{commands}\n```\n\n"
            f"**Rollback Plan:**\n```\n{rollback}\n```\n\n"
            f"**Status:** Awaiting approval (ID: {proposal.id[:8]}...)\n"
            f"To approve: `netopshub remediate approve {proposal.id[:8]}`"
        )

    def _show_rollback(self) -> str:
        """Show rollback plans for executed proposals."""
        executed = [p for p in self._proposals if p.executed]
        if not executed:
            return "No executed changes to roll back."
        lines = ["**Available Rollbacks:**\n"]
        for p in executed:
            rollback = "\n".join(f"  {cmd}" for cmd in p.rollback_commands)
            lines.append(f"**{p.title}** on {p.device_hostname}:\n```\n{rollback}\n```\n")
        return "\n".join(lines)

    @property
    def proposal_count(self) -> int:
        return len(self._proposals)

    @property
    def pending_count(self) -> int:
        return sum(1 for p in self._proposals if not p.approved)
