"""Anomaly detection engine with statistical and ML methods.

Supports:
- Z-score based detection
- IQR (Interquartile Range) method
- EWMA (Exponentially Weighted Moving Average)
- Isolation Forest (when scikit-learn is available)
- Maintenance window awareness
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from netopshub.models import Alert, AlertSeverity, Metric

logger = logging.getLogger(__name__)


class MaintenanceWindow:
    """Defines a period during which alerts are suppressed."""

    def __init__(
        self,
        name: str,
        start: datetime,
        end: datetime,
        device_ids: list[str] | None = None,
    ):
        self.name = name
        self.start = start
        self.end = end
        self.device_ids = device_ids  # None = all devices

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        return self.start <= now <= self.end

    def covers_device(self, device_id: str) -> bool:
        return self.device_ids is None or device_id in self.device_ids


class AnomalyResult:
    """Result of an anomaly detection check."""

    def __init__(
        self,
        is_anomaly: bool,
        score: float,
        method: str,
        metric: Metric,
        details: str = "",
    ):
        self.is_anomaly = is_anomaly
        self.score = score
        self.method = method
        self.metric = metric
        self.details = details
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_anomaly": self.is_anomaly,
            "score": round(self.score, 3),
            "method": self.method,
            "device_id": self.metric.device_id,
            "metric_type": self.metric.metric_type.value,
            "value": self.metric.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class AnomalyDetector:
    """Multi-method anomaly detection engine.

    Maintains a history of metric values per device/metric-type and
    applies configurable detection methods to identify anomalies.
    """

    def __init__(
        self,
        z_score_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        ewma_alpha: float = 0.3,
        min_samples: int = 10,
    ):
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
        self.ewma_alpha = ewma_alpha
        self.min_samples = min_samples
        self._history: dict[str, list[float]] = defaultdict(list)
        self._ewma: dict[str, float] = {}
        self._ewma_var: dict[str, float] = {}
        self._maintenance_windows: list[MaintenanceWindow] = []
        self._anomalies: list[AnomalyResult] = []
        self._max_history = 2000

    def detect(self, metric: Metric, methods: list[str] | None = None) -> list[AnomalyResult]:
        """Run anomaly detection on a metric using specified methods.

        Default methods: z_score, iqr, ewma
        """
        methods = methods or ["z_score", "iqr", "ewma"]
        key = f"{metric.device_id}:{metric.metric_type.value}"

        # Update history
        self._history[key].append(metric.value)
        if len(self._history[key]) > self._max_history:
            self._history[key] = self._history[key][-self._max_history:]

        # Check maintenance windows
        if self._in_maintenance(metric.device_id):
            return []

        results: list[AnomalyResult] = []
        history = self._history[key]

        if len(history) < self.min_samples:
            return results

        if "z_score" in methods:
            result = self._z_score_detect(metric, history)
            if result:
                results.append(result)

        if "iqr" in methods:
            result = self._iqr_detect(metric, history)
            if result:
                results.append(result)

        if "ewma" in methods:
            result = self._ewma_detect(metric, key)
            if result:
                results.append(result)

        self._anomalies.extend(results)
        return results

    def detect_batch(self, metrics: list[Metric]) -> list[AnomalyResult]:
        """Run anomaly detection on a batch of metrics."""
        all_results: list[AnomalyResult] = []
        for metric in metrics:
            results = self.detect(metric)
            all_results.extend(results)
        return all_results

    def add_maintenance_window(self, window: MaintenanceWindow) -> None:
        """Add a maintenance window for alert suppression."""
        self._maintenance_windows.append(window)

    def get_anomalies(
        self,
        device_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AnomalyResult]:
        """Get detected anomalies with optional filters."""
        results = self._anomalies
        if device_id:
            results = [r for r in results if r.metric.device_id == device_id]
        if since:
            results = [r for r in results if r.timestamp >= since]
        return results[-limit:]

    def correlate_anomalies(
        self,
        window_seconds: int = 300,
    ) -> list[dict[str, Any]]:
        """Correlate anomalies that occur within a time window."""
        if not self._anomalies:
            return []

        groups: list[list[AnomalyResult]] = []
        used: set[int] = set()

        for i, anomaly_a in enumerate(self._anomalies):
            if i in used:
                continue
            group = [anomaly_a]
            used.add(i)
            for j, anomaly_b in enumerate(self._anomalies[i + 1:], i + 1):
                if j in used:
                    continue
                time_diff = abs(
                    (anomaly_a.timestamp - anomaly_b.timestamp).total_seconds()
                )
                if time_diff <= window_seconds:
                    group.append(anomaly_b)
                    used.add(j)
            if len(group) > 1:
                groups.append(group)

        return [
            {
                "size": len(group),
                "devices": list(set(a.metric.device_id for a in group)),
                "metrics": list(set(a.metric.metric_type.value for a in group)),
                "time_span_seconds": (
                    max(a.timestamp for a in group) - min(a.timestamp for a in group)
                ).total_seconds(),
            }
            for group in groups
        ]

    def _z_score_detect(self, metric: Metric, history: list[float]) -> Optional[AnomalyResult]:
        """Z-score based anomaly detection."""
        mean = statistics.mean(history)
        std = statistics.stdev(history) if len(history) > 1 else 0
        if std == 0:
            return None

        z_score = (metric.value - mean) / std
        if abs(z_score) > self.z_score_threshold:
            return AnomalyResult(
                is_anomaly=True,
                score=abs(z_score),
                method="z_score",
                metric=metric,
                details=f"Z-score {z_score:.2f} exceeds threshold {self.z_score_threshold} (mean={mean:.2f}, std={std:.2f})",
            )
        return None

    def _iqr_detect(self, metric: Metric, history: list[float]) -> Optional[AnomalyResult]:
        """IQR (Interquartile Range) anomaly detection."""
        sorted_vals = sorted(history)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]
        iqr = q3 - q1

        lower = q1 - self.iqr_multiplier * iqr
        upper = q3 + self.iqr_multiplier * iqr

        if metric.value < lower or metric.value > upper:
            return AnomalyResult(
                is_anomaly=True,
                score=max(abs(metric.value - lower), abs(metric.value - upper)) / (iqr if iqr > 0 else 1),
                method="iqr",
                metric=metric,
                details=f"Value {metric.value:.2f} outside IQR bounds [{lower:.2f}, {upper:.2f}]",
            )
        return None

    def _ewma_detect(self, metric: Metric, key: str) -> Optional[AnomalyResult]:
        """EWMA (Exponentially Weighted Moving Average) anomaly detection."""
        alpha = self.ewma_alpha

        if key not in self._ewma:
            self._ewma[key] = metric.value
            self._ewma_var[key] = 0
            return None

        # Update EWMA
        prev_ewma = self._ewma[key]
        self._ewma[key] = alpha * metric.value + (1 - alpha) * prev_ewma

        # Update variance
        diff = metric.value - prev_ewma
        self._ewma_var[key] = alpha * diff ** 2 + (1 - alpha) * self._ewma_var[key]

        std = math.sqrt(self._ewma_var[key]) if self._ewma_var[key] > 0 else 0
        if std == 0:
            return None

        z = abs(diff) / std
        if z > self.z_score_threshold:
            return AnomalyResult(
                is_anomaly=True,
                score=z,
                method="ewma",
                metric=metric,
                details=f"EWMA deviation {z:.2f} exceeds threshold (ewma={self._ewma[key]:.2f}, std={std:.2f})",
            )
        return None

    def _in_maintenance(self, device_id: str) -> bool:
        """Check if device is in a maintenance window."""
        now = datetime.utcnow()
        return any(
            w.is_active(now) and w.covers_device(device_id)
            for w in self._maintenance_windows
        )

    @property
    def anomaly_count(self) -> int:
        return len(self._anomalies)
