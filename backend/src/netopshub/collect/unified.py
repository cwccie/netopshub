"""Unified collector — orchestrates all collection engines.

Provides a single interface for collecting telemetry from all sources
(SNMP, NetFlow, Syslog, REST) and normalizing to the unified metric format.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from netopshub.collect.netflow import NetFlowReceiver
from netopshub.collect.rest_collector import RESTCollector
from netopshub.collect.snmp import SNMPPoller, SNMPTarget
from netopshub.collect.syslog import SyslogListener
from netopshub.models import Metric

logger = logging.getLogger(__name__)


class UnifiedCollector:
    """Orchestrates all collection engines into a unified pipeline.

    Manages lifecycle of individual collectors and provides a single
    `collect_all()` method that returns normalized metrics from all sources.
    """

    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.snmp = SNMPPoller(demo_mode=demo_mode)
        self.netflow = NetFlowReceiver(demo_mode=demo_mode)
        self.syslog = SyslogListener(demo_mode=demo_mode)
        self.rest = RESTCollector(demo_mode=demo_mode)
        self._started = False
        self._collection_count = 0
        self._all_metrics: list[Metric] = []

    async def start(self) -> None:
        """Start all collection engines."""
        await self.netflow.start()
        await self.syslog.start()
        self._started = True
        logger.info("Unified collector started (all engines active)")

    async def stop(self) -> None:
        """Stop all collection engines."""
        await self.netflow.stop()
        await self.syslog.stop()
        self._started = False
        logger.info("Unified collector stopped")

    async def collect_all(self) -> list[Metric]:
        """Collect from all sources and return unified metrics."""
        metrics: list[Metric] = []

        # SNMP polling
        try:
            snmp_metrics = await self.snmp.poll_all()
            metrics.extend(snmp_metrics)
        except Exception as e:
            logger.error(f"SNMP collection error: {e}")

        # REST API collection
        try:
            rest_metrics = await self.rest.collect_all()
            metrics.extend(rest_metrics)
        except Exception as e:
            logger.error(f"REST collection error: {e}")

        self._collection_count += 1
        self._all_metrics.extend(metrics)

        # Trim stored metrics to last 10000
        if len(self._all_metrics) > 10000:
            self._all_metrics = self._all_metrics[-10000:]

        return metrics

    def get_metrics(
        self,
        device_id: Optional[str] = None,
        metric_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> list[Metric]:
        """Query collected metrics with filters."""
        result = self._all_metrics
        if device_id:
            result = [m for m in result if m.device_id == device_id]
        if metric_type:
            result = [m for m in result if m.metric_type.value == metric_type]
        if since:
            result = [m for m in result if m.timestamp >= since]
        return result[-limit:]

    @property
    def is_running(self) -> bool:
        return self._started

    @property
    def collection_count(self) -> int:
        return self._collection_count

    @property
    def total_metrics(self) -> int:
        return len(self._all_metrics)
