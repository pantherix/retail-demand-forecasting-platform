from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from .providers import CircuitBreakerOpenError, ProviderFactory
import sqlalchemy
from sqlalchemy.orm import Session

from backend.database.models import (
    Alert,
    Forecast,
    InventoryItem,
    Product,
    RiskScore,
    Sale,
    Warehouse,
)

logger = logging.getLogger(__name__)


class RetailCopilot:
    """
    AI Copilot for retail decision support.
    Integrates with RAG to retrieve operational facts and generates structured insights.
    """

    def __init__(self):
        # Initialize any needed attributes
        from .tools import TOOLS

        self.tools = TOOLS

    def _get_provider_name(self) -> str:
        """Return the configured provider name (defaults to 'openai')."""
        return os.getenv("LLM_PROVIDER", "openai").lower()

    def _get_provider_names(self) -> List[str]:
        """Return the list of configured LLM providers.
        Reads LLM_PROVIDERS env var as comma‑separated list; defaults to ['openai', 'groq'].
        """
        providers = os.getenv("LLM_PROVIDERS")
        if providers:
            return [p.strip().lower() for p in providers.split(",") if p.strip()]
        return ["openai", "groq"]

    # REMOVED: class-level _fallback_response method; using inner fallback function defined inside chat()

    def explain(self, sku: str, forecast: float, stock: float) -> str:
        coverage = stock / max(forecast, 1)
        if coverage < 0.5:
            return (
                f"SKU {sku} is in a CRITICAL state. With only {stock} units on hand against "
                f"a forecast of {forecast}, you have {round(coverage * 100)}% coverage. "
                "Immediate replenishment is required to avoid stockout."
            )
        elif coverage < 1.0:
            return (
                f"SKU {sku} is AT RISK. Current stock covers {round(coverage * 100)}% of forecast demand. "
                "A reorder should be placed within the next 7 days."
            )
        else:
            return (
                f"SKU {sku} is HEALTHY. Stock covers {round(coverage * 100)}% of forecast demand. "
                "Continue normal operations."
            )

    def analyze_forecast(
        self, sku: str, forecast: float, stock: float, price: float
    ) -> Dict:
        coverage = stock / max(forecast, 1)
        revenue_at_risk = max(forecast - stock, 0) * price

        if coverage < 0.5:
            risk_level = "CRITICAL"
            action = f"Immediately reorder {round(forecast - stock + forecast * 0.2)} units. Revenue at risk: ₹{revenue_at_risk:,.0f}."
        elif coverage < 1.0:
            risk_level = "HIGH"
            action = f"Plan reorder of {round((forecast - stock) * 1.1)} units within 7 days."
        elif coverage > 2.0:
            risk_level = "OVERSTOCK"
            action = (
                "Pause replenishment. Consider promotions to clear excess inventory."
            )
        else:
            risk_level = "HEALTHY"
            action = "Continue normal replenishment schedule."

        return {
            "sku": sku,
            "risk_level": risk_level,
            "coverage_ratio": round(coverage, 2),
            "revenue_at_risk": round(revenue_at_risk, 2),
            "recommended_action": action,
            "source": "rule_based",
        }

    def chat(
        self, prompt: str, db: Session, history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict:
        """
        Processes chatbot prompt: Question -> DB Query -> Decision Engine -> LLM/Local Output.
        """
        prompt_lower = prompt.lower()
        # Log incoming prompt and intent detection
        logger.info("RetailCopilot.chat called with prompt: %s", prompt)
        logger.debug("Prompt lowercased: %s", prompt_lower)
        # Parse intent flags will be evaluated later
        logger.debug("Intent detection will follow after regex matches.")
        # 1. Parse Question to identify target entities and intents
        sku_match = re.search(r"(SKU-\d+)", prompt, re.IGNORECASE)
        wh_match = re.search(r"(Warehouse\s+[A-Z])", prompt, re.IGNORECASE)
        cat_match = re.search(
            r"(Beverages|Snacks|Personal Care|Home Care|Packaged Food|Nutrition|Pharmacy|Electronics)",
            prompt,
            re.IGNORECASE,
        )

        is_order = any(
            w in prompt_lower
            for w in [
                "order",
                "reorder",
                "replenish",
                "replenishment",
                "buy",
                "purchase",
                "procure",
            ]
        )
        is_stockout = any(
            w in prompt_lower
            for w in ["stock out", "stockout", "run out", "low stock", "safety stock"]
        )
        is_revenue = any(
            w in prompt_lower
            for w in [
                "revenue at risk",
                "revenue is at risk",
                "what revenue",
                "financial exposure",
                "exposure",
                "money at risk",
                "profit at risk",
            ]
        )
        is_warehouse_overload = any(
            w in prompt_lower
            for w in ["overload", "capacity", "utilization", "overloaded"]
        )

        # Removed strict intent filter so conversational queries can reach the LLM

        context_data = {}
        table = None
        chart = None
        action_cards = []
        suggestions = [
            "What should I order today?",
            "Which SKU will stock out?",
            "What revenue is at risk?",
            "Which warehouse is overloaded?",
        ]
        confidence = "high"
        local_insight = "I am RetailGPT Copilot."
        local_recommendation = "I am ready to assist you."
        local_financial_impact = "N/A"

        # General/default intent — build a context-aware local summary AND pass the
        # user's actual question to the LLM so freeform queries get real answers.
        is_freeform = not (sku_match or wh_match or cat_match or is_order or is_stockout or is_revenue or is_warehouse_overload)
        if is_freeform:
            try:
                active_risks = db.query(RiskScore).filter(RiskScore.status != "Resolved").all()
                total_at_risk = sum(r.revenue_at_risk for r in active_risks)
                active_alerts = db.query(Alert).filter(Alert.status == "Active").count()
                critical_count = sum(1 for r in active_risks if r.financial_priority == 1)

                if active_risks:
                    system_context = (
                        f"Current system state: {len(active_risks)} active risk nodes, "
                        f"{critical_count} critical, total revenue at risk ₹{total_at_risk:,.2f}, "
                        f"{active_alerts} active alerts."
                    )
                    local_insight = (
                        f"System check: {len(active_risks)} active risk nodes detected with "
                        f"{critical_count} critical issues. Total revenue at risk is ₹{total_at_risk:,.2f}."
                    )
                    local_recommendation = (
                        f"Review the exception feed and resolve the {active_alerts} active system alerts. "
                        "Prioritize critical SKU replenishment playbooks."
                    )
                    local_financial_impact = f"Mitigating these exposures protects up to ₹{total_at_risk:,.2f} of gross revenue."
                else:
                    system_context = "Current system state: All inventory nodes are healthy with no active risks."
                    local_insight = "System health check: All inventory nodes are currently healthy and balanced."
                    local_recommendation = "Maintain standard automated replenishment monitoring."
                    local_financial_impact = "Margins and service levels are fully protected."

                # For freeform queries, enrich the prompt with system context so the
                # LLM can give a meaningful, query-specific answer.
                prompt = f"User question: {prompt}\n\nSystem context: {system_context}"
            except Exception as e:
                logger.error("Failed to compile default local system overview: %s", e)

        local_answer = f"{local_insight}\n\n**Recommendation:** {local_recommendation}"

        # 2. Query DB based on specific intents
        if sku_match:
            sku = sku_match.group(1).upper()
            from datetime import datetime, timedelta

            from src.business.inventory_risk import score_inventory_risk

            prod = db.query(Product).filter(Product.sku == sku).first()
            if prod:
                inv_items = (
                    db.query(InventoryItem)
                    .filter(InventoryItem.product_id == prod.id)
                    .all()
                )
                total_stock = sum(item.current_stock for item in inv_items)
                risk = (
                    db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
                )
                alerts = (
                    db.query(Alert)
                    .filter(Alert.product_id == prod.id, Alert.status == "Active")
                    .all()
                )

                # Use model forecasts (expected_demand), not historical sales quantities.
                # score_inventory_risk() expects per-day forecast demand values.
                forecasts_30d = (
                    db.query(Forecast.expected_demand)
                    .filter(
                        Forecast.product_id == prod.id,
                        Forecast.forecast_date > datetime.utcnow(),
                    )
                    .order_by(Forecast.forecast_date.asc())
                    .limit(30)
                    .all()
                )
                forecast_list = (
                    [float(f[0]) for f in forecasts_30d]
                    if forecasts_30d
                    else [10.0] * 30
                )

                computed_risk = score_inventory_risk(
                    prod.sku, forecast_list, total_stock, prod.unit_cost
                )
                days_cover = computed_risk.days_of_cover

                context_data = {
                    "entity": "SKU",
                    "sku": prod.sku,
                    "name": prod.name,
                    "category": prod.category,
                    "stock": total_stock,
                    "reorder_point": prod.reorder_point,
                    "safety_stock": prod.safety_stock,
                    "days_of_cover": days_cover,
                    "revenue_at_risk": computed_risk.revenue_at_risk,
                    "profit_at_risk": computed_risk.profit_at_risk,
                    "recommended_reorder_qty": computed_risk.recommended_reorder_qty,
                    "recommended_action": computed_risk.recommended_action,
                    "risk_level": computed_risk.risk_level,
                    "profit_at_risk": computed_risk.profit_at_risk,  # Ensure profit_at_risk is also included
                    "root_causes": computed_risk.root_causes,
                    "alerts": [a.message for a in alerts],
                }

                table = {
                    "headers": ["Metric", "Value"],
                    "rows": [
                        ["Product Name", prod.name],
                        ["Category", prod.category],
                        ["Current Stock", f"{total_stock:.0f} units"],
                        ["Safety Stock", f"{prod.safety_stock:.0f} units"],
                        ["Reorder Point", f"{prod.reorder_point:.0f} units"],
                        ["Days of Cover", f"{days_cover:.1f} days"],
                        ["Risk Level", computed_risk.risk_level],
                        ["Unit Cost", f"₹{prod.unit_cost:.2f}"],
                    ],
                }

                chart = {
                    "type": "bar",
                    "data": [
                        {"name": "Current Stock", "value": total_stock},
                        {"name": "Safety Stock", "value": prod.safety_stock},
                        {"name": "Reorder Pt", "value": prod.reorder_point},
                    ],
                }

                action_cards = [
                    {
                        "title": f"View {prod.sku} Intel",
                        "description": "Examine product-level forecasts, demand dynamics and scenarios.",
                        "action": "navigate",
                        "params": {"path": "/product-intelligence", "sku": prod.sku},
                    }
                ]

                suggestions = [
                    f"Is there a stockout risk for {prod.sku}?",
                    "What should I order today?",
                    "What revenue is at risk?",
                ]
            else:
                return {
                    "answer": f"SKU {sku} was not found in the database.",
                    "insight": f"SKU {sku} was not found in the database.",
                    "recommendation": "Check the SKU code and try again.",
                    "financial_impact": "N/A",
                    "table": None,
                    "chart": None,
                    "action_cards": [],
                    "suggestions": suggestions,
                    "confidence": "low",
                }

        elif wh_match:
            wh_name = wh_match.group(1)
            wh = db.query(Warehouse).filter(Warehouse.name.ilike(wh_name)).first()
            if wh:
                inv_items = (
                    db.query(InventoryItem)
                    .filter(InventoryItem.warehouse_id == wh.id)
                    .all()
                )
                understocked_items = [
                    item.product.sku
                    for item in inv_items
                    if item.current_stock < item.product.safety_stock
                ]

                context_data = {
                    "entity": "Warehouse",
                    "name": wh.name,
                    "location": wh.location,
                    "capacity": wh.capacity,
                    "utilization": wh.utilization,
                    "items_count": len(inv_items),
                    "understocked_items": understocked_items,
                }

                table = {
                    "headers": ["Metric", "Value"],
                    "rows": [
                        ["Warehouse Name", wh.name],
                        ["Location", wh.location],
                        ["Capacity (Units)", f"{wh.capacity:.0f}"],
                        ["Utilization", f"{wh.utilization:.1f}%"],
                        ["Total Stock Items", f"{len(inv_items)}"],
                        ["Understocked SKUs", f"{len(understocked_items)}"],
                    ],
                }

                chart = {
                    "type": "bar",
                    "data": [
                        {"name": "Utilization %", "value": wh.utilization},
                        {
                            "name": "Available Capacity %",
                            "value": max(100 - wh.utilization, 0),
                        },
                    ],
                }

                action_cards = [
                    {
                        "title": "Logistics Center",
                        "description": "View warehouse network, transfers and recommendations.",
                        "action": "navigate",
                        "params": {"path": "/warehouses"},
                    }
                ]

                suggestions = [
                    "Which warehouse is overloaded?",
                    "What should I order today?",
                ]
            else:
                return {
                    "answer": f"Warehouse {wh_name} was not found in the database.",
                    "insight": f"Warehouse {wh_name} was not found in the database.",
                    "recommendation": "Check the warehouse identifier and try again.",
                    "financial_impact": "N/A",
                    "table": None,
                    "chart": None,
                    "action_cards": [],
                    "suggestions": suggestions,
                    "confidence": "low",
                }

        elif cat_match:
            category = cat_match.group(1)
            products = db.query(Product).filter(Product.category == category).all()
            prod_ids = [p.id for p in products]
            risks = db.query(RiskScore).filter(RiskScore.product_id.in_(prod_ids)).all()
            total_rev_risk = sum(r.revenue_at_risk for r in risks)
            total_profit_risk = sum(r.profit_at_risk for r in risks)
            exposed_skus = [r.product.sku for r in risks if r.revenue_at_risk > 0]

            context_data = {
                "entity": "Category",
                "category": category,
                "product_count": len(products),
                "revenue_at_risk": total_rev_risk,
                "profit_at_risk": total_profit_risk,
                "exposed_skus": exposed_skus,
            }

            table = {
                "headers": ["Metric", "Value"],
                "rows": [
                    ["Category", category],
                    ["Product Count", f"{len(products)}"],
                    ["Exposed SKUs Count", f"{len(exposed_skus)}"],
                    ["Revenue at Risk", f"₹{total_rev_risk:,.2f}"],
                    ["Profit at Risk", f"₹{total_profit_risk:,.2f}"],
                ],
            }

            chart = {
                "type": "pie",
                "data": [
                    {"name": r.product.sku, "value": r.revenue_at_risk}
                    for r in risks
                    if r.revenue_at_risk > 0
                ],
            }

            action_cards = [
                {
                    "title": "Decision Center",
                    "description": "Review category risks in the Decision Center.",
                    "action": "navigate",
                    "params": {"path": "/decisions"},
                }
            ]

            suggestions = ["What should I order today?", "Which SKU will stock out?"]

        elif is_order:
            products = db.query(Product).all()
            order_items = []
            total_order_cost = 0.0

            for prod in products:
                inv_items = (
                    db.query(InventoryItem)
                    .filter(InventoryItem.product_id == prod.id)
                    .all()
                )
                stock = sum(item.current_stock for item in inv_items)
                risk = (
                    db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
                )

                reorder_point = prod.reorder_point
                recommended_qty = risk.reorder_quantity if risk else 0.0

                if stock <= reorder_point or recommended_qty > 0:
                    supplier_name = prod.supplier.name if prod.supplier else "N/A"
                    lead_time = prod.lead_time_days
                    unit_cost = prod.unit_cost

                    rec_qty = (
                        recommended_qty
                        if recommended_qty > 0
                        else max(reorder_point * 1.5 - stock, 0.0)
                    )
                    if rec_qty > 0:
                        purchase_cost = rec_qty * unit_cost
                        total_order_cost += purchase_cost

                        f_sum = db.query(
                            sqlalchemy.func.sum(Forecast.expected_demand)
                        ).filter(Forecast.product_id == prod.id).scalar() or (
                            reorder_point * 2.0
                        )

                        order_items.append(
                            {
                                "sku": prod.sku,
                                "name": prod.name,
                                "stock": stock,
                                "safety_stock": prod.safety_stock,
                                "reorder_point": reorder_point,
                                "forecast_demand": f_sum,
                                "recommended_qty": rec_qty,
                                "supplier": supplier_name,
                                "lead_time": lead_time,
                                "unit_cost": unit_cost,
                                "purchase_cost": purchase_cost,
                            }
                        )

            order_items.sort(key=lambda x: x["purchase_cost"], reverse=True)

            context_data = {
                "entity": "Reorder Analysis",
                "reorder_items_count": len(order_items),
                "total_order_cost": total_order_cost,
                "items": [
                    {"sku": o["sku"], "qty": o["recommended_qty"]}
                    for o in order_items[:5]
                ],
            }

            table = {
                "headers": [
                    "SKU",
                    "Product",
                    "Stock",
                    "Reorder Pt",
                    "Rec. Qty",
                    "Cost",
                    "Supplier",
                ],
                "rows": [
                    [
                        item["sku"],
                        item["name"],
                        f"{item['stock']:.0f}",
                        f"{item['reorder_point']:.0f}",
                        f"{item['recommended_qty']:.0f}",
                        f"₹{item['purchase_cost']:,.2f}",
                        item["supplier"],
                    ]
                    for item in order_items[:10]
                ],
            }

            chart = {
                "type": "bar",
                "data": [
                    {"name": item["sku"], "value": item["purchase_cost"]}
                    for item in order_items[:8]
                ],
            }

            action_cards = [
                {
                    "title": "Review Reorder Recommendations",
                    "description": "Approve generated draft purchase orders in the Reorder Engine.",
                    "action": "navigate",
                    "params": {"path": "/reorder"},
                }
            ]

            suggestions = [
                "Which SKU will stock out?",
                "What revenue is at risk?",
                "Which warehouse is overloaded?",
            ]

        elif is_stockout:
            products = db.query(Product).all()
            stockout_items = []

            for prod in products:
                inv_items = (
                    db.query(InventoryItem)
                    .filter(InventoryItem.product_id == prod.id)
                    .all()
                )
                stock = sum(item.current_stock for item in inv_items)
                risk = (
                    db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
                )

                days_cover = (
                    risk.expected_stockout_days
                    if (risk and risk.expected_stockout_days is not None)
                    else 0.0
                )
                if (
                    not risk or risk.expected_stockout_days is None
                ) and prod.reorder_point > 0:
                    days_cover = stock / (
                        prod.reorder_point / max(prod.lead_time_days, 1)
                    )

                rev_risk = risk.revenue_at_risk if risk else 0.0

                if stock < prod.safety_stock or days_cover < 10:
                    stockout_items.append(
                        {
                            "sku": prod.sku,
                            "name": prod.name,
                            "stock": stock,
                            "safety_stock": prod.safety_stock,
                            "days_cover": days_cover,
                            "revenue_risk": rev_risk,
                        }
                    )

            stockout_items.sort(key=lambda x: (x["days_cover"], -x["revenue_risk"]))

            context_data = {
                "entity": "Stockout Risk Analysis",
                "stockout_items_count": len(stockout_items),
                "items": [
                    {"sku": s["sku"], "days_cover": s["days_cover"]}
                    for s in stockout_items[:5]
                ],
            }

            table = {
                "headers": [
                    "SKU",
                    "Product",
                    "Stock",
                    "Safety Stock",
                    "Days of Cover",
                    "Revenue Risk",
                ],
                "rows": [
                    [
                        item["sku"],
                        item["name"],
                        f"{item['stock']:.0f}",
                        f"{item['safety_stock']:.0f}",
                        f"{item['days_cover']:.1f} days",
                        f"₹{item['revenue_risk']:,.2f}",
                    ]
                    for item in stockout_items[:10]
                ],
            }

            chart = {
                "type": "bar",
                "data": [
                    {"name": item["sku"], "value": item["days_cover"]}
                    for item in stockout_items[:8]
                ],
            }

            action_cards = [
                {
                    "title": "Open Decision Center",
                    "description": "Manage active alerts and mitigate stockout exposure.",
                    "action": "navigate",
                    "params": {"path": "/decisions"},
                }
            ]

            suggestions = [
                "What should I order today?",
                "What revenue is at risk?",
                "Which warehouse is overloaded?",
            ]

        elif is_revenue:
            risks = (
                db.query(RiskScore)
                .filter(RiskScore.revenue_at_risk > 0)
                .order_by(RiskScore.revenue_at_risk.desc())
                .all()
            )
            risk_items = []

            for r in risks:
                prod = r.product
                inv_items = (
                    db.query(InventoryItem)
                    .filter(InventoryItem.product_id == prod.id)
                    .all()
                )
                stock = sum(item.current_stock for item in inv_items)

                risk_items.append(
                    {
                        "sku": prod.sku,
                        "name": prod.name,
                        "category": prod.category,
                        "stock": stock,
                        "revenue_risk": r.revenue_at_risk,
                        "profit_risk": r.profit_at_risk,
                        "priority": (
                            "Critical"
                            if r.financial_priority == 1
                            else "High" if r.financial_priority == 2 else "Medium"
                        ),
                        "action": r.recommended_action,
                    }
                )

            context_data = {
                "entity": "Revenue Exposure Analysis",
                "risk_items_count": len(risk_items),
                "total_revenue_at_risk": sum(x["revenue_risk"] for x in risk_items),
            }

            table = {
                "headers": [
                    "SKU",
                    "Product",
                    "Category",
                    "Priority",
                    "Revenue Risk",
                    "Margin Risk",
                ],
                "rows": [
                    [
                        item["sku"],
                        item["name"],
                        item["category"],
                        item["priority"],
                        f"₹{item['revenue_risk']:,.2f}",
                        f"₹{item['profit_risk']:,.2f}",
                    ]
                    for item in risk_items[:10]
                ],
            }

            chart = {
                "type": "pie",
                "data": [
                    {"name": item["sku"], "value": item["revenue_risk"]}
                    for item in risk_items[:8]
                ],
            }

            action_cards = [
                {
                    "title": "Open Scenario Lab",
                    "description": "Simulate demand pricing changes to mitigate revenue risks.",
                    "action": "navigate",
                    "params": {"path": "/scenario-lab"},
                }
            ]

            suggestions = [
                "What should I order today?",
                "Which SKU will stock out?",
                "Which warehouse is overloaded?",
            ]

        elif is_warehouse_overload:
            warehouses = db.query(Warehouse).all()
            wh_items = []

            for wh in warehouses:
                inv_items = (
                    db.query(InventoryItem)
                    .filter(InventoryItem.warehouse_id == wh.id)
                    .all()
                )
                stock = sum(item.current_stock for item in inv_items)
                val = sum(
                    item.current_stock * item.product.unit_cost
                    for item in inv_items
                    if item.product.unit_cost is not None
                )

                wh_items.append(
                    {
                        "name": wh.name,
                        "location": wh.location,
                        "capacity": wh.capacity,
                        "utilization": wh.utilization,
                        "stock_units": stock,
                        "stock_value": val,
                    }
                )

            wh_items.sort(key=lambda x: x["utilization"], reverse=True)

            context_data = {
                "entity": "Warehouse Network Analysis",
                "warehouses_count": len(wh_items),
                "overloaded": [w["name"] for w in wh_items if w["utilization"] > 80.0],
            }

            table = {
                "headers": [
                    "Warehouse",
                    "Location",
                    "Stock (Units)",
                    "Valuation",
                    "Capacity",
                    "Utilization",
                ],
                "rows": [
                    [
                        item["name"],
                        item["location"],
                        f"{item['stock_units']:.0f}",
                        f"₹{item['stock_value']:,.2f}",
                        f"{item['capacity']:.0f}",
                        f"{item['utilization']:.1f}%",
                    ]
                    for item in wh_items
                ],
            }

            chart = {
                "type": "bar",
                "data": [
                    {"name": item["name"], "value": item["utilization"]}
                    for item in wh_items
                ],
            }

            action_cards = [
                {
                    "title": "Logistics Intelligence",
                    "description": "Review warehouse utilization and transfer excess stock.",
                    "action": "navigate",
                    "params": {"path": "/warehouses"},
                }
            ]

            suggestions = [
                "What should I order today?",
                "Which SKU will stock out?",
                "What revenue is at risk?",
            ]

        # 3. Compile local fallback responses

        if sku_match:
            local_insight = (
                f"SKU {context_data['sku']} ({context_data['name']}) has a risk level of {context_data['risk_level']}. "
                f"Current stock of {context_data['stock']:.0f} units provides {context_data['days_of_cover']:.1f} days of cover. "
                f"Financial exposure: ₹{context_data['revenue_at_risk']:,.2f} revenue at risk, ₹{context_data['profit_at_risk']:,.2f} profit at risk. "
                "Database query status evaluated under SKUs requiring replenishment."
            )
            local_recommendation = (
                f"Action recommendation is '{context_data['recommended_action']}' for {context_data['recommended_reorder_qty']:.0f} units. "
                f"Root causes: {', '.join(context_data['root_causes'])}."
            )
            local_financial_impact = f"Executing this action mitigates ₹{context_data['revenue_at_risk']:,.2f} of revenue at risk and protects ₹{context_data['profit_at_risk']:,.2f} of margins."

        elif wh_match:
            local_insight = f"Warehouse '{context_data['name']}' in {context_data['location']} is at {context_data['utilization']:.1f}% capacity utilization."
            if context_data["understocked_items"]:
                local_recommendation = f"Initiate transfer inventory to mitigate understock on SKUs: {', '.join(context_data['understocked_items'])}."
                local_financial_impact = "Rebalancing stock prevents potential stockouts in localized regions."
            else:
                local_recommendation = "Maintain current storage levels."
                local_financial_impact = (
                    "No immediate financial loss risks detected for this node."
                )

        elif cat_match:
            local_insight = f"Category '{context_data['category']}' has {context_data['product_count']} active products. "
            if context_data["exposed_skus"]:
                local_recommendation = f"Stockouts detected. Action required on exposed SKUs: {', '.join(context_data['exposed_skus'])}."
                local_financial_impact = f"Resolving exposure protects ₹{context_data['revenue_at_risk']:,.2f} in revenue and ₹{context_data['profit_at_risk']:,.2f} in profit."
            else:
                local_recommendation = "Category is fully stocked."
                local_financial_impact = "Margins protected."

        elif is_order:
            local_insight = f"Database scan reveals {context_data['reorder_items_count']} SKUs requiring replenishment."
            local_recommendation = f"Suggested to approve purchase orders for key SKUs: {', '.join(o['sku'] for o in order_items[:3])}."
            local_financial_impact = f"Executing these orders requires ₹{context_data['total_order_cost']:,.2f} procurement budget."

        elif is_stockout:
            local_insight = f"There are {context_data['stockout_items_count']} SKUs with potential stockout risks."
            local_recommendation = f"Prioritize restocking or internal transfers for critical items: {', '.join(s['sku'] for s in stockout_items[:3])}."
            local_financial_impact = (
                "Stockout mitigation protects client service levels."
            )

        elif is_revenue:
            local_insight = f"Revenue exposure is active on {context_data['risk_items_count']} items, totaling ₹{context_data['total_revenue_at_risk']:,.2f}."
            local_recommendation = "Expedite reorders and review supplier fill rates."
            local_financial_impact = f"Protects up to ₹{context_data['total_revenue_at_risk']:,.2f} of gross revenue."

        elif is_warehouse_overload:
            local_insight = f"Logistics network audit shows {context_data['warehouses_count']} warehouses."
            overloaded_whs = context_data.get("overloaded", [])
            if overloaded_whs:
                local_recommendation = f"Relocate stock from overloaded facilities: {', '.join(overloaded_whs)}."
                local_financial_impact = "Reduces localized logistics congestion risk."
            else:
                local_recommendation = (
                    "Warehouse utilization levels are within safe operating limits."
                )
                local_financial_impact = "No overflow costs expected."

        # Update local_answer to capture any logic-based updates to insight/recommendation
        local_answer = f"{local_insight}\n\n**Recommendation:** {local_recommendation}"

        sku_val = (
            context_data.get("sku", None)
            if context_data.get("entity") == "SKU"
            else None
        )

        def _fallback_response():
            # Construct answer dynamically to capture any updates to local_insight
            answer = f"{local_insight}\n\n**Recommendation:** {local_recommendation}"
            return {
                "answer": answer,
                "insight": local_insight,
                "recommendation": local_recommendation,
                "financial_impact": local_financial_impact,
                "sku": sku_val,
                "table": table,
                "chart": chart,
                "action_cards": action_cards,
                "suggestions": suggestions,
                "confidence": "low",
            }

        # ------------------------------------------------------------------
        # Robust ProviderFactory integration with fallback chain
        # ------------------------------------------------------------------
        # Ensure system_prompt is always defined; providers expect it.
        system_prompt = (
            "You are RetailGPT, a precise retail operations decision assistant.\n"
            "You MUST respond ONLY with a raw JSON object (no markdown wrapping, no introductory text) matching this schema:\n"
            "{\n"
            '  "answer": "A clear, conversational response to the user query.",\n'
            '  "insight": "A concise operational insight summarizing the system state or SKU risk.",\n'
            '  "recommendation": "Suggested next steps or decisions to execute.",\n'
            '  "financial_impact": "Estimated cost, revenue at risk, or financial protection description.",\n'
            '  "sku": "The SKU string if the user is asking about a specific SKU, else null",\n'
            '  "table": {"headers": ["col1", "col2"], "rows": [["val1", "val2"]]} or null,\n'
            '  "chart": {"type": "line|bar|pie", "data": [{"name": "label", "value": 100}]} or null,\n'
            '  "action_cards": [{"title": "Reorder SKU-X", "action": "autogenerate_po", "sku": "SKU-X", "quantity": 100, "supplier_id": 1}] or empty list,\n'
            '  "suggestions": ["list", "of", "quick", "followup", "questions"],\n'
            '  "confidence": "high|medium|low"\n'
            "}\n"
            "Ensure the JSON is valid and easily parseable."
        )

        fallback_fn = _fallback_response
        provider_used = None
        last_error = None
        response = None
        for prov_name in self._get_provider_names():
            try:
                provider = ProviderFactory.get_provider(
                    prov_name, fallback_fn=fallback_fn
                )
                result = provider.chat(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history=history,
                    tools=self.tools,
                )

                # Treat an empty dict as a non-response (e.g. missing API key)
                # so we fall through to the next provider instead of silently
                # returning the hardcoded local_answer.
                if not result:
                    logger.warning(
                        "LLM provider %s returned empty response; trying next provider.", prov_name
                    )
                    last_error = RuntimeError(f"{prov_name} returned empty response")
                    continue

                response = result
                provider_used = prov_name
                # Successful LLM response – break out of the loop
                break
            except CircuitBreakerOpenError as e:
                logger.warning("LLM provider %s circuit is OPEN: %s", prov_name, str(e))
                last_error = e
            except Exception as e:
                logger.error(
                    "LLM provider %s failed with error: %s",
                    prov_name,
                    str(e),
                    exc_info=True,
                )
                last_error = e
        
        if response is None:
            # All providers failed – fall back to rule‑based response
            error_msg = str(last_error) if last_error else "All providers failed"
            logger.warning(
                "All LLM providers failed, using rule‑based fallback: %s", error_msg
            )
            if "quota" in error_msg:
                local_insight = (
                    "LLM quota exceeded. Switching to local rule‑based fallback."
                )
            elif "401" in error_msg or "AuthenticationError" in error_msg:
                local_insight = (
                    "LLM authentication failed. Switching to local rule‑based fallback."
                )

            fallback_res = fallback_fn()
            # The fallback_fn closure already captures the (potentially updated) local_insight
            # and constructs the answer based on it.
            fallback_res["provider_used"] = "rule_based"
            return fallback_res
        # If we have a successful response, construct the final payload
        try:
            if not isinstance(response, dict):
                raise AttributeError("LLM response is not a dictionary.")
            return {
                "answer": response.get("answer", local_answer),
                "insight": response.get("insight", local_insight),
                "recommendation": response.get("recommendation", local_recommendation),
                "financial_impact": response.get(
                    "financial_impact", local_financial_impact
                ),
                "sku": response.get("sku", sku_val),
                "table": response.get("table", table),
                "chart": response.get("chart", chart),
                "action_cards": response.get("action_cards", action_cards),
                "suggestions": response.get("suggestions", suggestions),
                "confidence": response.get("confidence", "high"),
                "provider_used": provider_used,  # Use the actual provider that succeeded
            }
        except Exception as payload_err:
            logger.error("Failed to build copilot response payload, falling back: %s", payload_err, exc_info=True)
            fallback_res = fallback_fn()
            fallback_res["provider_used"] = "rule_based"
            return fallback_res


copilot = RetailCopilot()
