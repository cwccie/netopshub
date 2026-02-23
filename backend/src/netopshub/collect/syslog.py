"""Syslog listener (RFC 3164/5424) with severity classification and pattern extraction.

Receives syslog messages from network devices, parses them into structured
records, and classifies severity for alerting and correlation.
"""

from __future__ import annotations

import logging
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from netopshub.models import SyslogMessage

logger = logging.getLogger(__name__)


FACILITY_NAMES = {
    0: "kern", 1: "user", 2: "mail", 3: "daemon", 4: "auth",
    5: "syslog", 6: "lpr", 7: "news", 8: "uucp", 9: "cron",
    10: "authpriv", 11: "ftp", 16: "local0", 17: "local1",
    18: "local2", 19: "local3", 20: "local4", 21: "local5",
    22: "local6", 23: "local7",
}

SEVERITY_NAMES = {
    0: "emergency", 1: "alert", 2: "critical", 3: "error",
    4: "warning", 5: "notice", 6: "informational", 7: "debug",
}


# Common syslog patterns from network devices
NETWORK_SYSLOG_PATTERNS = [
    {"pattern": r"BGP-5-ADJCHANGE.*neighbor\s+(\S+).*(\w+)$", "category": "bgp_state_change"},
    {"pattern": r"OSPF-5-ADJCHG.*(\S+).*from\s+(\w+)\s+to\s+(\w+)", "category": "ospf_state_change"},
    {"pattern": r"LINK-3-UPDOWN.*Interface\s+(\S+).*changed.*to\s+(\w+)", "category": "interface_state"},
    {"pattern": r"SYS-5-RESTART", "category": "device_restart"},
    {"pattern": r"SEC-6-IPACCESSLOG", "category": "acl_hit"},
    {"pattern": r"HSRP-5-STATECHANGE", "category": "hsrp_state"},
    {"pattern": r"EIGRP-5-NBRCHANGE", "category": "eigrp_neighbor"},
    {"pattern": r"STP-.*TOPOLOGY_CHANGE", "category": "stp_change"},
    {"pattern": r"CONFIG-.*CONFIG_I", "category": "config_change"},
    {"pattern": r"PLATFORM-.*FAN|TEMP|POWER", "category": "environmental"},
]


class SyslogListener:
    """Syslog message receiver and parser.

    In demo mode, generates realistic network syslog messages.
    In production, would bind to UDP/TCP port 514.
    """

    def __init__(self, listen_port: int = 514, demo_mode: bool = True):
        self.listen_port = listen_port
        self.demo_mode = demo_mode
        self._running = False
        self._messages: list[SyslogMessage] = []
        self._message_counts: dict[int, int] = defaultdict(int)
        self._pattern_counts: dict[str, int] = defaultdict(int)

    async def start(self) -> None:
        """Start the syslog listener."""
        self._running = True
        logger.info(f"Syslog listener started on port {self.listen_port}")
        if self.demo_mode:
            self._generate_demo_messages()

    async def stop(self) -> None:
        """Stop the syslog listener."""
        self._running = False
        logger.info("Syslog listener stopped")

    def get_messages(
        self,
        since: Optional[datetime] = None,
        severity: Optional[int] = None,
        device_hostname: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 500,
    ) -> list[SyslogMessage]:
        """Query collected syslog messages with filters."""
        msgs = self._messages
        if since:
            msgs = [m for m in msgs if m.timestamp >= since]
        if severity is not None:
            msgs = [m for m in msgs if m.severity <= severity]
        if device_hostname:
            msgs = [m for m in msgs if m.device_hostname == device_hostname]
        if category:
            msgs = [m for m in msgs if m.structured_data.get("category") == category]
        return msgs[:limit]

    def classify_message(self, message: str) -> dict[str, Any]:
        """Classify a syslog message against known patterns."""
        for pat_info in NETWORK_SYSLOG_PATTERNS:
            match = re.search(pat_info["pattern"], message, re.IGNORECASE)
            if match:
                return {
                    "category": pat_info["category"],
                    "matched": True,
                    "groups": match.groups(),
                }
        return {"category": "unclassified", "matched": False, "groups": ()}

    def get_severity_distribution(self) -> dict[str, int]:
        """Return message counts by severity."""
        return {
            SEVERITY_NAMES.get(sev, f"severity-{sev}"): count
            for sev, count in sorted(self._message_counts.items())
        }

    def get_category_distribution(self) -> dict[str, int]:
        """Return message counts by category."""
        return dict(self._pattern_counts)

    def parse_rfc5424(self, raw: str) -> Optional[SyslogMessage]:
        """Parse an RFC 5424 syslog message."""
        pattern = r"<(\d+)>1\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)"
        match = re.match(pattern, raw)
        if not match:
            return None

        priority = int(match.group(1))
        facility = priority >> 3
        severity = priority & 7

        return SyslogMessage(
            source_ip="0.0.0.0",
            device_hostname=match.group(3),
            facility=facility,
            severity=severity,
            message=match.group(7),
            program=match.group(4),
        )

    def parse_rfc3164(self, raw: str) -> Optional[SyslogMessage]:
        """Parse an RFC 3164 (BSD) syslog message."""
        pattern = r"<(\d+)>(\w{3}\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+(.*)"
        match = re.match(pattern, raw)
        if not match:
            return None

        priority = int(match.group(1))
        facility = priority >> 3
        severity = priority & 7

        return SyslogMessage(
            source_ip="0.0.0.0",
            device_hostname=match.group(3),
            facility=facility,
            severity=severity,
            message=match.group(4),
        )

    def _generate_demo_messages(self, count: int = 200) -> None:
        """Generate realistic demo syslog messages."""
        devices = [
            ("router-core-1", "10.0.0.1"),
            ("router-core-2", "10.0.0.2"),
            ("switch-dist-1", "10.0.1.1"),
            ("switch-dist-2", "10.0.1.2"),
            ("switch-access-1", "10.0.2.1"),
            ("firewall-edge-1", "10.0.0.254"),
        ]

        templates = [
            (6, "%SYS-6-LOGGINGHOST_STARTSTOP: Logging to host 10.0.0.100 port 514 started"),
            (5, "%BGP-5-ADJCHANGE: neighbor 10.0.0.{n} {state}"),
            (5, "%OSPF-5-ADJCHG: Process 1, Nbr 10.0.{n}.{n2} on GigabitEthernet0/{intf} from FULL to DOWN"),
            (3, "%LINK-3-UPDOWN: Interface GigabitEthernet0/{intf}, changed state to down"),
            (5, "%LINK-3-UPDOWN: Interface GigabitEthernet0/{intf}, changed state to up"),
            (4, "%SYS-5-CONFIG_I: Configured from console by admin on vty0 (10.0.0.100)"),
            (6, "%SEC-6-IPACCESSLOGP: list OUTSIDE denied tcp 192.168.1.{n}(12345) -> 10.0.1.{n2}(22), 1 packet"),
            (2, "%PLATFORM-2-TEMP_CRITICAL: Temperature sensor 1 reading 85C exceeds threshold 80C"),
            (4, "%STP-4-TOPOLOGY_CHANGE: Topology change detected on GigabitEthernet0/{intf}"),
            (5, "%HSRP-5-STATECHANGE: GigabitEthernet0/0 Grp 1 state Active -> Standby"),
            (6, "%EIGRP-5-NBRCHANGE: EIGRP-IPv4 1: Neighbor 10.0.{n}.{n2} (GigabitEthernet0/{intf}) is up"),
            (3, "%EIGRP-5-NBRCHANGE: EIGRP-IPv4 1: Neighbor 10.0.{n}.{n2} (GigabitEthernet0/{intf}) is down: holding time expired"),
            (5, "%LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/{intf}, changed state to up"),
            (4, "%SNMP-4-NOTRAPIP: SNMP trap source not specified, using default"),
            (6, "%SYS-6-CLOCKUPDATE: System clock has been updated"),
        ]

        now = datetime.utcnow()
        for _ in range(count):
            hostname, source_ip = random.choice(devices)
            severity, template = random.choice(templates)
            message = template.format(
                n=random.randint(1, 10),
                n2=random.randint(1, 254),
                intf=random.randint(0, 7),
                state=random.choice(["Up", "Down"]),
            )

            classification = self.classify_message(message)
            msg = SyslogMessage(
                device_hostname=hostname,
                source_ip=source_ip,
                facility=23,  # local7
                severity=severity,
                timestamp=now - timedelta(minutes=random.randint(0, 1440)),
                message=message,
                program="IOS",
                structured_data={"category": classification["category"]},
            )
            self._messages.append(msg)
            self._message_counts[severity] += 1
            self._pattern_counts[classification["category"]] += 1

        # Sort by timestamp
        self._messages.sort(key=lambda m: m.timestamp, reverse=True)

    @property
    def message_count(self) -> int:
        return len(self._messages)
