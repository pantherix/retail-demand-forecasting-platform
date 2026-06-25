"""Tests for risk scoring and ranking."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.risk.ranking import (
    PortfolioRiskRanking,
    RiskClassifier,
    RiskScoreCalculator,
)

from src.business.inventory_risk import (
    InventoryRisk,
    score_inventory_risk,
    summarize_portfolio,
)


# ── InventoryRisk (src) ───────────────────────────────────────────────────────
class TestInventoryRisk:
    def test_high_risk_when_low_stock(self):
        risk = score_inventory_risk(
            "SKU-X", [100.0] * 30, stock_on_hand=500, unit_cost=10
        )
        assert risk.risk_level == "High"

    def test_low_risk_when_well_stocked(self):
        # stock=450, 30-day forecast=300 → coverage fine, no overstock trigger
        risk = score_inventory_risk(
            "SKU-X", [10.0] * 30, stock_on_hand=450, unit_cost=10
        )
        assert risk.risk_level == "Low"

    def test_revenue_at_risk_positive_for_stockout(self):
        risk = score_inventory_risk(
            "SKU-X", [100.0] * 30, stock_on_hand=100, unit_cost=5
        )
        assert risk.revenue_at_risk > 0

    def test_no_revenue_risk_when_stocked(self):
        risk = score_inventory_risk(
            "SKU-X", [10.0] * 30, stock_on_hand=9999, unit_cost=5
        )
        assert risk.revenue_at_risk == 0

    def test_service_level_capped_at_100(self):
        risk = score_inventory_risk(
            "SKU-X", [10.0] * 30, stock_on_hand=9999, unit_cost=5
        )
        assert risk.service_level <= 100.0

    def test_reorder_qty_non_negative(self):
        risk = score_inventory_risk(
            "SKU-X", [50.0] * 30, stock_on_hand=200, unit_cost=10
        )
        assert risk.recommended_reorder_qty >= 0

    def test_message_is_not_empty(self):
        risk = score_inventory_risk(
            "SKU-X", [50.0] * 30, stock_on_hand=200, unit_cost=10
        )
        assert len(risk.message) > 0

    def test_days_of_cover_calculation(self):
        risk = score_inventory_risk(
            "SKU-X", [10.0] * 30, stock_on_hand=200, unit_cost=5
        )
        assert risk.days_of_cover == pytest.approx(20.0, abs=0.1)


# ── Portfolio Summary ─────────────────────────────────────────────────────────
class TestPortfolioSummary:
    def _make_risk(self, level: str) -> InventoryRisk:
        return InventoryRisk(
            product_id="X",
            risk_level=level,
            risk_type="Stock-out",
            forecast_demand=100,
            stock_on_hand=50,
            recommended_reorder_qty=60,
            priority_score=10,
            financial_priority=10.0,
            revenue_at_risk=100.0,
            profit_at_risk=40.0,
            overstock_value=0,
            service_level=75.0,
            days_of_cover=5.0,
            forecast_confidence=90,
            expected_stockout_days=3.0,
            recommended_action="Reorder Immediately",
            root_causes=["test"],
            message="test",
        )

    def test_counts_high_risk(self):
        risks = [
            self._make_risk("High"),
            self._make_risk("High"),
            self._make_risk("Low"),
        ]
        summary = summarize_portfolio(risks)
        assert summary["high_risk_skus"] == 2

    def test_total_revenue_at_risk(self):
        risks = [self._make_risk("High")] * 3
        summary = summarize_portfolio(risks)
        assert summary["revenue_at_risk"] == 300.0

    def test_empty_portfolio(self):
        summary = summarize_portfolio([])
        assert summary["sku_count"] == 0


# ── RiskScoreCalculator ───────────────────────────────────────────────────────
class TestRiskScoreCalculator:
    def test_score_between_0_and_100(self):
        calc = RiskScoreCalculator()
        score = calc.calculate(forecast=1000, stock=500, revenue=200000)
        assert 0 <= score <= 100

    def test_zero_forecast_returns_zero(self):
        calc = RiskScoreCalculator()
        assert calc.calculate(0, 500, 100000) == 0

    def test_critical_when_very_low_stock(self):
        calc = RiskScoreCalculator()
        classifier = RiskClassifier()
        score = calc.calculate(forecast=1000, stock=10, revenue=500000)
        assert classifier.classify(score) == "CRITICAL"

    def test_low_when_well_stocked(self):
        calc = RiskScoreCalculator()
        classifier = RiskClassifier()
        score = calc.calculate(forecast=100, stock=10000, revenue=50000)
        assert classifier.classify(score) == "LOW"


# ── PortfolioRiskRanking ──────────────────────────────────────────────────────
class TestPortfolioRiskRanking:
    @pytest.fixture
    def products(self):
        return [
            {"sku": "SKU-A", "forecast": 1000, "stock": 50, "revenue": 500000},
            {"sku": "SKU-B", "forecast": 500, "stock": 2000, "revenue": 80000},
            {"sku": "SKU-C", "forecast": 800, "stock": 300, "revenue": 200000},
        ]

    def test_returns_all_skus(self, products):
        engine = PortfolioRiskRanking()
        rankings = engine.rank(products)
        assert len(rankings) == 3

    def test_sorted_descending_by_score(self, products):
        engine = PortfolioRiskRanking()
        rankings = engine.rank(products)
        scores = [r["risk_score"] for r in rankings]
        assert scores == sorted(scores, reverse=True)

    def test_critical_only_filters_correctly(self, products):
        engine = PortfolioRiskRanking()
        critical = engine.critical_only(products)
        assert all(r["risk"] == "CRITICAL" for r in critical)

    def test_each_result_has_required_keys(self, products):
        engine = PortfolioRiskRanking()
        rankings = engine.rank(products)
        for r in rankings:
            assert all(
                k in r
                for k in [
                    "sku",
                    "risk_score",
                    "risk",
                    "stockout",
                    "overstock",
                    "revenue_risk",
                ]
            )
