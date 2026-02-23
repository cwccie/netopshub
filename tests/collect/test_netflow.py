"""Tests for NetFlow receiver."""

import pytest
from netopshub.collect.netflow import NetFlowReceiver


class TestNetFlowReceiver:
    @pytest.mark.asyncio
    async def test_start_stop(self, netflow_receiver):
        await netflow_receiver.start()
        assert netflow_receiver.flow_count > 0
        await netflow_receiver.stop()

    @pytest.mark.asyncio
    async def test_demo_flows_generated(self, netflow_receiver):
        await netflow_receiver.start()
        assert netflow_receiver.flow_count == 500
        assert netflow_receiver.total_received == 500

    @pytest.mark.asyncio
    async def test_get_flows(self, netflow_receiver):
        await netflow_receiver.start()
        flows = netflow_receiver.get_flows(limit=10)
        assert len(flows) == 10

    @pytest.mark.asyncio
    async def test_aggregate(self, netflow_receiver):
        await netflow_receiver.start()
        agg = netflow_receiver.aggregate(period_minutes=120)
        assert agg.total_flows > 0
        assert agg.total_bytes > 0
        assert agg.total_packets > 0

    @pytest.mark.asyncio
    async def test_top_talkers(self, netflow_receiver):
        await netflow_receiver.start()
        talkers = netflow_receiver.get_top_talkers(n=5)
        assert len(talkers) <= 5
        assert all("address" in t for t in talkers)

    @pytest.mark.asyncio
    async def test_filter_by_src(self, netflow_receiver):
        await netflow_receiver.start()
        flows = netflow_receiver.get_flows()
        if flows:
            src = flows[0].src_addr
            filtered = netflow_receiver.get_flows(src_addr=src)
            assert all(f.src_addr == src for f in filtered)
