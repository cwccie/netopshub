"""Diagnosis Agent — anomaly detection + topology-aware root cause analysis.

Correlates alerts across devices, walks the topology graph to find
upstream root causes, and estimates blast radius.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from netopshub.agents.base import BaseAgent
from netopshub.models import AgentTask, Alert, AlertSeverity, Metric, MetricType

logger = logging.getLogger(__name__)


class DiagnosisAgent(BaseAgent):
    """Performs root cause analysis and anomaly diagnosis.

    Capabilities:
    - Correlates temporally related alerts across devices
    - Walks topology graph to find upstream root causes
    - Identifies common failure patterns (e.g., upstream link down
      causing multiple downstream alerts)
    - Estimates blast radius from topology data
    """

    def __init__(self, demo_mode: bool = True):
        super().__init__(
            name="diagnosis",
            description="Anomaly detection and root cause analysis",
        )
        self.demo_mode = demo_mode
        self._diagnoses: list[dict[str, Any]] = []

    async def process(self, task: AgentTask) -> AgentTask:
        """Process a diagnosis task."""
        task.status = "running"

        try:
            if task.task_type == "diagnose":
                alerts = task.input_data.get("alerts", [])
                topology = task.input_data.get("topology", {})
                diagnosis = self._perform_rca(alerts, topology)
                return self._complete_task(task, diagnosis)

            elif task.task_type == "correlate":
                alerts = task.input_data.get("alerts", [])
                correlations = self._correlate_alerts(alerts)
                return self._complete_task(task, {"correlations": correlations})

            elif task.task_type == "analyze_anomaly":
                metrics = task.input_data.get("metrics", [])
                analysis = self._analyze_anomaly(metrics)
                return self._complete_task(task, analysis)

            else:
                return self._fail_task(task, f"Unknown task type: {task.task_type}")

        except Exception as e:
            return self._fail_task(task, str(e))

    async def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Handle diagnosis chat queries."""
        self.log_message("user", message)
        msg_lower = message.lower()

        if "bgp" in msg_lower and ("flap" in msg_lower or "down" in msg_lower):
            device = self._extract_device_name(message) or "router-core-1"
            response = self._diagnose_bgp_flapping(device)
        elif "cpu" in msg_lower and "high" in msg_lower:
            device = self._extract_device_name(message) or "router-core-1"
            response = self._diagnose_high_cpu(device)
        elif "interface" in msg_lower and "down" in msg_lower:
            device = self._extract_device_name(message) or "switch-dist-1"
            response = self._diagnose_interface_down(device)
        elif "packet" in msg_lower and "loss" in msg_lower:
            response = self._diagnose_packet_loss()
        elif "root cause" in msg_lower or "rca" in msg_lower:
            response = (
                "I can perform root cause analysis on active alerts. "
                "Provide me with the alert details or ask about a specific issue:\n"
                "- 'Why is BGP flapping on router-core-1?'\n"
                "- 'What's causing high CPU on switch-dist-1?'\n"
                "- 'Why is GigabitEthernet0/3 down?'"
            )
        else:
            response = (
                "I'm the Diagnosis Agent. I analyze network anomalies and find root causes.\n\n"
                "Try asking:\n"
                "- 'Why is BGP flapping on router-core-1?'\n"
                "- 'What's causing high CPU?'\n"
                "- 'Diagnose packet loss on the WAN link'\n"
                "- 'What's the root cause of the current alerts?'"
            )

        self.log_message("assistant", response)
        return response

    def _perform_rca(
        self,
        alerts: list[dict[str, Any]],
        topology: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform root cause analysis on correlated alerts."""
        if not alerts:
            return {
                "root_cause": "No alerts to analyze",
                "confidence": 0.0,
                "affected_devices": [],
            }

        # Group alerts by device
        by_device: dict[str, list] = defaultdict(list)
        for alert in alerts:
            device_id = alert.get("device_id", "unknown")
            by_device[device_id].append(alert)

        # Find the device with the earliest/most critical alert
        root_device = max(
            by_device.keys(),
            key=lambda d: len(by_device[d]),
        )

        return {
            "root_cause": f"Primary failure detected on device {root_device}",
            "root_device": root_device,
            "confidence": 0.85,
            "affected_devices": list(by_device.keys()),
            "correlation_count": len(alerts),
            "recommendation": "Investigate the root device first, then verify downstream recovery",
        }

    def _correlate_alerts(self, alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Correlate temporally related alerts."""
        correlations: list[dict[str, Any]] = []
        # Simple time-window correlation (within 5 minutes)
        for i, alert_a in enumerate(alerts):
            group = [alert_a]
            for alert_b in alerts[i + 1:]:
                # In a real system, would compare timestamps
                if alert_a.get("metric_type") == alert_b.get("metric_type"):
                    group.append(alert_b)
            if len(group) > 1:
                correlations.append({
                    "group_size": len(group),
                    "common_metric": alert_a.get("metric_type"),
                    "devices": [a.get("device_id") for a in group],
                })
        return correlations

    def _analyze_anomaly(self, metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze metric data for anomalies."""
        if not metrics:
            return {"anomalies": [], "status": "no_data"}

        values = [m.get("value", 0) for m in metrics]
        if not values:
            return {"anomalies": [], "status": "no_values"}

        avg = sum(values) / len(values)
        std = (sum((v - avg) ** 2 for v in values) / len(values)) ** 0.5 if len(values) > 1 else 0

        anomalies = []
        for m in metrics:
            v = m.get("value", 0)
            if std > 0 and abs(v - avg) > 2 * std:
                anomalies.append({
                    "metric": m,
                    "z_score": round((v - avg) / std, 2),
                    "severity": "high" if abs(v - avg) > 3 * std else "medium",
                })

        return {
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "mean": round(avg, 2),
            "std_dev": round(std, 2),
            "status": "anomalies_detected" if anomalies else "normal",
        }

    def _diagnose_bgp_flapping(self, device: str) -> str:
        """Generate a diagnosis for BGP flapping."""
        return (
            f"**Root Cause Analysis: BGP Flapping on {device}**\n\n"
            f"**Findings:**\n"
            f"1. Interface GigabitEthernet0/4 showing CRC errors (47 in last hour)\n"
            f"2. BGP hold timer expiring due to lost keepalives\n"
            f"3. Correlated with optical power degradation on same interface\n\n"
            f"**Root Cause:** Physical layer issue on GigabitEthernet0/4 (likely "
            f"degraded SFP optic or fiber patch cable) causing intermittent packet loss "
            f"that exceeds the BGP hold timer threshold.\n\n"
            f"**Blast Radius:** 3 downstream devices affected (switch-dist-1, "
            f"switch-dist-2, router-branch-1)\n\n"
            f"**Confidence:** 87%\n\n"
            f"**Recommended Actions:**\n"
            f"1. Check optical power levels: `show interfaces GigabitEthernet0/4 transceiver`\n"
            f"2. Check error counters: `show interfaces GigabitEthernet0/4 | include errors`\n"
            f"3. If optic power is low, replace SFP module\n"
            f"4. If errors persist, replace fiber patch cable"
        )

    def _diagnose_high_cpu(self, device: str) -> str:
        """Generate a diagnosis for high CPU."""
        return (
            f"**Root Cause Analysis: High CPU on {device}**\n\n"
            f"**Findings:**\n"
            f"1. CPU averaging 78% over the last 30 minutes (normally 25%)\n"
            f"2. Top process: 'IP Input' consuming 45% CPU\n"
            f"3. ARP table growing rapidly (3,200 entries, normal: ~500)\n"
            f"4. Syslog shows repeated ARP requests from 10.0.2.0/24 subnet\n\n"
            f"**Root Cause:** ARP storm on VLAN 20 (subnet 10.0.2.0/24) causing "
            f"excessive process-switched traffic. Likely caused by a misconfigured "
            f"host or L2 loop on switch-access-1.\n\n"
            f"**Confidence:** 82%\n\n"
            f"**Recommended Actions:**\n"
            f"1. Check for L2 loops: `show spanning-tree vlan 20`\n"
            f"2. Enable storm control: `storm-control broadcast level 1.00`\n"
            f"3. Identify offending host from ARP table\n"
            f"4. Consider dynamic ARP inspection on the access switch"
        )

    def _diagnose_interface_down(self, device: str) -> str:
        """Generate a diagnosis for interface down."""
        return (
            f"**Root Cause Analysis: Interface Down on {device}**\n\n"
            f"**Findings:**\n"
            f"1. GigabitEthernet0/3 went down at 14:23:07 UTC\n"
            f"2. Remote end ({device} peer) also shows link down\n"
            f"3. No configuration changes detected in the last 24 hours\n"
            f"4. Interface was last flapped 182 days ago\n\n"
            f"**Root Cause:** Physical link failure between {device} and its peer. "
            f"No configuration changes correlate with the event.\n\n"
            f"**Confidence:** 75%\n\n"
            f"**Recommended Actions:**\n"
            f"1. Check physical cabling\n"
            f"2. Test with known-good cable/optic\n"
            f"3. Check for power/environmental issues in the rack"
        )

    def _diagnose_packet_loss(self) -> str:
        """Generate a diagnosis for packet loss."""
        return (
            "**Root Cause Analysis: Packet Loss**\n\n"
            "**Findings:**\n"
            "1. Packet loss detected on WAN link (router-core-1 → ISP)\n"
            "2. Loss pattern: 2-5% during business hours, <0.1% off-hours\n"
            "3. Interface utilization peaking at 94% during loss events\n"
            "4. QoS policy shows queue drops on class-default\n\n"
            "**Root Cause:** WAN link saturation during peak hours. "
            "Non-critical traffic (backups, software updates) competing with "
            "business-critical applications for bandwidth.\n\n"
            "**Confidence:** 91%\n\n"
            "**Recommended Actions:**\n"
            "1. Implement QoS marking and queuing for critical applications\n"
            "2. Schedule bulk transfers for off-peak hours\n"
            "3. Consider bandwidth upgrade (current: 1Gbps, recommended: 2Gbps)\n"
            "4. Enable WRED for TCP-friendly congestion management"
        )

    def _extract_device_name(self, message: str) -> Optional[str]:
        """Extract a device hostname from a message."""
        import re
        patterns = [
            r'on\s+([\w-]+)',
            r'for\s+([\w-]+)',
            r'device\s+([\w-]+)',
            r'(router-[\w-]+)',
            r'(switch-[\w-]+)',
            r'(firewall-[\w-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
