from __future__ import annotations

from typing import Dict, List


class ExecutiveAgent:
    """Generates executive-level summaries and board narratives."""

    def execute(self, sku: str, forecast: float, stock: float) -> Dict:
        coverage = stock / max(forecast, 1)
        if coverage < 0.5:
            status = "CRITICAL - Immediate action required"
            action = (
                f"Reorder {round(forecast - stock + forecast * 0.2)} units immediately"
            )
        elif coverage < 1.0:
            status = "AT RISK - Monitor closely"
            action = f"Plan reorder of {round(forecast * 0.3)} units within 7 days"
        else:
            status = "HEALTHY - On track"
            action = "Continue normal replenishment schedule"

        return {
            "sku": sku,
            "forecast": round(forecast, 2),
            "stock": round(stock, 2),
            "coverage": round(coverage, 2),
            "status": status,
            "recommended_action": action,
        }

    def board_summary(self, portfolio: List[Dict]) -> Dict:
        total_forecast = sum(p.get("forecast", 0) for p in portfolio)
        total_revenue = sum(p.get("revenue", 0) for p in portfolio)
        critical = [p for p in portfolio if p.get("risk") in ("CRITICAL", "HIGH")]

        return {
            "sku_count": len(portfolio),
            "total_forecast": round(total_forecast, 2),
            "total_revenue": round(total_revenue, 2),
            "critical_skus": len(critical),
            "critical_sku_list": [p["sku"] for p in critical],
            "health_score": round(
                (1 - len(critical) / max(len(portfolio), 1)) * 100, 1
            ),
        }

    def executive_narrative(self, summary: Dict) -> str:
        health = summary.get("health_score", 0)
        critical = summary.get("critical_skus", 0)
        skus = summary.get("sku_count", 0)
        revenue = summary.get("total_revenue", 0)

        if health >= 80:
            outlook = "strong"
        elif health >= 60:
            outlook = "moderate"
        else:
            outlook = "concerning"

        return (
            f"Portfolio health is {outlook} at {health}%. "
            f"Of {skus} active SKUs, {critical} require immediate attention. "
            f"Total forecasted revenue exposure is ₹{revenue:,.0f}. "
            f"{'Immediate replenishment action recommended for critical SKUs.' if critical > 0 else 'No critical actions required at this time.'}"
        )
