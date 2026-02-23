"""Network discovery — LLDP/CDP topology, device enumeration, interface inventory."""

from netopshub.discover.topology import TopologyDiscovery
from netopshub.discover.scanner import NetworkScanner

__all__ = ["TopologyDiscovery", "NetworkScanner"]
