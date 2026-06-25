"""Enterprise Decision Intelligence Service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.database.intelligence import (
    DataQualityLevel,
    DecisionAction,
    DecisionSeverity,
)


class FinancialImpactAnalyzer:
    """Analyzes and computes financial impact for inventory decisions."""

    @staticmethod
    def compute_impact(
        sku: str,
        portfolio_id: str,
        current_stock: float,
        demand_forecast: float,
        forecast_accuracy: float,
        daily_sales_rate: float,
        unit_cost: float,
        retail_price: float,
        lead_time_days: int,
        safety_stock: float,
        reorder_point: float,
        carrying_cost_pct: float = 0.25,
        stockout_cost_multiplier: float = 2.5,
    ) -> Dict[str, Any]:
        """
        Compute comprehensive financial impact metrics.

        Returns:
            Dictionary with financial metrics, risk assessment, and recommendations
        """
        # Days of cover
        daily_usage = daily_sales_rate
        days_of_cover = current_stock / daily_usage if daily_usage > 0 else 999

        # Revenue at risk (stockout scenario)
        inventory_gap = max(0, demand_forecast - current_stock)
        revenue_at_risk = inventory_gap * retail_price if inventory_gap > 0 else 0

        # Carrying costs (overstock scenario)
        excess_stock = max(0, current_stock - demand_forecast - safety_stock)
        annual_carrying_cost = excess_stock * unit_cost * carrying_cost_pct

        # Stockout cost
        stockout_probability = max(0, min(1, 1 - (forecast_accuracy / 100)))
        potential_stockout_impact = inventory_gap * retail_price * stockout_probability

        # Reorder recommendation
        optimal_order_qty = demand_forecast + safety_stock - current_stock

        # Action determination
        severity = DecisionSeverity.LOW.value
        action = DecisionAction.MONITOR.value
        urgency_score = 0.0
        impact_drivers = {}
        risk_factors = {}

        if days_of_cover < 7:
            severity = DecisionSeverity.CRITICAL.value
            action = DecisionAction.ORDER_NOW.value
            urgency_score = 0.95
            impact_drivers["stockout_imminent"] = True
            risk_factors["low_days_of_cover"] = days_of_cover
        elif days_of_cover < 14:
            severity = DecisionSeverity.HIGH.value
            action = (
                DecisionAction.INCREASE_ORDER.value
                if optimal_order_qty > 0
                else DecisionAction.HOLD.value
            )
            urgency_score = 0.75
            impact_drivers["stockout_approaching"] = True
            risk_factors["medium_days_of_cover"] = days_of_cover
        elif excess_stock > (demand_forecast * 0.5):
            severity = DecisionSeverity.HIGH.value
            action = (
                DecisionAction.REDUCE_ORDER.value
                if inventory_gap < 0
                else DecisionAction.LIQUIDATE.value
            )
            urgency_score = 0.70
            impact_drivers["excess_inventory"] = True
            risk_factors["excess_pct"] = (
                excess_stock / current_stock if current_stock > 0 else 0
            )
        elif revenue_at_risk > (
            retail_price * daily_usage * 5
        ):  # >5 days potential lost sales
            severity = DecisionSeverity.MEDIUM.value
            action = DecisionAction.INCREASE_ORDER.value
            urgency_score = 0.60
            impact_drivers["revenue_exposure"] = True
            risk_factors["revenue_at_risk"] = revenue_at_risk

        # Confidence interval
        forecast_std = demand_forecast * (1 - forecast_accuracy / 100)
        confidence_interval = {
            "lower_95": max(0, demand_forecast - 1.96 * forecast_std),
            "upper_95": demand_forecast + 1.96 * forecast_std,
            "cv": forecast_std / demand_forecast if demand_forecast > 0 else 0,
        }

        potential_savings = 0.0
        potential_loss = 0.0

        if (
            action == DecisionAction.ORDER_NOW.value
            or action == DecisionAction.INCREASE_ORDER.value
        ):
            potential_loss = revenue_at_risk
        elif (
            action == DecisionAction.REDUCE_ORDER.value
            or action == DecisionAction.LIQUIDATE.value
        ):
            potential_savings = annual_carrying_cost

        return {
            "revenue_at_risk": revenue_at_risk,
            "potential_loss": potential_loss,
            "potential_savings": potential_savings,
            "inventory_carrying_cost": annual_carrying_cost,
            "stockout_cost": potential_stockout_impact,
            "days_of_cover": days_of_cover,
            "optimal_order_qty": max(0, optimal_order_qty),
            "inventory_gap": inventory_gap,
            "excess_stock": excess_stock,
            "severity": severity,
            "action": action,
            "urgency_score": urgency_score,
            "impact_drivers": impact_drivers,
            "risk_factors": risk_factors,
            "confidence_interval": confidence_interval,
        }


class DecisionFeedGenerator:
    """Generates action-oriented decision feed items."""

    SEVERITY_PRIORITY = {
        DecisionSeverity.CRITICAL.value: 1,
        DecisionSeverity.HIGH.value: 2,
        DecisionSeverity.MEDIUM.value: 3,
        DecisionSeverity.LOW.value: 4,
    }

    @classmethod
    def generate_feed_item(
        cls,
        financial_impact: Dict[str, Any],
        sku: str,
        portfolio_id: str,
        sku_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a feed item from financial impact analysis."""

        action = financial_impact["action"]
        severity = financial_impact["severity"]
        revenue_at_risk = financial_impact["revenue_at_risk"]
        potential_savings = financial_impact["potential_savings"]

        title = cls._generate_title(action, sku, severity)
        description = cls._generate_description(financial_impact, sku_profile or {})

        estimated_time_min, estimated_time_max = cls._estimate_execution_time(action)
        effort_points = cls._estimate_effort(action, severity)

        impact_type = None
        financial_impact_val = 0.0
        if revenue_at_risk > 0:
            impact_type = "revenue_risk"
            financial_impact_val = revenue_at_risk
        elif potential_savings > 0:
            impact_type = "cost_reduction"
            financial_impact_val = potential_savings

        related_skus = []
        if sku_profile:
            related_skus = sku_profile.get("related_products", [])[:3]

        return {
            "title": title,
            "description": description,
            "action_required": action,
            "sku": sku,
            "severity": severity,
            "financial_impact": financial_impact_val,
            "impact_type": impact_type,
            "estimated_execution_time_min": estimated_time_min,
            "estimated_execution_time_max": estimated_time_max,
            "estimated_effort_points": effort_points,
            "supporting_data": financial_impact,
            "related_skus": related_skus,
        }

    @staticmethod
    def _generate_title(action: str, sku: str, severity: str) -> str:
        action_text = {
            DecisionAction.ORDER_NOW.value: "🔴 Order Now",
            DecisionAction.INCREASE_ORDER.value: "🟠 Increase Order",
            DecisionAction.HOLD.value: "🟡 Hold Orders",
            DecisionAction.REDUCE_ORDER.value: "🔵 Reduce Orders",
            DecisionAction.LIQUIDATE.value: "❌ Liquidate Excess",
            DecisionAction.MONITOR.value: "👁️ Monitor",
        }
        return f"{action_text.get(action, action)} — {sku}"

    @staticmethod
    def _generate_description(
        financial_impact: Dict[str, Any], sku_profile: Dict[str, Any]
    ) -> str:
        days = financial_impact["days_of_cover"]
        action = financial_impact["action"]

        descriptions = {
            DecisionAction.ORDER_NOW.value: (
                f"Stock running critically low with only {days:.1f} days remaining. "
                f"Imminent stockout risk. Revenue exposure: ₹{financial_impact['revenue_at_risk']:,.0f}. "
                f"Action: Order {financial_impact['optimal_order_qty']:.0f} units immediately."
            ),
            DecisionAction.INCREASE_ORDER.value: (
                f"Current stock ({days:.1f} days) approaching reorder threshold. "
                f"Forecast shows strong demand ahead. Recommend increasing order by "
                f"{financial_impact['optimal_order_qty']:.0f} units to prevent stockout."
            ),
            DecisionAction.HOLD.value: (
                f"Stock levels adequate with {days:.1f} days of cover. "
                f"Pause new orders to avoid excess inventory."
            ),
            DecisionAction.REDUCE_ORDER.value: (
                f"Excess inventory detected with {days:.1f} days of cover vs {financial_impact.get('expected_days', 14)} expected. "
                f"Potential carrying cost: ₹{financial_impact['inventory_carrying_cost']:,.0f}/year. "
                f"Recommend reducing order quantity by 30-50%."
            ),
            DecisionAction.LIQUIDATE.value: (
                f"Significant overstock: {financial_impact['excess_stock']:.0f} excess units. "
                f"Annual carrying cost: ₹{financial_impact['inventory_carrying_cost']:,.0f}. "
                f"Consider promotional pricing or clearance to reduce holding costs."
            ),
        }

        return descriptions.get(
            action,
            f"Inventory decision required for {sku_profile.get('sku_name', 'SKU')}",
        )

    @staticmethod
    def _estimate_execution_time(action: str) -> Tuple[float, float]:
        times = {
            DecisionAction.ORDER_NOW.value: (0.25, 0.5),  # 15-30 min
            DecisionAction.INCREASE_ORDER.value: (0.5, 1.0),  # 30-60 min
            DecisionAction.REDUCE_ORDER.value: (1.0, 2.0),  # 1-2 hours
            DecisionAction.LIQUIDATE.value: (4.0, 8.0),  # 4-8 hours
            DecisionAction.MONITOR.value: (0.1, 0.2),  # 5-10 min
        }
        return times.get(action, (1.0, 2.0))

    @staticmethod
    def _estimate_effort(action: str, severity: str) -> float:
        base_effort = {
            DecisionAction.ORDER_NOW.value: 5.0,
            DecisionAction.INCREASE_ORDER.value: 3.0,
            DecisionAction.REDUCE_ORDER.value: 3.0,
            DecisionAction.LIQUIDATE.value: 8.0,
            DecisionAction.MONITOR.value: 1.0,
        }

        severity_multiplier = {
            DecisionSeverity.CRITICAL.value: 1.5,
            DecisionSeverity.HIGH.value: 1.25,
            DecisionSeverity.MEDIUM.value: 1.0,
            DecisionSeverity.LOW.value: 0.75,
        }

        return base_effort.get(action, 3.0) * severity_multiplier.get(severity, 1.0)


class SKUIntelligenceEngine:
    """Deep SKU analysis and profiling."""

    @staticmethod
    def build_sku_profile(
        sku: str,
        portfolio_id: str,
        sales_data: pd.DataFrame,
        forecast_data: Dict[str, Any],
        inventory_data: Dict[str, float],
        financial_data: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Build comprehensive SKU intelligence profile.

        Args:
            sales_data: DataFrame with columns ['date', 'quantity', 'price', 'cost']
            forecast_data: Dict with forecast metrics
            inventory_data: Dict with current stock, lead time, MOQ, etc
            financial_data: Dict with margins, costs
        """

        # Classification
        total_revenue = (sales_data["quantity"] * sales_data["price"]).sum()
        avg_daily_sales = sales_data["quantity"].mean()

        # 12-month statistics (if available)
        annual_revenue = (
            total_revenue
            if len(sales_data) >= 365
            else total_revenue * (365 / len(sales_data))
        )

        # Revenue tier
        revenue_contributor = "niche"
        if annual_revenue > 500000:
            revenue_contributor = "top_tier"
        elif annual_revenue > 100000:
            revenue_contributor = "growth"
        elif annual_revenue < 10000:
            revenue_contributor = "declining"

        # Inventory classification (ABC)
        inventory_class = "C"
        if annual_revenue > 500000:
            inventory_class = "A"
        elif annual_revenue > 100000:
            inventory_class = "B"

        # Demand pattern
        quantities = sales_data["quantity"].values
        cv = np.std(quantities) / np.mean(quantities) if np.mean(quantities) > 0 else 0

        if cv > 1.0:
            demand_pattern = "volatile"
        elif cv > 0.5:
            demand_pattern = "trending"
        else:
            demand_pattern = "steady"

        # Check seasonality
        if len(sales_data) >= 90:
            first_90 = sales_data["quantity"].iloc[:90].mean()
            last_90 = sales_data["quantity"].iloc[-90:].mean()
            if abs(first_90 - last_90) / max(first_90, last_90) > 0.3:
                demand_pattern = "seasonal"

        # Financial metrics
        gross_margin_pct = (
            (
                financial_data.get("retail_price", 100)
                - financial_data.get("unit_cost", 50)
            )
            / financial_data.get("retail_price", 100)
            * 100
        )
        margin_contribution = annual_revenue * (gross_margin_pct / 100)

        # Inventory metrics
        inventory_turnover = annual_revenue / (
            inventory_data.get("avg_inventory_value", 1) or 1
        )
        stockout_frequency = forecast_data.get("stockout_frequency_12m", 0)
        overstock_frequency = forecast_data.get("overstock_frequency_12m", 0)

        # Forecast health
        forecast_accuracy_mape = forecast_data.get("mape", 25.0)
        forecast_bias = forecast_data.get("bias", 0.0)
        forecast_volatility = forecast_data.get(
            "volatility", np.std(quantities) if len(quantities) > 0 else 0
        )

        # Data quality assessment
        missing_pct = 1 - (sales_data["quantity"].notna().sum() / len(sales_data))
        outlier_pct = SKUIntelligenceEngine._detect_outliers_pct(
            sales_data["quantity"].values
        )

        data_quality = DataQualityLevel.GOOD.value
        if missing_pct > 0.1 or outlier_pct > 0.2:
            data_quality = DataQualityLevel.FAIR.value
        elif missing_pct < 0.02 and outlier_pct < 0.05:
            data_quality = DataQualityLevel.EXCELLENT.value
        elif missing_pct > 0.2 or outlier_pct > 0.3:
            data_quality = DataQualityLevel.POOR.value

        # Demand volatility index (0-100)
        demand_vol_index = min(100, cv * 40)

        # Variance analysis
        variance_analysis = {
            "coefficient_of_variation": float(cv),
            "std_dev": float(np.std(quantities)),
            "mean_daily_sales": float(avg_daily_sales),
            "sales_min": float(np.min(quantities)),
            "sales_max": float(np.max(quantities)),
        }

        # Overall health score (0-100)
        health_components = [
            (100 - min(forecast_accuracy_mape, 100), 0.35),  # Forecast accuracy 35%
            (100 - (stockout_frequency * 10), 0.25),  # Stockout prevention 25%
            ((gross_margin_pct / 100) * 100, 0.20),  # Margin 20%
            (
                (100 - (inventory_turnover * 10)) if inventory_turnover > 0 else 50,
                0.10,
            ),  # Turnover 10%
            (
                100 if data_quality != DataQualityLevel.POOR.value else 50,
                0.10,
            ),  # Data quality 10%
        ]

        overall_health_score = sum(
            score * weight for score, weight in health_components
        )
        overall_health_score = max(0, min(100, overall_health_score))

        return {
            "sku": sku,
            "portfolio_id": portfolio_id,
            "revenue_contributor": revenue_contributor,
            "inventory_class": inventory_class,
            "demand_pattern": demand_pattern,
            "annual_revenue": annual_revenue,
            "gross_margin_pct": gross_margin_pct,
            "margin_contribution": margin_contribution,
            "avg_daily_sales": avg_daily_sales,
            "inventory_turnover": inventory_turnover,
            "stockout_frequency_12m": stockout_frequency,
            "overstock_frequency_12m": overstock_frequency,
            "forecast_accuracy_mape": forecast_accuracy_mape,
            "forecast_bias": forecast_bias,
            "forecast_volatility": forecast_volatility,
            "data_quality_level": data_quality,
            "demand_volatility_index": demand_vol_index,
            "overall_health_score": overall_health_score,
            "variance_analysis": variance_analysis,
        }

    @staticmethod
    def _detect_outliers_pct(data: np.ndarray) -> float:
        """Detect outliers using IQR method."""
        if len(data) < 4:
            return 0.0
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers = np.sum((data < lower_bound) | (data > upper_bound))
        return outliers / len(data)


class RevenueAtRiskAnalyzer:
    """Portfolio-level revenue at risk analysis."""

    @staticmethod
    def compute_portfolio_rar(
        sku_impacts: List[Dict[str, Any]],
        portfolio_id: str,
        horizon_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Compute portfolio-level revenue at risk.

        Args:
            sku_impacts: List of financial impacts for each SKU
            portfolio_id: Portfolio identifier
            horizon_days: Analysis horizon
        """

        if not sku_impacts:
            return {}

        total_revenue_at_risk = sum(si["revenue_at_risk"] for si in sku_impacts)
        total_stockout_cost = sum(si["stockout_cost"] for si in sku_impacts)
        total_carrying_cost = sum(si["inventory_carrying_cost"] for si in sku_impacts)

        skus_at_risk = sum(1 for si in sku_impacts if si["revenue_at_risk"] > 0)
        critical_stockouts = sum(1 for si in sku_impacts if si["days_of_cover"] < 7)
        excess_inventory_count = sum(1 for si in sku_impacts if si["excess_stock"] > 0)

        total_potential_mitigation = sum(
            si["potential_loss"] for si in sku_impacts
        ) + sum(si["potential_savings"] for si in sku_impacts)

        # Severity classification
        severity = DecisionSeverity.LOW.value
        if total_revenue_at_risk > 1000000:
            severity = DecisionSeverity.CRITICAL.value
        elif total_revenue_at_risk > 500000:
            severity = DecisionSeverity.HIGH.value
        elif total_revenue_at_risk > 100000:
            severity = DecisionSeverity.MEDIUM.value

        # Top risks by SKU
        top_risks = sorted(
            [
                {
                    "sku": si.get("sku", "Unknown"),
                    "revenue_at_risk": si["revenue_at_risk"],
                }
                for si in sku_impacts
            ],
            key=lambda x: x["revenue_at_risk"],
            reverse=True,
        )[:10]

        # Risk by category (if available)
        risk_by_category = {}
        for si in sku_impacts:
            category = si.get("category", "Other")
            if category not in risk_by_category:
                risk_by_category[category] = 0
            risk_by_category[category] += si["revenue_at_risk"]

        return {
            "portfolio_id": portfolio_id,
            "total_revenue_at_risk": total_revenue_at_risk,
            "total_stockout_cost": total_stockout_cost,
            "total_overstock_cost": total_carrying_cost,
            "total_opportunity_cost": total_revenue_at_risk * 0.1,  # Proxy
            "skus_at_risk": skus_at_risk,
            "critical_stockouts": critical_stockouts,
            "excess_inventory_skus": excess_inventory_count,
            "severity": severity,
            "potential_mitigation_revenue": total_potential_mitigation,
            "recommended_actions_count": len(
                [
                    si
                    for si in sku_impacts
                    if si["action"] != DecisionAction.MONITOR.value
                ]
            ),
            "top_risks": top_risks,
            "risk_by_category": risk_by_category,
            "horizon_days": horizon_days,
        }


class DataQualityMonitor:
    """Monitors and reports on data quality."""

    @staticmethod
    def assess_quality(df: pd.DataFrame, sku: str = None) -> Dict[str, Any]:
        """Assess data quality of a dataset."""

        total_records = len(df)

        # Completeness
        missing_count = df.isnull().sum().sum()
        missing_pct = (missing_count / (len(df) * len(df.columns))) * 100
        valid_records = total_records - int(df.isnull().any(axis=1).sum())

        # Duplicates
        duplicate_count = df.duplicated().sum()

        # Outliers (numeric columns)
        outlier_count = 0
        for col in df.select_dtypes(include=[np.number]).columns:
            outliers = DataQualityMonitor._detect_outliers(df[col].values)
            outlier_count += outliers

        # Consistency checks
        consistency_score = 100
        if missing_pct > 5:
            consistency_score -= 20
        if duplicate_count > total_records * 0.01:
            consistency_score -= 15
        if outlier_count > total_records * 0.05:
            consistency_score -= 15

        consistency_score = max(0, consistency_score)

        # Completeness score
        completeness = 100 - missing_pct

        # Overall score
        overall_score = (completeness * 0.35) + (consistency_score * 0.65)
        overall_score = max(0, min(100, overall_score))

        # Field-level scores
        field_scores = {}
        for col in df.columns:
            null_pct = (df[col].isnull().sum() / len(df)) * 100
            field_scores[col] = 100 - null_pct

        # Issues and warnings
        issues = []
        if missing_pct > 10:
            issues.append(f"High missing data: {missing_pct:.1f}%")
        if duplicate_count > 0:
            issues.append(f"Duplicates found: {duplicate_count} records")
        if outlier_count > total_records * 0.1:
            issues.append(f"High outliers: {outlier_count} data points")

        return {
            "overall_quality_score": overall_score,
            "completeness_pct": completeness,
            "consistency_score": consistency_score,
            "total_records": total_records,
            "valid_records": valid_records,
            "invalid_records": total_records - valid_records,
            "missing_values": int(missing_count),
            "duplicate_records": int(duplicate_count),
            "outliers_detected": int(outlier_count),
            "field_scores": field_scores,
            "issues": issues,
        }

    @staticmethod
    def _detect_outliers(data: np.ndarray) -> int:
        """Count outliers using IQR method."""
        if len(data) < 4:
            return 0
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1
        if iqr == 0:
            return 0
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        return int(np.sum((data < lower) | (data > upper)))
