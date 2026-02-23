"""Health monitoring engine for network devices.

Tracks CPU, memory, bandwidth, error rates, and environmental metrics,
with configurable thresholds and trend analysis.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from netopshub.models import (
    Alert,
    AlertSeverity,
    AlertState,
    Metric,
    MetricThreshold,
    MetricType,
)

logger = logging.getLogger(__name__)


# Default thresholds
DEFAULT_THRESHOLDS: list[MetricThreshold] = [
    MetricThreshold(
        metric_type=MetricType.CPU,
        warning_threshold=70.0,
        critical_threshold=85.0,
        emergency_threshold=95.0,
    ),
    MetricThreshold(
        metric_type=MetricType.MEMORY,
        warning_threshold=75.0,
        critical_threshold=90.0,
        emergency_threshold=97.0,
    ),
    MetricThreshold(
        metric_type=MetricType.ERROR_RATE,
        warning_threshold=1.0,
        critical_threshold=5.0,
        emergency_threshold=10.0,
    ),
    MetricThreshold(
        metric_type=MetricType.TEMPERATURE,
        warning_threshold=65.0,
        critical_threshold=75.0,
        emergency_threshold=85.0,
    ),
    MetricThreshold(
        metric_type=MetricType.PACKET_LOSS,
        warning_threshold=0.5,
        critical_threshold=2.0,
        emergency_threshold=5.0,
    ),
]


class HealthMonitor:
    """Monitors device health metrics and generates alerts on threshold violations.

    Maintains a rolling window of metrics for each device and metric type,
    supports configurable thresholds, and provides trend analysis.
    """

    def __init__(self, thresholds: Optional[list[MetricThreshold]] = None):
        self._thresholds = {t.metric_type: t for t in (thresholds or DEFAULT_THRESHOLDS)}
        self._metric_history: dict[str, list[Metric]] = defaultdict(list)
        self._alerts: list[Alert] = []
        self._max_history = 1000

    def process_metrics(self, metrics: list[Metric]) -> list[Alert]:
        """Process a batch of metrics and check thresholds.

        Returns any alerts generated from threshold violations.
        """
        new_alerts: list[Alert] = []
        for metric in metrics:
            key = f"{metric.device_id}:{metric.metric_type.value}"
            self._metric_history[key].append(metric)
            # Trim history
            if len(self._metric_history[key]) > self._max_history:
                self._metric_history[key] = self._metric_history[key][-self._max_history:]

            # Check thresholds
            alert = self._check_threshold(metric)
            if alert:
                new_alerts.append(alert)
                self._alerts.append(alert)

        return new_alerts

    def get_device_health(self, device_id: str) -> dict[str, Any]:
        """Get current health summary for a device."""
        health: dict[str, Any] = {
            "device_id": device_id,
            "metrics": {},
            "status": "healthy",
            "active_alerts": 0,
        }

        for key, history in self._metric_history.items():
            if not key.startswith(f"{device_id}:"):
                continue
            metric_type = key.split(":")[1]
            if not history:
                continue
            latest = history[-1]
            values = [m.value for m in history[-60:]]  # Last 60 samples

            health["metrics"][metric_type] = {
                "current": latest.value,
                "unit": latest.unit,
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(statistics.mean(values), 2),
                "stddev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
                "trend": self._calculate_trend(values),
                "timestamp": latest.timestamp.isoformat(),
            }

        # Determine overall status from active alerts
        device_alerts = [
            a for a in self._alerts
            if a.device_id == device_id and a.state == AlertState.ACTIVE
        ]
        health["active_alerts"] = len(device_alerts)
        if any(a.severity == AlertSeverity.EMERGENCY for a in device_alerts):
            health["status"] = "emergency"
        elif any(a.severity == AlertSeverity.CRITICAL for a in device_alerts):
            health["status"] = "critical"
        elif any(a.severity == AlertSeverity.WARNING for a in device_alerts):
            health["status"] = "warning"

        return health

    def get_metric_history(
        self,
        device_id: str,
        metric_type: MetricType,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get metric history for a device and metric type."""
        key = f"{device_id}:{metric_type.value}"
        history = self._metric_history.get(key, [])[-limit:]
        return [
            {
                "value": m.value,
                "unit": m.unit,
                "timestamp": m.timestamp.isoformat(),
                "interface": m.interface_name,
            }
            for m in history
        ]

    def set_threshold(self, threshold: MetricThreshold) -> None:
        """Set or update a threshold."""
        self._thresholds[threshold.metric_type] = threshold

    def get_thresholds(self) -> list[MetricThreshold]:
        """Get all configured thresholds."""
        return list(self._thresholds.values())

    def _check_threshold(self, metric: Metric) -> Optional[Alert]:
        """Check if a metric violates its threshold."""
        threshold = self._thresholds.get(metric.metric_type)
        if not threshold:
            return None

        value = metric.value
        severity = None
        threshold_value = None

        if threshold.emergency_threshold and value >= threshold.emergency_threshold:
            severity = AlertSeverity.EMERGENCY
            threshold_value = threshold.emergency_threshold
        elif value >= threshold.critical_threshold:
            severity = AlertSeverity.CRITICAL
            threshold_value = threshold.critical_threshold
        elif value >= threshold.warning_threshold:
            severity = AlertSeverity.WARNING
            threshold_value = threshold.warning_threshold

        if severity:
            return Alert(
                device_id=metric.device_id,
                device_hostname=metric.device_hostname,
                interface_name=metric.interface_name,
                severity=severity,
                title=f"{metric.metric_type.value.upper()} threshold exceeded on {metric.device_hostname or metric.device_id}",
                description=(
                    f"{metric.metric_type.value} is {value}{metric.unit}, "
                    f"exceeding {severity.value} threshold of {threshold_value}{metric.unit}"
                ),
                metric_type=metric.metric_type,
                metric_value=value,
                threshold_value=threshold_value,
                source="health_monitor",
            )
        return None

    def _calculate_trend(self, values: list[float]) -> str:
        """Calculate trend direction from a series of values."""
        if len(values) < 3:
            return "stable"
        recent = statistics.mean(values[-5:]) if len(values) >= 5 else values[-1]
        older = statistics.mean(values[:5])
        diff = recent - older
        if diff > older * 0.1:
            return "increasing"
        elif diff < -older * 0.1:
            return "decreasing"
        return "stable"

    @property
    def alert_count(self) -> int:
        return len(self._alerts)

    @property
    def active_alert_count(self) -> int:
        return len([a for a in self._alerts if a.state == AlertState.ACTIVE])
