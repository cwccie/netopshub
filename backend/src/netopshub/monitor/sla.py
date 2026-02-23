"""SLA monitoring — tracks latency, jitter, packet loss against defined baselines."""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Optional

from netopshub.models import Metric, MetricType, SLAReport, SLATarget

logger = logging.getLogger(__name__)


DEFAULT_SLA_TARGETS = [
    SLATarget(
        name="Network Latency",
        description="Round-trip latency must stay under 50ms",
        metric_type=MetricType.LATENCY,
        target_value=50.0,
        comparison="lt",
        measurement_window="24h",
    ),
    SLATarget(
        name="Packet Loss",
        description="Packet loss must stay under 0.1%",
        metric_type=MetricType.PACKET_LOSS,
        target_value=0.1,
        comparison="lt",
        measurement_window="24h",
    ),
    SLATarget(
        name="Network Jitter",
        description="Jitter must stay under 10ms",
        metric_type=MetricType.JITTER,
        target_value=10.0,
        comparison="lt",
        measurement_window="24h",
    ),
    SLATarget(
        name="CPU Utilization",
        description="Average CPU must stay under 80%",
        metric_type=MetricType.CPU,
        target_value=80.0,
        comparison="lt",
        measurement_window="24h",
    ),
]


class SLAMonitor:
    """Monitors SLA compliance across defined targets.

    Evaluates metric data against SLA targets and generates
    compliance reports.
    """

    def __init__(self, targets: Optional[list[SLATarget]] = None):
        self._targets = targets or DEFAULT_SLA_TARGETS
        self._metric_data: dict[str, list[float]] = {}

    def add_target(self, target: SLATarget) -> None:
        """Add an SLA target."""
        self._targets.append(target)

    def process_metrics(self, metrics: list[Metric]) -> None:
        """Ingest metrics for SLA evaluation."""
        for metric in metrics:
            key = f"{metric.device_id}:{metric.metric_type.value}"
            if key not in self._metric_data:
                self._metric_data[key] = []
            self._metric_data[key].append(metric.value)
            # Keep only last 1440 samples (24h at 1/min)
            if len(self._metric_data[key]) > 1440:
                self._metric_data[key] = self._metric_data[key][-1440:]

    def evaluate(self, device_id: Optional[str] = None) -> list[SLAReport]:
        """Evaluate all SLA targets and return reports."""
        reports: list[SLAReport] = []
        now = datetime.utcnow()

        for target in self._targets:
            # Find matching metric data
            matching_keys = [
                k for k in self._metric_data
                if k.endswith(f":{target.metric_type.value}")
                and (device_id is None or k.startswith(f"{device_id}:"))
            ]

            all_values: list[float] = []
            for key in matching_keys:
                all_values.extend(self._metric_data[key])

            if not all_values:
                reports.append(SLAReport(
                    target=target,
                    current_value=0.0,
                    is_met=True,
                    compliance_percentage=100.0,
                    measurement_period_start=now - timedelta(hours=24),
                    measurement_period_end=now,
                ))
                continue

            current = statistics.mean(all_values[-10:]) if len(all_values) >= 10 else all_values[-1]

            if target.comparison == "lt":
                violations = sum(1 for v in all_values if v >= target.target_value)
                is_met = current < target.target_value
            else:
                violations = sum(1 for v in all_values if v <= target.target_value)
                is_met = current > target.target_value

            compliance = ((len(all_values) - violations) / len(all_values)) * 100 if all_values else 100.0

            reports.append(SLAReport(
                target=target,
                current_value=round(current, 2),
                is_met=is_met,
                compliance_percentage=round(compliance, 2),
                measurement_period_start=now - timedelta(hours=24),
                measurement_period_end=now,
                violations=violations,
            ))

        return reports

    def get_compliance_summary(self) -> dict[str, Any]:
        """Get overall SLA compliance summary."""
        reports = self.evaluate()
        total = len(reports)
        met = sum(1 for r in reports if r.is_met)
        return {
            "total_targets": total,
            "targets_met": met,
            "targets_violated": total - met,
            "overall_compliance": round((met / total) * 100, 1) if total else 100.0,
            "reports": [
                {
                    "name": r.target.name,
                    "is_met": r.is_met,
                    "current": r.current_value,
                    "target": r.target.target_value,
                    "compliance": r.compliance_percentage,
                }
                for r in reports
            ],
        }

    @property
    def target_count(self) -> int:
        return len(self._targets)
