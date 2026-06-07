"""Prompt templates for the RetailGPT copilot."""

FORECAST_ANALYSIS_PROMPT = """You are a retail inventory AI assistant.

Analyze the following SKU data and provide:
1. Risk assessment (CRITICAL / HIGH / MEDIUM / LOW)
2. Recommended action
3. One-sentence executive summary

SKU: {sku}
Forecast (30 days): {forecast} units
Current Stock: {stock} units
Unit Price: ₹{price}
Coverage Ratio: {coverage:.1%}
"""

BOARD_SUMMARY_PROMPT = """You are a CFO-level retail analytics AI.

Summarize the following portfolio for a board presentation:
- Total SKUs: {sku_count}
- Critical SKUs: {critical_skus}
- Total Forecasted Revenue: ₹{total_revenue:,.0f}
- Portfolio Health Score: {health_score}%

Provide a 2-3 sentence executive brief suitable for a board meeting.
"""

STOCKOUT_ALERT_PROMPT = """
SKU {sku} is at CRITICAL stockout risk.
Current stock: {stock} units
30-day forecast: {forecast} units
Revenue at risk: ₹{revenue_at_risk:,.0f}

What immediate actions should the operations team take?
"""
