"""Tests for inventory optimization."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.inventory.optimizer import InventoryOptimizer
from backend.inventory.reorder import ReorderPlanner
from backend.inventory.reorder_point import ReorderPointCalculator
from backend.inventory.safety_stock import SafetyStockCalculator


@pytest.fixture
def optimizer():
    return InventoryOptimizer()


# ── Safety Stock ──────────────────────────────────────────────────────────────
class TestSafetyStock:
    def test_basic_calculation(self):
        calc = SafetyStockCalculator()
        result = calc.calculate(demand_std=20, lead_time=9, z_score=1.65)
        expected = 1.65 * 20 * math.sqrt(9)
        assert abs(result - expected) < 0.01

    def test_zero_std(self):
        calc = SafetyStockCalculator()
        assert calc.calculate(0, 7) == 0.0


# ── Reorder Point ─────────────────────────────────────────────────────────────
class TestReorderPoint:
    def test_basic_calculation(self):
        calc = ReorderPointCalculator()
        result = calc.calculate(avg_daily_demand=10, lead_time=7, safety_stock=30)
        assert result == 100.0

    def test_zero_lead_time(self):
        calc = ReorderPointCalculator()
        assert calc.calculate(10, 0, 20) == 20.0


# ── ReorderPlanner ────────────────────────────────────────────────────────────
class TestReorderPlanner:
    def test_recommends_order_when_low_stock(self):
        planner = ReorderPlanner()
        result = planner.calculate(forecast=1000, current_stock=200)
        assert result["recommended_order"] > 0

    def test_no_order_when_overstocked(self):
        planner = ReorderPlanner()
        result = planner.calculate(forecast=500, current_stock=2000)
        assert result["recommended_order"] == 0

    def test_returns_all_keys(self):
        planner = ReorderPlanner()
        result = planner.calculate(1000, 500)
        assert all(
            k in result
            for k in ["forecast", "safety_stock", "reorder_point", "recommended_order"]
        )


# ── InventoryOptimizer ────────────────────────────────────────────────────────
class TestInventoryOptimizer:
    def test_eoq_is_positive(self, optimizer):
        result = optimizer.calculate_eoq(
            annual_demand=12000, ordering_cost=100, holding_cost=5
        )
        assert result > 0

    def test_eoq_zero_holding_cost(self, optimizer):
        assert optimizer.calculate_eoq(12000, 100, 0) == 0

    def test_safety_stock_positive(self, optimizer):
        ss = optimizer.calculate_safety_stock(demand_std=20, lead_time_days=7)
        assert ss > 0

    def test_reorder_point_formula(self, optimizer):
        ss = optimizer.calculate_safety_stock(20, 7)
        rop = optimizer.calculate_reorder_point(
            avg_daily_demand=40, lead_time_days=7, safety_stock=ss
        )
        assert rop == round(40 * 7 + ss, 2)

    def test_stockout_probability_critical(self, optimizer):
        assert optimizer.stockout_probability(stock=10, forecast=1000) == 95

    def test_stockout_probability_healthy(self, optimizer):
        assert optimizer.stockout_probability(stock=2000, forecast=1000) == 5

    def test_health_score_capped_at_100(self, optimizer):
        assert optimizer.inventory_health_score(stock=9999, forecast=100) == 100

    def test_health_score_zero_forecast(self, optimizer):
        assert optimizer.inventory_health_score(stock=100, forecast=0) == 100

    def test_optimize_returns_all_keys(self, optimizer):
        result = optimizer.optimize(forecast=1200, current_stock=500)
        expected_keys = [
            "forecast",
            "current_stock",
            "safety_stock",
            "reorder_point",
            "economic_order_qty",
            "recommended_order",
            "stockout_risk",
            "inventory_health",
        ]
        assert all(k in result for k in expected_keys)

    def test_optimize_no_negative_order(self, optimizer):
        result = optimizer.optimize(forecast=500, current_stock=5000)
        assert result["recommended_order"] == 0
