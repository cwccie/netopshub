"""Compliance Agent — config compliance checking against NIST/CIS/PCI-DSS.

Evaluates device configurations against security frameworks and
custom baselines, generating compliance reports with remediation guidance.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from netopshub.agents.base import BaseAgent
from netopshub.models import (
    AgentTask,
    AlertSeverity,
    ComplianceResult,
    ComplianceRule,
    ComplianceStatus,
)

logger = logging.getLogger(__name__)


# Built-in compliance rules
BUILTIN_RULES: list[ComplianceRule] = [
    # NIST 800-53 controls
    ComplianceRule(
        name="SSH v2 Required",
        description="SSH version 2 must be configured (v1 is insecure)",
        framework="NIST-800-53",
        control_id="AC-17(2)",
        severity=AlertSeverity.CRITICAL,
        check_type="contains",
        pattern="ip ssh version 2",
        remediation="Configure: ip ssh version 2",
    ),
    ComplianceRule(
        name="Password Encryption",
        description="Service password-encryption must be enabled",
        framework="NIST-800-53",
        control_id="IA-5(1)",
        severity=AlertSeverity.CRITICAL,
        check_type="contains",
        pattern="service password-encryption",
        remediation="Configure: service password-encryption",
    ),
    ComplianceRule(
        name="Banner Required",
        description="Login banner must be configured for legal notice",
        framework="NIST-800-53",
        control_id="AC-8",
        severity=AlertSeverity.WARNING,
        check_type="regex",
        pattern=r"banner\s+(login|motd)\s+",
        remediation="Configure: banner login ^Authorized access only^",
    ),
    ComplianceRule(
        name="NTP Configured",
        description="NTP must be configured for accurate timestamps",
        framework="NIST-800-53",
        control_id="AU-8",
        severity=AlertSeverity.WARNING,
        check_type="regex",
        pattern=r"ntp server\s+\S+",
        remediation="Configure: ntp server <NTP_SERVER_IP>",
    ),
    ComplianceRule(
        name="Logging Configured",
        description="Remote syslog must be configured",
        framework="NIST-800-53",
        control_id="AU-6",
        severity=AlertSeverity.CRITICAL,
        check_type="regex",
        pattern=r"logging host\s+\S+",
        remediation="Configure: logging host <SYSLOG_SERVER_IP>",
    ),
    ComplianceRule(
        name="Console Timeout",
        description="Console line must have an exec-timeout",
        framework="CIS",
        control_id="CIS-1.1.7",
        severity=AlertSeverity.WARNING,
        check_type="regex",
        pattern=r"line con.*\n.*exec-timeout\s+\d+",
        remediation="Configure under line con 0: exec-timeout 5 0",
    ),
    ComplianceRule(
        name="VTY Access Control",
        description="VTY lines must have access-class configured",
        framework="CIS",
        control_id="CIS-1.2.2",
        severity=AlertSeverity.CRITICAL,
        check_type="regex",
        pattern=r"line vty.*\n.*access-class\s+\S+",
        remediation="Configure under line vty 0 15: access-class ACL_VTY in",
    ),
    ComplianceRule(
        name="SNMP Community Not Default",
        description="Default SNMP communities (public/private) must not be used",
        framework="CIS",
        control_id="CIS-2.1.1",
        severity=AlertSeverity.CRITICAL,
        check_type="not_contains",
        pattern="snmp-server community public",
        remediation="Remove: no snmp-server community public",
    ),
    ComplianceRule(
        name="Unused Interfaces Shutdown",
        description="Unused interfaces should be administratively shut down",
        framework="PCI-DSS",
        control_id="PCI-1.1.6",
        severity=AlertSeverity.WARNING,
        check_type="regex",
        pattern=r"interface.*\n\s+shutdown",
        remediation="Shut down unused interfaces: shutdown",
    ),
    ComplianceRule(
        name="AAA Authentication",
        description="AAA authentication must be configured",
        framework="NIST-800-53",
        control_id="IA-2",
        severity=AlertSeverity.CRITICAL,
        check_type="contains",
        pattern="aaa authentication login",
        remediation="Configure: aaa new-model; aaa authentication login default local",
    ),
]


# Demo device configurations
DEMO_CONFIGS = {
    "router-core-1": """
hostname router-core-1
!
service password-encryption
ip ssh version 2
!
aaa new-model
aaa authentication login default local
!
ntp server 10.0.0.100
logging host 10.0.0.200
!
snmp-server community NetOps$ecure RO
!
banner login ^C
*** AUTHORIZED ACCESS ONLY ***
^C
!
line con 0
 exec-timeout 5 0
line vty 0 15
 access-class ACL_VTY in
 transport input ssh
""",
    "switch-access-1": """
hostname switch-access-1
!
ip ssh version 2
!
snmp-server community public RO
!
ntp server 10.0.0.100
!
line con 0
 no exec-timeout
line vty 0 15
 transport input ssh telnet
""",
    "firewall-edge-1": """
hostname firewall-edge-1
!
service password-encryption
ip ssh version 2
!
aaa authentication login default local
!
ntp server 10.0.0.100
ntp server 10.0.0.101
logging host 10.0.0.200
logging host 10.0.0.201
!
snmp-server community FW$nmp! RO
!
banner login ^C
*** AUTHORIZED ACCESS ONLY - ALL ACTIVITY MONITORED ***
^C
!
line con 0
 exec-timeout 3 0
line vty 0 4
 access-class ACL_MGMT in
 transport input ssh
""",
}


class ComplianceAgent(BaseAgent):
    """Checks device configurations against compliance frameworks.

    Supports NIST 800-53, CIS Benchmarks, PCI-DSS, and custom baselines.
    """

    def __init__(self, demo_mode: bool = True):
        super().__init__(
            name="compliance",
            description="Configuration compliance auditing",
        )
        self.demo_mode = demo_mode
        self._rules = list(BUILTIN_RULES)
        self._results: dict[str, list[ComplianceResult]] = {}

    async def process(self, task: AgentTask) -> AgentTask:
        """Process a compliance task."""
        task.status = "running"

        try:
            if task.task_type == "audit":
                device_id = task.input_data.get("device_id", "")
                framework = task.input_data.get("framework")
                config = task.input_data.get("config", "")
                if not config and self.demo_mode:
                    config = DEMO_CONFIGS.get(device_id, "")
                results = self.check_compliance(device_id, config, framework)
                return self._complete_task(task, {
                    "device_id": device_id,
                    "results": [r.model_dump() for r in results],
                    "compliant": sum(1 for r in results if r.status == ComplianceStatus.COMPLIANT),
                    "non_compliant": sum(1 for r in results if r.status == ComplianceStatus.NON_COMPLIANT),
                    "total": len(results),
                })

            elif task.task_type == "audit_all":
                framework = task.input_data.get("framework")
                all_results = self._audit_all(framework)
                return self._complete_task(task, all_results)

            else:
                return self._fail_task(task, f"Unknown task type: {task.task_type}")

        except Exception as e:
            return self._fail_task(task, str(e))

    async def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Handle compliance chat queries."""
        self.log_message("user", message)
        msg_lower = message.lower()

        if "audit" in msg_lower or "check" in msg_lower or "compliance" in msg_lower:
            results_summary = self._audit_all()
            response = self._format_audit_summary(results_summary)
        elif "nist" in msg_lower:
            results_summary = self._audit_all(framework="NIST-800-53")
            response = self._format_audit_summary(results_summary, "NIST-800-53")
        elif "cis" in msg_lower:
            results_summary = self._audit_all(framework="CIS")
            response = self._format_audit_summary(results_summary, "CIS")
        elif "pci" in msg_lower:
            results_summary = self._audit_all(framework="PCI-DSS")
            response = self._format_audit_summary(results_summary, "PCI-DSS")
        else:
            response = (
                "I can audit device configurations against security frameworks.\n\n"
                "Try:\n"
                "- 'Run a compliance audit'\n"
                "- 'Check NIST 800-53 compliance'\n"
                "- 'Audit against CIS benchmarks'\n"
                "- 'Check PCI-DSS compliance'"
            )

        self.log_message("assistant", response)
        return response

    def check_compliance(
        self,
        device_id: str,
        config: str,
        framework: Optional[str] = None,
    ) -> list[ComplianceResult]:
        """Check a device config against compliance rules."""
        rules = self._rules
        if framework:
            rules = [r for r in rules if r.framework == framework]

        results: list[ComplianceResult] = []
        for rule in rules:
            status = self._evaluate_rule(rule, config)
            results.append(ComplianceResult(
                rule_id=rule.id,
                device_id=device_id,
                device_hostname=device_id,
                status=status,
                framework=rule.framework,
                control_id=rule.control_id,
                details=f"{rule.name}: {'PASS' if status == ComplianceStatus.COMPLIANT else 'FAIL'}",
                evidence=rule.remediation if status == ComplianceStatus.NON_COMPLIANT else "",
            ))

        self._results[device_id] = results
        return results

    def _evaluate_rule(self, rule: ComplianceRule, config: str) -> ComplianceStatus:
        """Evaluate a single rule against a configuration."""
        if not config:
            return ComplianceStatus.NOT_ASSESSED

        if rule.check_type == "contains":
            return (
                ComplianceStatus.COMPLIANT
                if rule.pattern in config
                else ComplianceStatus.NON_COMPLIANT
            )
        elif rule.check_type == "not_contains":
            return (
                ComplianceStatus.COMPLIANT
                if rule.pattern not in config
                else ComplianceStatus.NON_COMPLIANT
            )
        elif rule.check_type == "regex":
            return (
                ComplianceStatus.COMPLIANT
                if re.search(rule.pattern, config, re.MULTILINE | re.IGNORECASE)
                else ComplianceStatus.NON_COMPLIANT
            )
        return ComplianceStatus.NOT_ASSESSED

    def _audit_all(self, framework: Optional[str] = None) -> dict[str, Any]:
        """Audit all demo devices."""
        all_results: dict[str, Any] = {"devices": {}, "summary": {}}
        total_compliant = 0
        total_non_compliant = 0
        total_checks = 0

        for device_id, config in DEMO_CONFIGS.items():
            results = self.check_compliance(device_id, config, framework)
            compliant = sum(1 for r in results if r.status == ComplianceStatus.COMPLIANT)
            non_compliant = sum(1 for r in results if r.status == ComplianceStatus.NON_COMPLIANT)
            all_results["devices"][device_id] = {
                "compliant": compliant,
                "non_compliant": non_compliant,
                "total": len(results),
                "score": round((compliant / len(results)) * 100, 1) if results else 0,
                "failures": [
                    {"rule": r.details, "remediation": r.evidence}
                    for r in results
                    if r.status == ComplianceStatus.NON_COMPLIANT
                ],
            }
            total_compliant += compliant
            total_non_compliant += non_compliant
            total_checks += len(results)

        all_results["summary"] = {
            "total_checks": total_checks,
            "compliant": total_compliant,
            "non_compliant": total_non_compliant,
            "overall_score": round((total_compliant / total_checks) * 100, 1) if total_checks else 0,
        }
        return all_results

    def _format_audit_summary(self, results: dict[str, Any], framework: str = "All Frameworks") -> str:
        """Format audit results for chat display."""
        summary = results.get("summary", {})
        lines = [
            f"**Compliance Audit Results — {framework}**\n",
            f"Overall Score: **{summary.get('overall_score', 0)}%**",
            f"Total Checks: {summary.get('total_checks', 0)}",
            f"Passed: {summary.get('compliant', 0)} | Failed: {summary.get('non_compliant', 0)}\n",
        ]

        for device_id, device_data in results.get("devices", {}).items():
            score = device_data.get("score", 0)
            status_icon = "PASS" if score >= 80 else "WARN" if score >= 60 else "FAIL"
            lines.append(f"**{device_id}**: {score}% [{status_icon}]")
            for failure in device_data.get("failures", [])[:3]:
                lines.append(f"  - {failure['rule']}")
                if failure['remediation']:
                    lines.append(f"    Fix: {failure['remediation']}")

        return "\n".join(lines)

    def add_rule(self, rule: ComplianceRule) -> None:
        """Add a custom compliance rule."""
        self._rules.append(rule)

    @property
    def rule_count(self) -> int:
        return len(self._rules)
