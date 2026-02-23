"""Tests for REST collector."""

import pytest
from netopshub.collect.rest_collector import RESTCollector, RESTEndpoint


class TestRESTCollector:
    def test_add_endpoint(self, rest_collector):
        ep = RESTEndpoint(name="test", base_url="http://localhost", vendor="meraki")
        rest_collector.add_endpoint(ep)
        assert rest_collector.endpoint_count == 1

    @pytest.mark.asyncio
    async def test_collect_meraki(self, rest_collector):
        ep = RESTEndpoint(name="meraki", base_url="http://api.meraki.com", vendor="meraki")
        rest_collector.add_endpoint(ep)
        metrics = await rest_collector.collect("meraki")
        assert len(metrics) > 0

    @pytest.mark.asyncio
    async def test_collect_arista(self, rest_collector):
        ep = RESTEndpoint(name="arista", base_url="http://arista.local", vendor="arista")
        rest_collector.add_endpoint(ep)
        metrics = await rest_collector.collect("arista")
        assert len(metrics) > 0

    @pytest.mark.asyncio
    async def test_collect_unknown_endpoint(self, rest_collector):
        with pytest.raises(ValueError):
            await rest_collector.collect("nonexistent")

    @pytest.mark.asyncio
    async def test_get_devices(self, rest_collector):
        ep = RESTEndpoint(name="meraki", base_url="http://api.meraki.com", vendor="meraki")
        rest_collector.add_endpoint(ep)
        devices = await rest_collector.get_devices("meraki")
        assert len(devices) > 0
