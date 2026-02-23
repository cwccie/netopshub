"""Forecast Agent — capacity and failure prediction.

Uses time-series analysis to predict bandwidth exhaustion,
capacity limits, and potential failures.
"""

from __future__ import annotations

import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import Any, Optional

from netopshub.agents.base import BaseAgent
from netopshub.models import AgentTask, MetricType

logger = logging.getLogger(__name__)


class ForecastAgent(BaseAgent):
    """Predicts capacity exhaustion and potential failures.

    Uses linear regression and simple time-series analysis to forecast
    when metrics will exceed thresholds.
    """

    def __init__(self, demo_mode: bool = True):
        super().__init__(
            name="forecast",
            description="Capacity planning and failure prediction",
        )
        self.demo_mode = demo_mode

    async def process(self, task: AgentTask) -> AgentTask:
        """Process a forecast task."""
        task.status = "running"

        try:
            if task.task_type == "predict_capacity":
                data = task.input_data.get("metric_history", [])
                threshold = task.input_data.get("threshold", 90.0)
                forecast = self.predict_threshold_breach(data, threshold)
                return self._complete_task(task, forecast)

            elif task.task_type == "trend_analysis":
                data = task.input_data.get("metric_history", [])
                analysis = self.analyze_trend(data)
                return self._complete_task(task, analysis)

            else:
                return self._fail_task(task, f"Unknown task type: {task.task_type}")

        except Exception as e:
            return self._fail_task(task, str(e))

    async def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Handle forecast chat queries."""
        self.log_message("user", message)
        msg_lower = message.lower()

        if "bandwidth" in msg_lower or "capacity" in msg_lower:
            response = self._forecast_bandwidth()
        elif "cpu" in msg_lower or "memory" in msg_lower:
            response = self._forecast_resources()
        elif "predict" in msg_lower or "forecast" in msg_lower:
            response = self._general_forecast()
        else:
            response = (
                "I can predict capacity exhaustion and potential failures.\n\n"
                "Try asking:\n"
                "- 'When will bandwidth run out?'\n"
                "- 'Predict CPU capacity for router-core-1'\n"
                "- 'Show me the trend forecast'"
            )

        self.log_message("assistant", response)
        return response

    def predict_threshold_breach(
        self,
        values: list[float],
        threshold: float,
        interval_seconds: int = 60,
    ) -> dict[str, Any]:
        """Predict when a metric will breach a threshold.

        Uses linear regression on the most recent data points.
        """
        if len(values) < 3:
            return {
                "prediction": "insufficient_data",
                "message": "Need at least 3 data points for prediction",
            }

        n = len(values)
        x = list(range(n))
        slope, intercept = self._linear_regression(x, values)

        if slope <= 0:
            return {
                "prediction": "no_breach",
                "slope": round(slope, 6),
                "current_value": round(values[-1], 2),
                "threshold": threshold,
                "trend": "decreasing" if slope < 0 else "stable",
                "message": f"Metric is {'decreasing' if slope < 0 else 'stable'}, no breach predicted",
            }

        # Calculate when threshold will be reached
        if slope > 0:
            steps_to_breach = (threshold - values[-1]) / slope
            seconds_to_breach = steps_to_breach * interval_seconds
            breach_time = datetime.utcnow() + timedelta(seconds=max(0, seconds_to_breach))

            return {
                "prediction": "breach_predicted",
                "current_value": round(values[-1], 2),
                "threshold": threshold,
                "slope_per_interval": round(slope, 6),
                "estimated_breach_time": breach_time.isoformat(),
                "time_to_breach_hours": round(seconds_to_breach / 3600, 1),
                "confidence": self._calculate_confidence(x, values, slope, intercept),
                "message": f"Threshold of {threshold} predicted to be reached in {round(seconds_to_breach / 3600, 1)} hours",
            }

        return {"prediction": "stable", "message": "No breach predicted"}

    def analyze_trend(self, values: list[float]) -> dict[str, Any]:
        """Analyze trend direction and strength."""
        if len(values) < 3:
            return {"trend": "unknown", "message": "Insufficient data"}

        n = len(values)
        x = list(range(n))
        slope, intercept = self._linear_regression(x, values)

        avg = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0

        # Detect seasonality (simple check for periodicity)
        has_seasonality = self._detect_seasonality(values)

        if abs(slope) < std * 0.01:
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        return {
            "trend": trend,
            "slope": round(slope, 6),
            "mean": round(avg, 2),
            "std_dev": round(std, 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "has_seasonality": has_seasonality,
            "data_points": n,
        }

    def _linear_regression(self, x: list[float], y: list[float]) -> tuple[float, float]:
        """Simple linear regression returning (slope, intercept)."""
        n = len(x)
        if n == 0:
            return 0.0, 0.0

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)

        denom = n * sum_x2 - sum_x ** 2
        if denom == 0:
            return 0.0, sum_y / n if n else 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        return slope, intercept

    def _calculate_confidence(
        self,
        x: list[float],
        y: list[float],
        slope: float,
        intercept: float,
    ) -> float:
        """Calculate R-squared as a confidence measure."""
        y_mean = statistics.mean(y)
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))

        if ss_tot == 0:
            return 1.0
        r_squared = 1 - (ss_res / ss_tot)
        return round(max(0, r_squared), 3)

    def _detect_seasonality(self, values: list[float], min_period: int = 10) -> bool:
        """Simple seasonality detection via autocorrelation."""
        if len(values) < min_period * 2:
            return False

        n = len(values)
        mean = statistics.mean(values)
        variance = sum((v - mean) ** 2 for v in values) / n

        if variance == 0:
            return False

        # Check autocorrelation at various lags
        for lag in range(min_period, n // 2):
            autocorr = sum(
                (values[i] - mean) * (values[i + lag] - mean)
                for i in range(n - lag)
            ) / ((n - lag) * variance)
            if autocorr > 0.5:
                return True
        return False

    def _forecast_bandwidth(self) -> str:
        """Generate a bandwidth forecast."""
        return (
            "**Bandwidth Capacity Forecast**\n\n"
            "**WAN Link (router-core-1 → ISP)**\n"
            "- Current utilization: 67% (670 Mbps of 1 Gbps)\n"
            "- Growth rate: +3.2% per month\n"
            "- Predicted 80% threshold: **4.1 months** (June 2026)\n"
            "- Predicted 90% threshold: **7.3 months** (September 2026)\n"
            "- Confidence: 82% (R² = 0.82)\n\n"
            "**DC Fabric (switch-dist-1 uplinks)**\n"
            "- Current utilization: 45% (4.5 Gbps of 10 Gbps)\n"
            "- Growth rate: +1.8% per month\n"
            "- Predicted 80% threshold: **19.4 months** (October 2027)\n"
            "- Confidence: 74%\n\n"
            "**Recommendation:** Plan WAN bandwidth upgrade to 2 Gbps "
            "within the next quarter to avoid congestion."
        )

    def _forecast_resources(self) -> str:
        """Generate a resource forecast."""
        return (
            "**Resource Capacity Forecast**\n\n"
            "**router-core-1**\n"
            "- CPU: 32% avg → stable trend, no concern\n"
            "- Memory: 58% avg → increasing +0.5%/week\n"
            "- Predicted memory 80%: **44 weeks** (January 2027)\n\n"
            "**switch-dist-1**\n"
            "- CPU: 18% avg → stable\n"
            "- Memory: 42% avg → stable\n"
            "- TCAM: 67% used → increasing +2 entries/day\n"
            "- Predicted TCAM exhaustion: **6.2 months**\n\n"
            "**Recommendation:** Monitor TCAM usage on switch-dist-1; "
            "consider route summarization or hardware upgrade."
        )

    def _general_forecast(self) -> str:
        """Generate a general forecast summary."""
        return (
            "**Network Forecast Summary**\n\n"
            "| Resource | Status | Time to Critical |\n"
            "|----------|--------|------------------|\n"
            "| WAN Bandwidth | Warning | 4.1 months |\n"
            "| DC Fabric Bandwidth | OK | 19+ months |\n"
            "| Router CPU | OK | No trend |\n"
            "| Router Memory | Watch | 44 weeks |\n"
            "| Switch TCAM | Warning | 6.2 months |\n"
            "| Firewall Sessions | OK | 12+ months |\n\n"
            "**Priority Actions:**\n"
            "1. Plan WAN bandwidth upgrade (Q2 2026)\n"
            "2. Optimize TCAM usage on distribution switches\n"
            "3. Monitor router memory growth trend"
        )
