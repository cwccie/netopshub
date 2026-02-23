"""Tests for unified collector."""

import pytest
from netopshub.collect.unified import UnifiedCollector
from netopshub.collect.snmp import SNMPTarget


class TestUnifiedCollector:
    @pytest.mark.asyncio
    async def test_start_stop(self, unified_collector):
        await unified_collector.start()
        assert unified_collector.is_running is True
        await unified_collector.stop()
        assert unified_collector.is_running is False

    @pytest.mark.asyncio
    async def test_collect_all(self, unified_collector):
        unified_collector.snmp.add_target(SNMPTarget(host="10.0.0.1"))
        metrics = await unified_collector.collect_all()
        assert len(metrics) > 0
        assert unified_collector.collection_count == 1
        assert unified_collector.total_metrics > 0

    @pytest.mark.asyncio
    async def test_get_metrics(self, unified_collector):
        unified_collector.snmp.add_target(SNMPTarget(host="10.0.0.1"))
        await unified_collector.collect_all()
        metrics = unified_collector.get_metrics(device_id="10.0.0.1")
        assert len(metrics) > 0
