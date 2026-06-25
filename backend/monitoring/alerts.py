from __future__ import annotations

from typing import Dict, List


class AlertEngine:
    """Rule-based alert generation for inventory and forecasting events."""

    def evaluate_risk(self, payload: Dict) -> List[Dict]:
        alerts = []
        risk = payload.get("risk", {}).get("risk", "LOW")

        if risk == "CRITICAL":
            alerts.append(
                {
                    "severity": "critical",
                    "type": "stockout",
                    "message": "Immediate replenishment required — stockout imminent.",
                }
            )
        elif risk == "HIGH":
            alerts.append(
                {
                    "severity": "high",
                    "type": "stockout",
                    "message": "Stockout risk detected — place reorder within 3 days.",
                }
            )

        return alerts

    def evaluate_forecast_accuracy(self, mape: float) -> List[Dict]:
        alerts = []
        if mape > 30:
            alerts.append(
                {
                    "severity": "high",
                    "type": "model_drift",
                    "message": f"Forecast MAPE is {mape:.1f}% — model retraining recommended.",
                }
            )
        elif mape > 20:
            alerts.append(
                {
                    "severity": "medium",
                    "type": "model_accuracy",
                    "message": f"Forecast MAPE is {mape:.1f}% — monitor closely.",
                }
            )
        return alerts

    def evaluate_inventory_health(self, health_score: float) -> List[Dict]:
        alerts = []
        if health_score < 40:
            alerts.append(
                {
                    "severity": "critical",
                    "type": "inventory_health",
                    "message": f"Inventory health is critically low at {health_score:.0f}%.",
                }
            )
        elif health_score < 60:
            alerts.append(
                {
                    "severity": "high",
                    "type": "inventory_health",
                    "message": f"Inventory health is low at {health_score:.0f}%.",
                }
            )
        return alerts


alert_engine = AlertEngine()
