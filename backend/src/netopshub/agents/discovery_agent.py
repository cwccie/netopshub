"""Discovery Agent — network discovery via MCP tools.

Scans networks, builds topology graphs, detects new devices, and
maintains an up-to-date network inventory.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from netopshub.agents.base import BaseAgent
from netopshub.discover.scanner import NetworkScanner
from netopshub.discover.topology import TopologyDiscovery
from netopshub.models import AgentTask, Device

logger = logging.getLogger(__name__)


class DiscoveryAgent(BaseAgent):
    """Discovers network devices and builds topology.

    Capabilities:
    - Subnet scanning via SNMP probes
    - Platform identification
    - Interface inventory
    - LLDP/CDP neighbor discovery
    - Topology graph construction
    """

    def __init__(self, demo_mode: bool = True):
        super().__init__(
            name="discovery",
            description="Network discovery and topology mapping",
        )
        self.scanner = NetworkScanner(demo_mode=demo_mode)
        self.topology = TopologyDiscovery()
        self.demo_mode = demo_mode

    async def process(self, task: AgentTask) -> AgentTask:
        """Process a discovery task."""
        task.status = "running"
        self.log_message("system", f"Processing discovery task: {task.task_type}")

        try:
            if task.task_type == "scan_subnet":
                subnet = task.input_data.get("subnet", "10.0.0.0/24")
                community = task.input_data.get("community", "public")
                devices = await self.scanner.scan_subnet(subnet, community)
                self.topology.add_devices(devices)
                return self._complete_task(task, {
                    "devices_found": len(devices),
                    "devices": [d.model_dump() for d in devices],
                })

            elif task.task_type == "build_topology":
                graph = self.topology.build_demo_topology()
                return self._complete_task(task, {
                    "device_count": len(graph.devices),
                    "link_count": len(graph.links),
                    "topology": self.topology.to_dict(),
                })

            elif task.task_type == "get_neighbors":
                device_id = task.input_data.get("device_id", "")
                neighbors = self.topology.get_neighbors(device_id)
                return self._complete_task(task, {
                    "device_id": device_id,
                    "neighbors": neighbors,
                })

            elif task.task_type == "blast_radius":
                device_id = task.input_data.get("device_id", "")
                radius = self.topology.get_blast_radius(device_id)
                return self._complete_task(task, {
                    "device_id": device_id,
                    "affected_devices": list(radius),
                    "count": len(radius),
                })

            else:
                return self._fail_task(task, f"Unknown task type: {task.task_type}")

        except Exception as e:
            logger.error(f"Discovery task failed: {e}")
            return self._fail_task(task, str(e))

    async def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Handle discovery-related chat queries."""
        self.log_message("user", message)
        msg_lower = message.lower()

        if "discover" in msg_lower or "scan" in msg_lower:
            devices = await self.scanner.scan_subnet("10.0.0.0/24")
            self.topology.add_devices(devices)
            device_list = "\n".join(
                f"  - {d.hostname} ({d.ip_address}) — {d.vendor.value} {d.model}"
                for d in devices
            )
            response = (
                f"I discovered {len(devices)} devices on the network:\n\n"
                f"{device_list}\n\n"
                f"Topology graph has been built with {self.topology.neighbor_count} "
                f"neighbor relationships."
            )
        elif "topology" in msg_lower:
            graph = self.topology.build_demo_topology()
            critical = self.topology.get_critical_devices()
            crit_list = "\n".join(
                f"  - {d['hostname']}: {d['neighbor_count']} connections, "
                f"blast radius: {d['blast_radius']} devices"
                for d in critical[:5]
            )
            response = (
                f"Current topology: {len(graph.devices)} devices, {len(graph.links)} links.\n\n"
                f"Most critical devices:\n{crit_list}"
            )
        elif "device" in msg_lower:
            devices = self.scanner.get_discovered_devices()
            if devices:
                response = f"I have {len(devices)} devices in inventory. Ask about a specific device by name."
            else:
                response = "No devices discovered yet. Run a subnet scan first."
        else:
            response = (
                "I can help with network discovery. Try asking me to:\n"
                "- Discover devices on a subnet\n"
                "- Show the network topology\n"
                "- Find critical devices\n"
                "- Calculate blast radius for a device"
            )

        self.log_message("assistant", response)
        return response
