"""Tests for topology discovery."""

import pytest
from netopshub.discover.topology import TopologyDiscovery
from netopshub.models import Device, DeviceType, DeviceVendor, Neighbor


class TestTopologyDiscovery:
    def test_add_device(self, topology):
        device = Device(hostname="r1", ip_address="10.0.0.1", device_type=DeviceType.ROUTER, vendor=DeviceVendor.CISCO)
        topology.add_device(device)
        assert topology.device_count == 1

    def test_add_neighbor(self, topology):
        d1 = Device(hostname="r1", ip_address="10.0.0.1", device_type=DeviceType.ROUTER, vendor=DeviceVendor.CISCO)
        d2 = Device(hostname="r2", ip_address="10.0.0.2", device_type=DeviceType.ROUTER, vendor=DeviceVendor.CISCO)
        topology.add_device(d1)
        topology.add_device(d2)
        topology.add_neighbor(Neighbor(
            local_device_id=d1.id,
            local_interface="Gi0/0",
            remote_device_id=d2.id,
            remote_interface="Gi0/0",
        ))
        assert topology.neighbor_count == 1

    def test_build_topology(self, topology):
        d1 = Device(hostname="r1", ip_address="10.0.0.1", device_type=DeviceType.ROUTER, vendor=DeviceVendor.CISCO)
        d2 = Device(hostname="r2", ip_address="10.0.0.2", device_type=DeviceType.ROUTER, vendor=DeviceVendor.CISCO)
        topology.add_devices([d1, d2])
        topology.add_neighbor(Neighbor(
            local_device_id=d1.id,
            local_interface="Gi0/0",
            remote_device_id=d2.id,
            remote_interface="Gi0/0",
        ))
        graph = topology.build_topology()
        assert len(graph.devices) == 2
        assert len(graph.links) == 1

    def test_get_path(self, topology):
        d1 = Device(hostname="r1", ip_address="10.0.0.1", device_type=DeviceType.ROUTER, vendor=DeviceVendor.CISCO)
        d2 = Device(hostname="r2", ip_address="10.0.0.2", device_type=DeviceType.ROUTER, vendor=DeviceVendor.CISCO)
        d3 = Device(hostname="s1", ip_address="10.0.1.1", device_type=DeviceType.SWITCH, vendor=DeviceVendor.ARISTA)
        topology.add_devices([d1, d2, d3])
        topology.add_neighbor(Neighbor(local_device_id=d1.id, local_interface="Gi0/0", remote_device_id=d2.id, remote_interface="Gi0/0"))
        topology.add_neighbor(Neighbor(local_device_id=d2.id, local_interface="Gi0/1", remote_device_id=d3.id, remote_interface="Et1"))
        path = topology.get_path(d1.id, d3.id)
        assert len(path) == 3

    def test_blast_radius(self, topology):
        d1 = Device(hostname="core", ip_address="10.0.0.1", device_type=DeviceType.ROUTER, vendor=DeviceVendor.CISCO)
        d2 = Device(hostname="dist1", ip_address="10.0.1.1", device_type=DeviceType.SWITCH, vendor=DeviceVendor.ARISTA)
        d3 = Device(hostname="dist2", ip_address="10.0.1.2", device_type=DeviceType.SWITCH, vendor=DeviceVendor.ARISTA)
        topology.add_devices([d1, d2, d3])
        topology.add_neighbor(Neighbor(local_device_id=d1.id, local_interface="Gi0/0", remote_device_id=d2.id, remote_interface="Et1"))
        topology.add_neighbor(Neighbor(local_device_id=d1.id, local_interface="Gi0/1", remote_device_id=d3.id, remote_interface="Et1"))
        radius = topology.get_blast_radius(d1.id)
        assert len(radius) == 2

    def test_demo_topology(self, topology):
        graph = topology.build_demo_topology()
        assert len(graph.devices) > 0
        assert len(graph.links) > 0

    def test_to_dict(self, topology):
        topology.build_demo_topology()
        data = topology.to_dict()
        assert "devices" in data
        assert "links" in data
        assert data["device_count"] > 0
