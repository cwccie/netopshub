"""NetFlow v5/v9/IPFIX receiver with flow aggregation and top-talker analysis.

Receives flow data from network devices, parses flow records, and provides
aggregation functions for traffic analysis and anomaly detection.
"""

from __future__ import annotations

import logging
import random
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from netopshub.models import CollectorType, Metric, MetricType, NetFlowRecord

logger = logging.getLogger(__name__)


COMMON_PORTS = [22, 53, 80, 443, 8080, 8443, 3389, 25, 110, 143, 993, 995]
PROTOCOLS = {6: "TCP", 17: "UDP", 1: "ICMP", 47: "GRE", 50: "ESP"}


@dataclass
class FlowAggregation:
    """Aggregated flow statistics."""
    total_bytes: int = 0
    total_packets: int = 0
    total_flows: int = 0
    top_sources: list[dict[str, Any]] = field(default_factory=list)
    top_destinations: list[dict[str, Any]] = field(default_factory=list)
    top_applications: list[dict[str, Any]] = field(default_factory=list)
    protocol_distribution: dict[str, int] = field(default_factory=dict)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class NetFlowReceiver:
    """NetFlow/IPFIX receiver with flow aggregation.

    In demo mode, generates realistic flow data. In production, would bind
    to a UDP socket and parse incoming NetFlow packets.
    """

    def __init__(self, listen_port: int = 2055, demo_mode: bool = True):
        self.listen_port = listen_port
        self.demo_mode = demo_mode
        self._running = False
        self._flows: list[NetFlowRecord] = []
        self._flow_cache: dict[str, list[NetFlowRecord]] = defaultdict(list)
        self._total_received = 0

    async def start(self) -> None:
        """Start the NetFlow receiver."""
        self._running = True
        logger.info(f"NetFlow receiver started on UDP port {self.listen_port}")
        if self.demo_mode:
            self._generate_demo_flows()

    async def stop(self) -> None:
        """Stop the NetFlow receiver."""
        self._running = False
        logger.info("NetFlow receiver stopped")

    def get_flows(
        self,
        since: Optional[datetime] = None,
        src_addr: Optional[str] = None,
        dst_addr: Optional[str] = None,
        limit: int = 1000,
    ) -> list[NetFlowRecord]:
        """Query collected flows with optional filters."""
        flows = self._flows
        if since:
            flows = [f for f in flows if f.start_time >= since]
        if src_addr:
            flows = [f for f in flows if f.src_addr == src_addr]
        if dst_addr:
            flows = [f for f in flows if f.dst_addr == dst_addr]
        return flows[:limit]

    def aggregate(
        self,
        period_minutes: int = 60,
        top_n: int = 10,
    ) -> FlowAggregation:
        """Aggregate flows over a time period."""
        cutoff = datetime.utcnow() - timedelta(minutes=period_minutes)
        recent = [f for f in self._flows if f.start_time >= cutoff]

        agg = FlowAggregation(
            total_flows=len(recent),
            period_start=cutoff,
            period_end=datetime.utcnow(),
        )

        src_bytes: dict[str, int] = defaultdict(int)
        dst_bytes: dict[str, int] = defaultdict(int)
        port_bytes: dict[int, int] = defaultdict(int)
        proto_bytes: dict[str, int] = defaultdict(int)

        for flow in recent:
            agg.total_bytes += flow.bytes
            agg.total_packets += flow.packets
            src_bytes[flow.src_addr] += flow.bytes
            dst_bytes[flow.dst_addr] += flow.bytes
            port_bytes[flow.dst_port] += flow.bytes
            proto_name = PROTOCOLS.get(flow.protocol, f"proto-{flow.protocol}")
            proto_bytes[proto_name] += flow.bytes

        # Top sources
        agg.top_sources = [
            {"address": addr, "bytes": b}
            for addr, b in sorted(src_bytes.items(), key=lambda x: -x[1])[:top_n]
        ]

        # Top destinations
        agg.top_destinations = [
            {"address": addr, "bytes": b}
            for addr, b in sorted(dst_bytes.items(), key=lambda x: -x[1])[:top_n]
        ]

        # Top applications (by port)
        agg.top_applications = [
            {"port": port, "bytes": b}
            for port, b in sorted(port_bytes.items(), key=lambda x: -x[1])[:top_n]
        ]

        agg.protocol_distribution = dict(proto_bytes)
        return agg

    def get_top_talkers(self, n: int = 10) -> list[dict[str, Any]]:
        """Return top N talkers by total bytes transferred."""
        host_bytes: dict[str, int] = defaultdict(int)
        for flow in self._flows:
            host_bytes[flow.src_addr] += flow.bytes
            host_bytes[flow.dst_addr] += flow.bytes
        sorted_hosts = sorted(host_bytes.items(), key=lambda x: -x[1])[:n]
        return [{"address": addr, "total_bytes": b} for addr, b in sorted_hosts]

    def to_metrics(self, device_id: str) -> list[Metric]:
        """Convert recent flow data to unified metrics."""
        agg = self.aggregate(period_minutes=5)
        now = datetime.utcnow()
        return [
            Metric(
                device_id=device_id,
                metric_type=MetricType.BANDWIDTH_IN,
                value=round(agg.total_bytes / (5 * 60) * 8 / 1_000_000, 2),
                unit="Mbps",
                timestamp=now,
                source=CollectorType.NETFLOW,
                tags={"aggregation": "5min"},
            ),
        ]

    def _generate_demo_flows(self, count: int = 500) -> None:
        """Generate realistic demo flow data."""
        subnets = ["10.0.1", "10.0.2", "10.0.3", "172.16.1", "192.168.1"]
        external = ["8.8.8.8", "1.1.1.1", "151.101.1.69", "13.107.42.14",
                     "172.217.14.110", "104.16.249.249", "93.184.216.34"]
        now = datetime.utcnow()

        for _ in range(count):
            src_subnet = random.choice(subnets)
            src = f"{src_subnet}.{random.randint(1, 254)}"
            dst = random.choice(external) if random.random() > 0.3 else f"{random.choice(subnets)}.{random.randint(1, 254)}"
            proto = random.choices([6, 17, 1], weights=[70, 25, 5])[0]
            dst_port = random.choice(COMMON_PORTS) if proto != 1 else 0
            start = now - timedelta(minutes=random.randint(0, 60))

            flow = NetFlowRecord(
                src_addr=src,
                dst_addr=dst,
                src_port=random.randint(1024, 65535) if proto != 1 else 0,
                dst_port=dst_port,
                protocol=proto,
                bytes=random.randint(64, 15_000_000),
                packets=random.randint(1, 10000),
                start_time=start,
                end_time=start + timedelta(seconds=random.randint(1, 300)),
                input_interface=random.randint(1, 8),
                output_interface=random.randint(1, 8),
                tcp_flags=random.randint(0, 31) if proto == 6 else 0,
                exporter_ip="10.0.0.1",
            )
            self._flows.append(flow)
        self._total_received = count

    @property
    def flow_count(self) -> int:
        return len(self._flows)

    @property
    def total_received(self) -> int:
        return self._total_received
