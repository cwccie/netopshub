"""Topology discovery via LLDP/CDP neighbor information.

Builds a network topology graph from neighbor relationship data,
supporting LLDP, CDP, BGP, and OSPF neighbor protocols.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from netopshub.models import (
    Device,
    Neighbor,
    TopologyGraph,
    TopologyLink,
)

logger = logging.getLogger(__name__)


class TopologyDiscovery:
    """Builds and maintains the network topology graph.

    Discovers neighbor relationships from LLDP/CDP data and constructs
    a graph representation of the network topology.
    """

    def __init__(self):
        self._devices: dict[str, Device] = {}
        self._neighbors: list[Neighbor] = []
        self._links: list[TopologyLink] = []
        self._adjacency: dict[str, set[str]] = defaultdict(set)

    def add_device(self, device: Device) -> None:
        """Add a device to the topology."""
        self._devices[device.id] = device

    def add_devices(self, devices: list[Device]) -> None:
        """Add multiple devices to the topology."""
        for device in devices:
            self.add_device(device)

    def add_neighbor(self, neighbor: Neighbor) -> None:
        """Add a neighbor relationship."""
        self._neighbors.append(neighbor)
        self._adjacency[neighbor.local_device_id].add(neighbor.remote_device_id)
        self._adjacency[neighbor.remote_device_id].add(neighbor.local_device_id)

    def build_topology(self) -> TopologyGraph:
        """Build the complete topology graph from neighbor data."""
        self._links = []
        seen_links: set[tuple[str, str]] = set()

        for neighbor in self._neighbors:
            link_key = tuple(sorted([
                f"{neighbor.local_device_id}:{neighbor.local_interface}",
                f"{neighbor.remote_device_id}:{neighbor.remote_interface}",
            ]))
            if link_key in seen_links:
                continue
            seen_links.add(link_key)

            self._links.append(TopologyLink(
                source_device_id=neighbor.local_device_id,
                source_interface=neighbor.local_interface,
                target_device_id=neighbor.remote_device_id,
                target_interface=neighbor.remote_interface,
                protocol=neighbor.protocol,
            ))

        return TopologyGraph(
            devices=list(self._devices.values()),
            links=self._links,
            generated_at=datetime.utcnow(),
        )

    def get_neighbors(self, device_id: str) -> list[str]:
        """Get all neighbor device IDs for a device."""
        return list(self._adjacency.get(device_id, set()))

    def get_path(self, source_id: str, target_id: str) -> list[str]:
        """Find shortest path between two devices (BFS)."""
        if source_id == target_id:
            return [source_id]
        if source_id not in self._adjacency:
            return []

        visited: set[str] = {source_id}
        queue: list[list[str]] = [[source_id]]

        while queue:
            path = queue.pop(0)
            current = path[-1]
            for neighbor in self._adjacency.get(current, set()):
                if neighbor == target_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return []

    def get_blast_radius(self, device_id: str, max_hops: int = 2) -> set[str]:
        """Calculate blast radius — devices affected if this device fails.

        Returns all devices within max_hops of the given device.
        """
        affected: set[str] = set()
        current_layer: set[str] = {device_id}

        for _ in range(max_hops):
            next_layer: set[str] = set()
            for dev in current_layer:
                for neighbor in self._adjacency.get(dev, set()):
                    if neighbor not in affected and neighbor != device_id:
                        next_layer.add(neighbor)
                        affected.add(neighbor)
            current_layer = next_layer

        return affected

    def get_critical_devices(self) -> list[dict[str, Any]]:
        """Identify critical devices (highest connectivity / articulation points)."""
        criticality: list[dict[str, Any]] = []
        for device_id, neighbors in self._adjacency.items():
            device = self._devices.get(device_id)
            criticality.append({
                "device_id": device_id,
                "hostname": device.hostname if device else "unknown",
                "neighbor_count": len(neighbors),
                "blast_radius": len(self.get_blast_radius(device_id)),
            })
        return sorted(criticality, key=lambda x: -x["neighbor_count"])

    def to_dict(self) -> dict[str, Any]:
        """Export topology as a dictionary for serialization."""
        graph = self.build_topology()
        return {
            "devices": [d.model_dump() for d in graph.devices],
            "links": [l.model_dump() for l in graph.links],
            "generated_at": graph.generated_at.isoformat(),
            "device_count": len(graph.devices),
            "link_count": len(graph.links),
        }

    def build_demo_topology(self) -> TopologyGraph:
        """Build a demo topology with realistic network layout."""
        from netopshub.discover.scanner import NetworkScanner
        scanner = NetworkScanner(demo_mode=True)

        import asyncio
        loop = asyncio.new_event_loop()
        devices = loop.run_until_complete(
            scanner.scan_subnet("10.0.0.0/24")
        ) if not asyncio.get_event_loop().is_running() else []
        # If event loop is running, use mock data directly
        if not devices:
            devices = scanner._mock_scan("10.0.0.0/24", "public")

        self.add_devices(devices)

        # Create realistic neighbor relationships
        device_map = {d.hostname: d for d in devices}

        neighbor_pairs = [
            ("router-core-1", "Gi0/0", "router-core-2", "Gi0/0", "lldp"),
            ("router-core-1", "Gi0/1", "switch-dist-1", "Et1", "lldp"),
            ("router-core-1", "Gi0/2", "switch-dist-2", "Et1", "lldp"),
            ("router-core-2", "Gi0/1", "switch-dist-1", "Et2", "lldp"),
            ("router-core-2", "Gi0/2", "switch-dist-2", "Et2", "lldp"),
            ("switch-dist-1", "Et3", "switch-access-1", "Gi0/1", "lldp"),
            ("switch-dist-1", "Et4", "switch-access-2", "Gi0/1", "lldp"),
            ("switch-dist-2", "Et3", "switch-access-1", "Gi0/2", "lldp"),
            ("switch-dist-2", "Et4", "switch-access-2", "Gi0/2", "lldp"),
            ("router-core-1", "Gi0/3", "firewall-edge-1", "eth1/1", "lldp"),
            ("router-core-2", "Gi0/3", "firewall-edge-1", "eth1/2", "lldp"),
            ("router-core-1", "Gi0/4", "router-branch-1", "ge-0/0/0", "bgp"),
        ]

        for local_host, local_intf, remote_host, remote_intf, proto in neighbor_pairs:
            local_dev = device_map.get(local_host)
            remote_dev = device_map.get(remote_host)
            if local_dev and remote_dev:
                self.add_neighbor(Neighbor(
                    local_device_id=local_dev.id,
                    local_interface=local_intf,
                    remote_device_id=remote_dev.id,
                    remote_interface=remote_intf,
                    remote_hostname=remote_host,
                    remote_ip=remote_dev.ip_address,
                    protocol=proto,
                ))

        return self.build_topology()

    @property
    def device_count(self) -> int:
        return len(self._devices)

    @property
    def link_count(self) -> int:
        return len(self._links)

    @property
    def neighbor_count(self) -> int:
        return len(self._neighbors)
