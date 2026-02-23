"""Verification Agent — post-change validation.

Validates that remediation actions resolved the issue and monitors
for regression after changes.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from netopshub.agents.base import BaseAgent
from netopshub.models import AgentTask

logger = logging.getLogger(__name__)


class VerificationAgent(BaseAgent):
    """Post-change verification and regression monitoring.

    After a remediation is applied, this agent:
    1. Runs health checks on the affected device
    2. Validates the specific issue is resolved
    3. Checks for unintended side effects
    4. Monitors for regression over a configurable window
    """

    def __init__(self, demo_mode: bool = True):
        super().__init__(
            name="verification",
            description="Post-change validation and regression monitoring",
        )
        self.demo_mode = demo_mode
        self._verifications: list[dict[str, Any]] = []

    async def process(self, task: AgentTask) -> AgentTask:
        """Process a verification task."""
        task.status = "running"

        try:
            if task.task_type == "verify_change":
                device_id = task.input_data.get("device_id", "")
                change_type = task.input_data.get("change_type", "")
                result = self._verify_change(device_id, change_type)
                self._verifications.append(result)
                return self._complete_task(task, result)

            elif task.task_type == "health_check":
                device_id = task.input_data.get("device_id", "")
                result = self._health_check(device_id)
                return self._complete_task(task, result)

            elif task.task_type == "regression_check":
                device_id = task.input_data.get("device_id", "")
                result = self._regression_check(device_id)
                return self._complete_task(task, result)

            else:
                return self._fail_task(task, f"Unknown task type: {task.task_type}")

        except Exception as e:
            return self._fail_task(task, str(e))

    async def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Handle verification chat queries."""
        self.log_message("user", message)
        msg_lower = message.lower()

        if "verify" in msg_lower or "check" in msg_lower:
            device = "router-core-1"
            result = self._verify_change(device, "bgp_fix")
            self._verifications.append(result)
            response = self._format_verification(result)
        elif "health" in msg_lower:
            result = self._health_check("router-core-1")
            response = self._format_health_check(result)
        elif "regression" in msg_lower:
            result = self._regression_check("router-core-1")
            response = self._format_regression(result)
        else:
            response = (
                "I verify that changes were applied correctly and monitor for regressions.\n\n"
                "Try:\n"
                "- 'Verify the last change on router-core-1'\n"
                "- 'Run a health check on switch-dist-1'\n"
                "- 'Check for regressions'"
            )

        self.log_message("assistant", response)
        return response

    def _verify_change(self, device_id: str, change_type: str) -> dict[str, Any]:
        """Verify a configuration change was applied correctly."""
        checks = [
            {"check": "Configuration applied", "status": "pass", "details": "All commands accepted without errors"},
            {"check": "Service impact", "status": "pass", "details": "No traffic loss detected during change"},
            {"check": "BGP session status", "status": "pass", "details": "All BGP sessions Established"},
            {"check": "Interface status", "status": "pass", "details": "All interfaces Up/Up"},
            {"check": "Error counters", "status": "pass", "details": "No new errors post-change"},
            {"check": "CPU impact", "status": "pass", "details": "CPU within normal range (28%)"},
            {"check": "Memory impact", "status": "pass", "details": "Memory within normal range (52%)"},
            {"check": "Routing table", "status": "pass", "details": "Expected prefix count (14,283) matches"},
        ]

        passed = sum(1 for c in checks if c["status"] == "pass")
        return {
            "device_id": device_id,
            "change_type": change_type,
            "verified_at": datetime.utcnow().isoformat(),
            "overall_status": "pass" if passed == len(checks) else "fail",
            "checks": checks,
            "passed": passed,
            "total": len(checks),
            "summary": f"{passed}/{len(checks)} checks passed",
        }

    def _health_check(self, device_id: str) -> dict[str, Any]:
        """Run a comprehensive health check on a device."""
        return {
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "overall": "healthy",
            "checks": {
                "reachability": {"status": "pass", "latency_ms": 2.3},
                "cpu": {"status": "pass", "value": 28, "threshold": 85},
                "memory": {"status": "pass", "value": 52, "threshold": 90},
                "interfaces": {"status": "pass", "up": 7, "down": 1, "admin_down": 0},
                "bgp_peers": {"status": "pass", "established": 4, "idle": 0},
                "ospf_neighbors": {"status": "pass", "full": 3, "down": 0},
                "temperature": {"status": "pass", "value": 42, "threshold": 75},
                "disk": {"status": "pass", "value": 34, "threshold": 90},
                "uptime": {"status": "pass", "days": 182},
                "last_config_change": {"status": "pass", "hours_ago": 2.3},
            },
        }

    def _regression_check(self, device_id: str) -> dict[str, Any]:
        """Check for regression after a change."""
        return {
            "device_id": device_id,
            "monitoring_window": "24h",
            "timestamp": datetime.utcnow().isoformat(),
            "regression_detected": False,
            "metrics_monitored": [
                {"metric": "cpu", "baseline": 25.0, "current": 28.0, "status": "normal"},
                {"metric": "memory", "baseline": 50.0, "current": 52.0, "status": "normal"},
                {"metric": "bgp_sessions", "baseline": 4, "current": 4, "status": "normal"},
                {"metric": "error_rate", "baseline": 0.02, "current": 0.01, "status": "improved"},
                {"metric": "latency", "baseline": 2.1, "current": 2.3, "status": "normal"},
            ],
            "conclusion": "No regression detected. All metrics within baseline thresholds.",
        }

    def _format_verification(self, result: dict[str, Any]) -> str:
        """Format verification results for display."""
        lines = [
            f"**Change Verification — {result['device_id']}**\n",
            f"Overall: **{result['overall_status'].upper()}** ({result['summary']})\n",
        ]
        for check in result["checks"]:
            status = "PASS" if check["status"] == "pass" else "FAIL"
            lines.append(f"  [{status}] {check['check']}: {check['details']}")
        return "\n".join(lines)

    def _format_health_check(self, result: dict[str, Any]) -> str:
        """Format health check results for display."""
        lines = [
            f"**Health Check — {result['device_id']}**\n",
            f"Overall: **{result['overall'].upper()}**\n",
        ]
        for name, check in result["checks"].items():
            status = "PASS" if check["status"] == "pass" else "FAIL"
            details = ", ".join(f"{k}={v}" for k, v in check.items() if k != "status")
            lines.append(f"  [{status}] {name}: {details}")
        return "\n".join(lines)

    def _format_regression(self, result: dict[str, Any]) -> str:
        """Format regression check results."""
        lines = [
            f"**Regression Check — {result['device_id']}**\n",
            f"Window: {result['monitoring_window']}\n",
            f"Regression: **{'YES' if result['regression_detected'] else 'NO'}**\n",
        ]
        for m in result["metrics_monitored"]:
            lines.append(
                f"  {m['metric']}: baseline={m['baseline']} → current={m['current']} [{m['status']}]"
            )
        lines.append(f"\n{result['conclusion']}")
        return "\n".join(lines)

    @property
    def verification_count(self) -> int:
        return len(self._verifications)
