"""Network scanner for device discovery and enumeration.

Scans subnets for SNMP-manageable devices, performs platform identification,
and builds an initial device inventory.
"""

from __future__ import annotations

import ipaddress
import logging
import random
from datetime import datetime
from typing import Optional

from netopshub.collect.snmp import SNMPPoller
from netopshub.models import (
    Device,
    DeviceType,
    DeviceVendor,
    Interface,
    InterfaceStatus,
)

logger = logging.getLogger(__name__)


# Platform identification patterns
PLATFORM_SIGNATURES = {
    "Cisco IOS": (DeviceVendor.CISCO, DeviceType.ROUTER),
    "Cisco IOS-XE": (DeviceVendor.CISCO, DeviceType.ROUTER),
    "Cisco NX-OS": (DeviceVendor.CISCO, DeviceType.SWITCH),
    "Cisco Adaptive Security": (DeviceVendor.CISCO, DeviceType.FIREWALL),
    "Arista Networks EOS": (DeviceVendor.ARISTA, DeviceType.SWITCH),
    "Juniper Networks": (DeviceVendor.JUNIPER, DeviceType.ROUTER),
    "Palo Alto Networks": (DeviceVendor.PALO_ALTO, DeviceType.FIREWALL),
    "Fortinet FortiGate": (DeviceVendor.FORTINET, DeviceType.FIREWALL),
}


class NetworkScanner:
    """Scans networks for device discovery.

    Uses SNMP probes to discover devices, identify platforms, and
    build interface inventories.
    """

    def __init__(self, snmp_poller: Optional[SNMPPoller] = None, demo_mode: bool = True):
        self.snmp = snmp_poller or SNMPPoller(demo_mode=demo_mode)
        self.demo_mode = demo_mode
        self._discovered: dict[str, Device] = {}

    async def scan_subnet(
        self,
        subnet: str,
        community: str = "public",
        max_concurrent: int = 50,
    ) -> list[Device]:
        """Scan a subnet for SNMP-manageable devices.

        Args:
            subnet: CIDR notation subnet (e.g., "10.0.0.0/24")
            community: SNMP community string
            max_concurrent: Maximum concurrent SNMP probes
        """
        network = ipaddress.ip_network(subnet, strict=False)
        hosts = list(network.hosts())
        logger.info(f"Scanning {subnet} ({len(hosts)} hosts)")

        if self.demo_mode:
            return self._mock_scan(subnet, community)

        raise NotImplementedError("Production scanning requires pysnmp")

    async def scan_host(self, host: str, community: str = "public") -> Optional[Device]:
        """Probe a single host for SNMP discovery."""
        if self.demo_mode:
            return await self.snmp.discover_device(host, community)
        raise NotImplementedError("Production scanning requires pysnmp")

    async def get_interface_inventory(self, device: Device) -> list[Interface]:
        """Get full interface inventory for a discovered device."""
        if self.demo_mode:
            return await self.snmp.get_interfaces(device.ip_address)
        raise NotImplementedError("Production interface polling requires pysnmp")

    def identify_platform(self, sys_description: str) -> tuple[DeviceVendor, DeviceType]:
        """Identify device platform from sysDescription string."""
        for signature, (vendor, dtype) in PLATFORM_SIGNATURES.items():
            if signature.lower() in sys_description.lower():
                return vendor, dtype
        return DeviceVendor.UNKNOWN, DeviceType.UNKNOWN

    def get_discovered_devices(self) -> list[Device]:
        """Return all discovered devices."""
        return list(self._discovered.values())

    def get_device(self, device_id: str) -> Optional[Device]:
        """Get a specific discovered device by ID."""
        return self._discovered.get(device_id)

    def _mock_scan(self, subnet: str, community: str) -> list[Device]:
        """Generate mock scan results for a subnet."""
        mock_devices = [
            Device(
                hostname="router-core-1",
                ip_address="10.0.0.1",
                device_type=DeviceType.ROUTER,
                vendor=DeviceVendor.CISCO,
                model="ISR4451-X",
                os_version="IOS-XE 17.6.4",
                serial_number="FTX2150A1BC",
                location="DC1-ROW1-RACK3",
                site="datacenter-1",
                snmp_community=community,
                uptime_seconds=15724800,
                sys_description="Cisco IOS-XE ISR4451-X running 17.6.4",
            ),
            Device(
                hostname="router-core-2",
                ip_address="10.0.0.2",
                device_type=DeviceType.ROUTER,
                vendor=DeviceVendor.CISCO,
                model="ISR4451-X",
                os_version="IOS-XE 17.6.4",
                serial_number="FTX2150A1BD",
                location="DC1-ROW1-RACK4",
                site="datacenter-1",
                snmp_community=community,
                uptime_seconds=15724800,
                sys_description="Cisco IOS-XE ISR4451-X running 17.6.4",
            ),
            Device(
                hostname="switch-dist-1",
                ip_address="10.0.1.1",
                device_type=DeviceType.SWITCH,
                vendor=DeviceVendor.ARISTA,
                model="DCS-7280R3",
                os_version="EOS 4.31.1F",
                serial_number="SSJ21140123",
                location="DC1-ROW2-RACK1",
                site="datacenter-1",
                snmp_community=community,
                uptime_seconds=8640000,
                sys_description="Arista Networks EOS DCS-7280R3 4.31.1F",
            ),
            Device(
                hostname="switch-dist-2",
                ip_address="10.0.1.2",
                device_type=DeviceType.SWITCH,
                vendor=DeviceVendor.ARISTA,
                model="DCS-7280R3",
                os_version="EOS 4.31.1F",
                serial_number="SSJ21140124",
                location="DC1-ROW2-RACK2",
                site="datacenter-1",
                snmp_community=community,
                uptime_seconds=8640000,
                sys_description="Arista Networks EOS DCS-7280R3 4.31.1F",
            ),
            Device(
                hostname="switch-access-1",
                ip_address="10.0.2.1",
                device_type=DeviceType.SWITCH,
                vendor=DeviceVendor.CISCO,
                model="C9300-48P",
                os_version="IOS-XE 17.9.1",
                serial_number="FCW2234L0PQ",
                location="Office-Floor2",
                site="main-office",
                snmp_community=community,
                uptime_seconds=2592000,
                sys_description="Cisco IOS-XE C9300-48P running 17.9.1",
            ),
            Device(
                hostname="switch-access-2",
                ip_address="10.0.2.2",
                device_type=DeviceType.SWITCH,
                vendor=DeviceVendor.CISCO,
                model="C9300-48P",
                os_version="IOS-XE 17.9.1",
                serial_number="FCW2234L0PR",
                location="Office-Floor3",
                site="main-office",
                snmp_community=community,
                uptime_seconds=2592000,
                sys_description="Cisco IOS-XE C9300-48P running 17.9.1",
            ),
            Device(
                hostname="firewall-edge-1",
                ip_address="10.0.0.254",
                device_type=DeviceType.FIREWALL,
                vendor=DeviceVendor.PALO_ALTO,
                model="PA-5260",
                os_version="PAN-OS 11.1.0",
                serial_number="PA5260-SN001",
                location="DC1-ROW1-RACK1",
                site="datacenter-1",
                snmp_community=community,
                uptime_seconds=31536000,
                sys_description="Palo Alto Networks PA-5260 PAN-OS 11.1.0",
            ),
            Device(
                hostname="router-branch-1",
                ip_address="10.0.3.1",
                device_type=DeviceType.ROUTER,
                vendor=DeviceVendor.JUNIPER,
                model="MX204",
                os_version="Junos 23.2R1",
                serial_number="JN1234567890",
                location="Branch-Office-1",
                site="branch-1",
                snmp_community=community,
                uptime_seconds=5184000,
                sys_description="Juniper Networks MX204 Junos 23.2R1",
            ),
        ]

        for device in mock_devices:
            self._discovered[device.id] = device

        logger.info(f"Discovered {len(mock_devices)} devices on {subnet}")
        return mock_devices

    @property
    def discovered_count(self) -> int:
        return len(self._discovered)
