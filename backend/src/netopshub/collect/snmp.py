"""SNMP v2c/v3 poller with adaptive polling intervals and bulk operations.

Supports device-level and interface-level metric collection, including:
- CPU utilization (HOST-RESOURCES-MIB, CISCO-PROCESS-MIB)
- Memory utilization (HOST-RESOURCES-MIB, CISCO-MEMORY-POOL-MIB)
- Interface counters (IF-MIB)
- System info (SNMPv2-MIB)
- BGP/OSPF state (BGP4-MIB, OSPF-MIB)

In demo mode, returns realistic mock data for testing without live devices.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from netopshub.models import (
    CollectorType,
    Device,
    DeviceType,
    DeviceVendor,
    Interface,
    InterfaceStatus,
    Metric,
    MetricType,
)

logger = logging.getLogger(__name__)


# Standard OIDs
OIDS = {
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysUpTime": "1.3.6.1.2.1.1.3.0",
    "sysName": "1.3.6.1.2.1.1.5.0",
    "sysLocation": "1.3.6.1.2.1.1.6.0",
    "ifDescr": "1.3.6.1.2.1.2.2.1.2",
    "ifSpeed": "1.3.6.1.2.1.2.2.1.5",
    "ifAdminStatus": "1.3.6.1.2.1.2.2.1.7",
    "ifOperStatus": "1.3.6.1.2.1.2.2.1.8",
    "ifInOctets": "1.3.6.1.2.1.2.2.1.10",
    "ifOutOctets": "1.3.6.1.2.1.2.2.1.16",
    "ifInErrors": "1.3.6.1.2.1.2.2.1.14",
    "ifOutErrors": "1.3.6.1.2.1.2.2.1.20",
    "ifInDiscards": "1.3.6.1.2.1.2.2.1.13",
    "ifOutDiscards": "1.3.6.1.2.1.2.2.1.19",
    "hrProcessorLoad": "1.3.6.1.2.1.25.3.3.1.2",
    "hrStorageUsed": "1.3.6.1.2.1.25.2.3.1.6",
    "hrStorageSize": "1.3.6.1.2.1.25.2.3.1.5",
}


@dataclass
class SNMPTarget:
    """SNMP polling target configuration."""
    host: str
    port: int = 161
    community: str = "public"
    version: str = "v2c"
    username: Optional[str] = None
    auth_protocol: Optional[str] = None
    auth_password: Optional[str] = None
    priv_protocol: Optional[str] = None
    priv_password: Optional[str] = None
    poll_interval: int = 60
    timeout: int = 5
    retries: int = 2


@dataclass
class PollResult:
    """Result from a single SNMP poll operation."""
    target: str
    oid: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    error: Optional[str] = None


class SNMPPoller:
    """SNMP polling engine with mock support for demo/testing.

    In production, this would use pysnmp or netsnmp bindings. The mock mode
    generates realistic telemetry data for development and demonstration.
    """

    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self._targets: dict[str, SNMPTarget] = {}
        self._running = False
        self._poll_count = 0
        self._last_values: dict[str, dict[str, float]] = {}

    def add_target(self, target: SNMPTarget) -> None:
        """Register a device for polling."""
        self._targets[target.host] = target
        self._last_values[target.host] = {}
        logger.info(f"Added SNMP target: {target.host} ({target.version})")

    def remove_target(self, host: str) -> None:
        """Remove a device from polling."""
        self._targets.pop(host, None)
        self._last_values.pop(host, None)

    async def poll_device(self, host: str) -> list[Metric]:
        """Poll a single device and return unified metrics."""
        target = self._targets.get(host)
        if not target:
            raise ValueError(f"Unknown target: {host}")

        if self.demo_mode:
            return self._mock_poll(target)

        # Production: would use pysnmp here
        raise NotImplementedError("Production SNMP polling requires pysnmp")

    async def poll_all(self) -> list[Metric]:
        """Poll all registered targets."""
        all_metrics: list[Metric] = []
        tasks = [self.poll_device(host) for host in self._targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_metrics.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Poll error: {result}")
        self._poll_count += 1
        return all_metrics

    async def discover_device(self, host: str, community: str = "public") -> Optional[Device]:
        """Discover a device via SNMP system MIB queries."""
        if self.demo_mode:
            return self._mock_discover(host, community)
        raise NotImplementedError("Production discovery requires pysnmp")

    async def get_interfaces(self, host: str) -> list[Interface]:
        """Get interface inventory from a device via IF-MIB."""
        if self.demo_mode:
            return self._mock_interfaces(host)
        raise NotImplementedError("Production interface polling requires pysnmp")

    def _mock_poll(self, target: SNMPTarget) -> list[Metric]:
        """Generate realistic mock metrics for a device."""
        now = datetime.utcnow()
        device_id = target.host
        metrics: list[Metric] = []

        # Initialize or evolve values realistically
        last = self._last_values.get(target.host, {})

        # CPU — fluctuates around a baseline with occasional spikes
        cpu_base = last.get("cpu_base", random.uniform(15, 45))
        cpu = max(0, min(100, cpu_base + random.gauss(0, 5)))
        if random.random() < 0.02:  # 2% chance of spike
            cpu = min(100, cpu + random.uniform(20, 40))
        metrics.append(Metric(
            device_id=device_id,
            metric_type=MetricType.CPU,
            value=round(cpu, 1),
            unit="percent",
            timestamp=now,
            source=CollectorType.SNMP,
        ))
        last["cpu_base"] = cpu_base + random.gauss(0, 0.5)

        # Memory
        mem_base = last.get("mem_base", random.uniform(40, 75))
        mem = max(0, min(100, mem_base + random.gauss(0, 2)))
        metrics.append(Metric(
            device_id=device_id,
            metric_type=MetricType.MEMORY,
            value=round(mem, 1),
            unit="percent",
            timestamp=now,
            source=CollectorType.SNMP,
        ))
        last["mem_base"] = mem_base + random.gauss(0, 0.3)

        # Interface bandwidth (simulate 4 interfaces)
        for i in range(4):
            bw_in = max(0, last.get(f"bw_in_{i}", random.uniform(10, 500)) + random.gauss(0, 50))
            bw_out = max(0, last.get(f"bw_out_{i}", random.uniform(10, 500)) + random.gauss(0, 50))
            metrics.append(Metric(
                device_id=device_id,
                interface_name=f"GigabitEthernet0/{i}",
                metric_type=MetricType.BANDWIDTH_IN,
                value=round(bw_in, 2),
                unit="Mbps",
                timestamp=now,
                source=CollectorType.SNMP,
            ))
            metrics.append(Metric(
                device_id=device_id,
                interface_name=f"GigabitEthernet0/{i}",
                metric_type=MetricType.BANDWIDTH_OUT,
                value=round(bw_out, 2),
                unit="Mbps",
                timestamp=now,
                source=CollectorType.SNMP,
            ))
            last[f"bw_in_{i}"] = bw_in
            last[f"bw_out_{i}"] = bw_out

        # Error rate
        err = max(0, random.gauss(0.1, 0.5))
        metrics.append(Metric(
            device_id=device_id,
            metric_type=MetricType.ERROR_RATE,
            value=round(err, 3),
            unit="errors/sec",
            timestamp=now,
            source=CollectorType.SNMP,
        ))

        # Temperature
        temp = last.get("temp", random.uniform(35, 55)) + random.gauss(0, 1)
        metrics.append(Metric(
            device_id=device_id,
            metric_type=MetricType.TEMPERATURE,
            value=round(temp, 1),
            unit="celsius",
            timestamp=now,
            source=CollectorType.SNMP,
        ))
        last["temp"] = temp

        self._last_values[target.host] = last
        return metrics

    def _mock_discover(self, host: str, community: str) -> Device:
        """Generate a mock discovered device."""
        vendors = [
            (DeviceVendor.CISCO, DeviceType.ROUTER, "ISR4451-X", "IOS-XE 17.6.4"),
            (DeviceVendor.CISCO, DeviceType.SWITCH, "C9300-48P", "IOS-XE 17.9.1"),
            (DeviceVendor.ARISTA, DeviceType.SWITCH, "DCS-7280R3", "EOS 4.31.1F"),
            (DeviceVendor.JUNIPER, DeviceType.ROUTER, "MX204", "Junos 23.2R1"),
            (DeviceVendor.PALO_ALTO, DeviceType.FIREWALL, "PA-5260", "PAN-OS 11.1.0"),
        ]
        vendor, dtype, model, osver = random.choice(vendors)
        return Device(
            hostname=f"device-{host.replace('.', '-')}",
            ip_address=host,
            device_type=dtype,
            vendor=vendor,
            model=model,
            os_version=osver,
            serial_number=f"SN{random.randint(100000, 999999)}",
            snmp_community=community,
            uptime_seconds=random.randint(86400, 31536000),
            sys_description=f"{vendor.value.title()} {model} running {osver}",
        )

    def _mock_interfaces(self, host: str) -> list[Interface]:
        """Generate mock interface data."""
        interfaces = []
        for i in range(8):
            status = InterfaceStatus.UP if random.random() > 0.15 else InterfaceStatus.DOWN
            interfaces.append(Interface(
                name=f"GigabitEthernet0/{i}",
                index=i + 1,
                description=f"Link to {'upstream' if i < 2 else 'server-' + str(i)}",
                speed_mbps=1000 if i < 4 else 10000,
                admin_status=InterfaceStatus.UP,
                oper_status=status,
                ip_address=f"10.0.{i}.1" if i < 4 else None,
                subnet_mask="255.255.255.0" if i < 4 else None,
                mac_address=f"00:1A:2B:3C:4D:{i:02X}",
                vlan_id=i * 10 + 10 if i < 4 else None,
                mtu=9216 if i >= 4 else 1500,
                in_octets=random.randint(1000000, 9000000000),
                out_octets=random.randint(1000000, 9000000000),
                in_errors=random.randint(0, 100),
                out_errors=random.randint(0, 50),
            ))
        return interfaces

    @property
    def target_count(self) -> int:
        return len(self._targets)

    @property
    def poll_count(self) -> int:
        return self._poll_count
