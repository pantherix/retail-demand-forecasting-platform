from __future__ import annotations

import io
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd


class BaseAdapter:
    """
    Base class for all data source adapters.
    All adapters must parse their respective formats and output the canonical schema:
    - products: List[Dict[str, Any]] -> {sku, product_name, category, unit_cost, unit_price}
    - inventory: List[Dict[str, Any]] -> {sku, warehouse, current_stock}
    - sales: List[Dict[str, Any]] -> {sku, date, quantity_sold, revenue, warehouse}
    """

    def __init__(self, data: Any = None, mapping: Dict[str, str] = None):
        self.data = data
        self.mapping = mapping or {}

    def parse(self) -> Dict[str, List[Dict[str, Any]]]:
        raise NotImplementedError


class CSVAdapter(BaseAdapter):
    def parse(self) -> Dict[str, List[Dict[str, Any]]]:
        df = pd.read_csv(io.BytesIO(self.data))
        return self._normalize_df(df)

    def _normalize_df(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        sku_col = self.mapping.get("sku")
        qty_col = self.mapping.get("current_stock")
        date_col = self.mapping.get("date")
        rev_col = self.mapping.get("revenue")

        prod_name_col = self.mapping.get("product_name")
        cat_col = self.mapping.get("category")
        cost_col = self.mapping.get("unit_cost")
        price_col = self.mapping.get("unit_price")
        wh_col = self.mapping.get("warehouse")

        products = []
        inventory = []
        sales = []
        seen_skus = set()

        for _, row in df.iterrows():
            sku_val = (
                str(row[sku_col]).strip()
                if sku_col and sku_col in row and pd.notna(row[sku_col])
                else None
            )
            if not sku_val:
                continue

            qty_val = (
                float(row[qty_col])
                if qty_col and qty_col in row and pd.notna(row[qty_col])
                else 1.0
            )

            # Date parsing
            date_val = None
            if date_col and date_col in row and pd.notna(row[date_col]):
                try:
                    date_val = pd.to_datetime(row[date_col]).to_pydatetime()
                except Exception:
                    date_val = datetime.utcnow()
            else:
                date_val = datetime.utcnow()

            price_val = (
                float(row[price_col])
                if price_col and price_col in row and pd.notna(row[price_col])
                else 100.0
            )
            cost_val = (
                float(row[cost_col])
                if cost_col and cost_col in row and pd.notna(row[cost_col])
                else 40.0
            )
            rev_val = (
                float(row[rev_col])
                if rev_col and rev_col in row and pd.notna(row[rev_col])
                else (qty_val * price_val)
            )

            prod_name = (
                str(row[prod_name_col]).strip()
                if prod_name_col
                and prod_name_col in row
                and pd.notna(row[prod_name_col])
                else f"Organic {sku_val} Item"
            )
            cat_val = (
                str(row[cat_col]).strip()
                if cat_col and cat_col in row and pd.notna(row[cat_col])
                else "General"
            )
            wh_name = (
                str(row[wh_col]).strip()
                if wh_col and wh_col in row and pd.notna(row[wh_col])
                else "Warehouse A"
            )

            if sku_val not in seen_skus:
                seen_skus.add(sku_val)
                products.append(
                    {
                        "sku": sku_val,
                        "product_name": prod_name,
                        "category": cat_val,
                        "unit_cost": cost_val,
                        "unit_price": price_val,
                    }
                )
                inventory.append(
                    {"sku": sku_val, "warehouse": wh_name, "current_stock": qty_val}
                )

            sales.append(
                {
                    "sku": sku_val,
                    "date": date_val,
                    "quantity_sold": qty_val,
                    "revenue": rev_val,
                    "warehouse": wh_name,
                }
            )

        return {"products": products, "inventory": inventory, "sales": sales}


class XLSXAdapter(CSVAdapter):
    def parse(self) -> Dict[str, List[Dict[str, Any]]]:
        df = pd.read_excel(io.BytesIO(self.data))
        return self._normalize_df(df)


class ShopifyAdapter(BaseAdapter):
    def parse(self) -> Dict[str, List[Dict[str, Any]]]:
        import random

        random.seed(42)

        products = []
        inventory = []
        sales = []

        shopify_skus = ["SKU-101", "SKU-205", "SKU-330", "SKU-440", "SKU-555"]
        categories = [
            "Beverages",
            "Snacks",
            "Personal Care",
            "Home Care",
            "Packaged Food",
        ]
        names = [
            "Organic Energy Drink",
            "Spiced Potato Chips",
            "Moisturizing Face Wash",
            "Eco Laundry Detergent",
            "Whole Wheat Bread",
        ]
        prices = [150.0, 80.0, 299.0, 450.0, 60.0]
        costs = [60.0, 30.0, 120.0, 200.0, 25.0]

        for i, sku in enumerate(shopify_skus):
            products.append(
                {
                    "sku": sku,
                    "product_name": f"[Shopify] {names[i]}",
                    "category": categories[i],
                    "unit_cost": costs[i],
                    "unit_price": prices[i],
                }
            )
            inventory.append(
                {
                    "sku": sku,
                    "warehouse": "Warehouse A",
                    "current_stock": float(random.randint(100, 500)),
                }
            )
            for day in range(20):
                qty = random.randint(5, 20)
                sales.append(
                    {
                        "sku": sku,
                        "date": datetime.utcnow() - timedelta(days=day),
                        "quantity_sold": float(qty),
                        "revenue": qty * prices[i],
                        "warehouse": "Warehouse A",
                    }
                )

        return {"products": products, "inventory": inventory, "sales": sales}


class OdooAdapter(BaseAdapter):
    def parse(self) -> Dict[str, List[Dict[str, Any]]]:
        import random

        random.seed(99)

        products = []
        inventory = []
        sales = []

        odoo_skus = ["SKU-330", "SKU-440", "SKU-601", "SKU-702"]
        categories = ["Personal Care", "Home Care", "Nutrition", "Pharmacy"]
        names = [
            "Moisturizing Face Wash",
            "Eco Laundry Detergent",
            "Premium Whey Protein",
            "Paracetamol",
        ]
        prices = [299.0, 450.0, 2499.0, 45.0]
        costs = [120.0, 200.0, 1200.0, 12.0]

        for i, sku in enumerate(odoo_skus):
            products.append(
                {
                    "sku": sku,
                    "product_name": f"[Odoo] {names[i]}",
                    "category": categories[i],
                    "unit_cost": costs[i],
                    "unit_price": prices[i],
                }
            )
            inventory.append(
                {
                    "sku": sku,
                    "warehouse": "Warehouse B",
                    "current_stock": float(random.randint(50, 250)),
                }
            )
            for day in range(15):
                qty = random.randint(2, 10)
                sales.append(
                    {
                        "sku": sku,
                        "date": datetime.utcnow() - timedelta(days=day),
                        "quantity_sold": float(qty),
                        "revenue": qty * prices[i],
                        "warehouse": "Warehouse B",
                    }
                )

        return {"products": products, "inventory": inventory, "sales": sales}


class ZohoInventoryAdapter(BaseAdapter):
    def parse(self) -> Dict[str, List[Dict[str, Any]]]:
        import random

        random.seed(111)

        products = []
        inventory = []
        sales = []

        zoho_skus = ["SKU-101", "SKU-555", "SKU-810"]
        categories = ["Beverages", "Packaged Food", "Electronics"]
        names = ["Organic Energy Drink", "Whole Wheat Bread", "Wireless Headphones"]
        prices = [150.0, 60.0, 3999.0]
        costs = [60.0, 25.0, 1800.0]

        for i, sku in enumerate(zoho_skus):
            products.append(
                {
                    "sku": sku,
                    "product_name": f"[Zoho] {names[i]}",
                    "category": categories[i],
                    "unit_cost": costs[i],
                    "unit_price": prices[i],
                }
            )
            inventory.append(
                {
                    "sku": sku,
                    "warehouse": "Warehouse C",
                    "current_stock": float(random.randint(10, 80)),
                }
            )
            for day in range(25):
                qty = random.randint(1, 5)
                sales.append(
                    {
                        "sku": sku,
                        "date": datetime.utcnow() - timedelta(days=day),
                        "quantity_sold": float(qty),
                        "revenue": qty * prices[i],
                        "warehouse": "Warehouse C",
                    }
                )

        return {"products": products, "inventory": inventory, "sales": sales}
