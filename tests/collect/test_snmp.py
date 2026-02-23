"""Tests for SNMP poller."""

import pytest
from netopshub.collect.snmp import SNMPPoller, SNMPTarget
from netopshub.models import MetricType


class TestSNMPPoller:
    def test_init(self, snmp_poller):
        assert snmp_poller.demo_mode is True
        assert snmp_poller.target_count == 0
        assert snmp_poller.poll_count == 0

    def test_add_target(self, snmp_poller):
        target = SNMPTarget(host="10.0.0.1")
        snmp_poller.add_target(target)
        assert snmp_poller.target_count == 1

    def test_remove_target(self, snmp_poller):
        target = SNMPTarget(host="10.0.0.1")
        snmp_poller.add_target(target)
        snmp_poller.remove_target("10.0.0.1")
        assert snmp_poller.target_count == 0

    @pytest.mark.asyncio
    async def test_poll_device(self, snmp_poller):
        snmp_poller.add_target(SNMPTarget(host="10.0.0.1"))
        metrics = await snmp_poller.poll_device("10.0.0.1")
        assert len(metrics) > 0
        assert any(m.metric_type == MetricType.CPU for m in metrics)
        assert any(m.metric_type == MetricType.MEMORY for m in metrics)

    @pytest.mark.asyncio
    async def test_poll_all(self, snmp_poller):
        snmp_poller.add_target(SNMPTarget(host="10.0.0.1"))
        snmp_poller.add_target(SNMPTarget(host="10.0.0.2"))
        metrics = await snmp_poller.poll_all()
        assert len(metrics) > 0
        assert snmp_poller.poll_count == 1

    @pytest.mark.asyncio
    async def test_poll_unknown_target(self, snmp_poller):
        with pytest.raises(ValueError):
            await snmp_poller.poll_device("10.0.0.99")

    @pytest.mark.asyncio
    async def test_discover_device(self, snmp_poller):
        device = await snmp_poller.discover_device("10.0.0.1")
        assert device is not None
        assert device.ip_address == "10.0.0.1"
        assert device.hostname != ""

    @pytest.mark.asyncio
    async def test_get_interfaces(self, snmp_poller):
        interfaces = await snmp_poller.get_interfaces("10.0.0.1")
        assert len(interfaces) > 0
        assert interfaces[0].name != ""

    @pytest.mark.asyncio
    async def test_metric_values_realistic(self, snmp_poller):
        snmp_poller.add_target(SNMPTarget(host="10.0.0.1"))
        metrics = await snmp_poller.poll_device("10.0.0.1")
        for m in metrics:
            if m.metric_type == MetricType.CPU:
                assert 0 <= m.value <= 100
            if m.metric_type == MetricType.MEMORY:
                assert 0 <= m.value <= 100
