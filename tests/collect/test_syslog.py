"""Tests for syslog listener."""

import pytest
from netopshub.collect.syslog import SyslogListener


class TestSyslogListener:
    @pytest.mark.asyncio
    async def test_start_stop(self, syslog_listener):
        await syslog_listener.start()
        assert syslog_listener.message_count > 0
        await syslog_listener.stop()

    @pytest.mark.asyncio
    async def test_demo_messages(self, syslog_listener):
        await syslog_listener.start()
        assert syslog_listener.message_count == 200

    @pytest.mark.asyncio
    async def test_get_messages(self, syslog_listener):
        await syslog_listener.start()
        messages = syslog_listener.get_messages(limit=10)
        assert len(messages) == 10

    @pytest.mark.asyncio
    async def test_filter_by_severity(self, syslog_listener):
        await syslog_listener.start()
        critical = syslog_listener.get_messages(severity=3)
        assert all(m.severity <= 3 for m in critical)

    def test_classify_bgp_message(self, syslog_listener):
        result = syslog_listener.classify_message(
            "%BGP-5-ADJCHANGE: neighbor 10.0.0.2 Down"
        )
        assert result["category"] == "bgp_state_change"
        assert result["matched"] is True

    def test_classify_ospf_message(self, syslog_listener):
        result = syslog_listener.classify_message(
            "%OSPF-5-ADJCHG: Process 1, Nbr 10.0.1.1 on GigabitEthernet0/0 from FULL to DOWN"
        )
        assert result["category"] == "ospf_state_change"

    def test_classify_unknown_message(self, syslog_listener):
        result = syslog_listener.classify_message("Some random log message")
        assert result["category"] == "unclassified"
        assert result["matched"] is False

    @pytest.mark.asyncio
    async def test_severity_distribution(self, syslog_listener):
        await syslog_listener.start()
        dist = syslog_listener.get_severity_distribution()
        assert len(dist) > 0

    def test_parse_rfc5424(self, syslog_listener):
        raw = "<134>1 2024-01-01T00:00:00Z router-1 IOS - - Some message"
        msg = syslog_listener.parse_rfc5424(raw)
        assert msg is not None
        assert msg.device_hostname == "router-1"
        assert msg.severity == 6  # 134 & 7

    def test_parse_rfc3164(self, syslog_listener):
        raw = "<134>Jan  1 00:00:00 router-1 Some message"
        msg = syslog_listener.parse_rfc3164(raw)
        assert msg is not None
        assert msg.device_hostname == "router-1"
