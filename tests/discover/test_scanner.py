"""Tests for network scanner."""

import pytest
from netopshub.discover.scanner import NetworkScanner
from netopshub.models import DeviceType, DeviceVendor


class TestNetworkScanner:
    @pytest.mark.asyncio
    async def test_scan_subnet(self, scanner):
        devices = await scanner.scan_subnet("10.0.0.0/24")
        assert len(devices) > 0
        assert scanner.discovered_count > 0

    @pytest.mark.asyncio
    async def test_scan_host(self, scanner):
        device = await scanner.scan_host("10.0.0.1")
        assert device is not None
        assert device.ip_address == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_get_interface_inventory(self, scanner):
        device = await scanner.scan_host("10.0.0.1")
        interfaces = await scanner.get_interface_inventory(device)
        assert len(interfaces) > 0

    def test_identify_platform_cisco(self, scanner):
        vendor, dtype = scanner.identify_platform("Cisco IOS-XE Software, ISR4451")
        assert vendor == DeviceVendor.CISCO
        assert dtype == DeviceType.ROUTER

    def test_identify_platform_arista(self, scanner):
        vendor, dtype = scanner.identify_platform("Arista Networks EOS DCS-7280")
        assert vendor == DeviceVendor.ARISTA
        assert dtype == DeviceType.SWITCH

    def test_identify_platform_unknown(self, scanner):
        vendor, dtype = scanner.identify_platform("Unknown vendor device")
        assert vendor == DeviceVendor.UNKNOWN
