"""REST API collector for vendor-specific APIs.

Supports polling from:
- Cisco Meraki Dashboard API
- Arista eAPI
- Palo Alto XML API
- Generic REST endpoints

Normalizes responses to the unified metric format.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any, Optional

from netopshub.models import (
    CollectorType,
    Device,
    DeviceType,
    DeviceVendor,
    Metric,
    MetricType,
)

logger = logging.getLogger(__name__)


class RESTEndpoint:
    """Configuration for a REST API endpoint."""

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        vendor: str = "generic",
        headers: Optional[dict[str, str]] = None,
        verify_ssl: bool = True,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.vendor = vendor
        self.headers = headers or {}
        self.verify_ssl = verify_ssl

        if api_key:
            if vendor == "meraki":
                self.headers["X-Cisco-Meraki-API-Key"] = api_key
            else:
                self.headers["Authorization"] = f"Bearer {api_key}"


class RESTCollector:
    """REST API collector with vendor-specific parsers.

    In demo mode, generates realistic API responses. In production,
    would use httpx/aiohttp for async HTTP requests.
    """

    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self._endpoints: dict[str, RESTEndpoint] = {}

    def add_endpoint(self, endpoint: RESTEndpoint) -> None:
        """Register a REST API endpoint."""
        self._endpoints[endpoint.name] = endpoint
        logger.info(f"Added REST endpoint: {endpoint.name} ({endpoint.vendor})")

    def remove_endpoint(self, name: str) -> None:
        """Remove a REST API endpoint."""
        self._endpoints.pop(name, None)

    async def collect(self, endpoint_name: str) -> list[Metric]:
        """Collect metrics from a specific endpoint."""
        endpoint = self._endpoints.get(endpoint_name)
        if not endpoint:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")

        if self.demo_mode:
            return self._mock_collect(endpoint)

        raise NotImplementedError("Production REST collection requires httpx")

    async def collect_all(self) -> list[Metric]:
        """Collect from all registered endpoints."""
        all_metrics: list[Metric] = []
        for name in self._endpoints:
            try:
                metrics = await self.collect(name)
                all_metrics.extend(metrics)
            except Exception as e:
                logger.error(f"REST collection error for {name}: {e}")
        return all_metrics

    async def get_devices(self, endpoint_name: str) -> list[Device]:
        """Get device inventory from a REST API."""
        endpoint = self._endpoints.get(endpoint_name)
        if not endpoint:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")

        if self.demo_mode:
            return self._mock_devices(endpoint)

        raise NotImplementedError("Production REST device query requires httpx")

    def _mock_collect(self, endpoint: RESTEndpoint) -> list[Metric]:
        """Generate mock metrics from a REST endpoint."""
        now = datetime.utcnow()
        metrics: list[Metric] = []

        if endpoint.vendor == "meraki":
            # Simulate Meraki network health metrics
            for i in range(3):
                metrics.append(Metric(
                    device_id=f"meraki-{i}",
                    device_hostname=f"meraki-ap-{i+1}",
                    metric_type=MetricType.CPU,
                    value=round(random.uniform(5, 35), 1),
                    unit="percent",
                    timestamp=now,
                    source=CollectorType.REST_API,
                    tags={"vendor": "meraki", "type": "access_point"},
                ))
        elif endpoint.vendor == "arista":
            # Simulate Arista eAPI responses
            for i in range(2):
                metrics.append(Metric(
                    device_id=f"arista-{i}",
                    device_hostname=f"arista-leaf-{i+1}",
                    metric_type=MetricType.CPU,
                    value=round(random.uniform(10, 50), 1),
                    unit="percent",
                    timestamp=now,
                    source=CollectorType.REST_API,
                    tags={"vendor": "arista"},
                ))
                metrics.append(Metric(
                    device_id=f"arista-{i}",
                    device_hostname=f"arista-leaf-{i+1}",
                    metric_type=MetricType.MEMORY,
                    value=round(random.uniform(30, 60), 1),
                    unit="percent",
                    timestamp=now,
                    source=CollectorType.REST_API,
                    tags={"vendor": "arista"},
                ))
        else:
            metrics.append(Metric(
                device_id="generic-0",
                device_hostname="generic-device",
                metric_type=MetricType.CPU,
                value=round(random.uniform(10, 70), 1),
                unit="percent",
                timestamp=now,
                source=CollectorType.REST_API,
            ))
        return metrics

    def _mock_devices(self, endpoint: RESTEndpoint) -> list[Device]:
        """Generate mock device inventory from REST API."""
        devices = []
        if endpoint.vendor == "meraki":
            for i in range(3):
                devices.append(Device(
                    hostname=f"meraki-ap-{i+1}",
                    ip_address=f"10.10.{i}.1",
                    device_type=DeviceType.ACCESS_POINT,
                    vendor=DeviceVendor.MERAKI,
                    model="MR46",
                    os_version="30.1",
                    site="main-office",
                ))
        elif endpoint.vendor == "arista":
            for i in range(2):
                devices.append(Device(
                    hostname=f"arista-leaf-{i+1}",
                    ip_address=f"10.20.{i}.1",
                    device_type=DeviceType.SWITCH,
                    vendor=DeviceVendor.ARISTA,
                    model="DCS-7050TX3-48C8",
                    os_version="EOS 4.31.1F",
                    site="datacenter-1",
                ))
        return devices

    @property
    def endpoint_count(self) -> int:
        return len(self._endpoints)
