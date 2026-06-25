from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from backend.database.models import AuditLog, InventoryTransfer, PurchaseOrder

logger = logging.getLogger("retailgpt.integration")


class IntegrationService:
    @staticmethod
    def sync_purchase_order_to_external(
        db: Session, po: PurchaseOrder, operator: str
    ) -> Dict[str, Any]:
        """
        Simulates pushing an Approved PO to Shopify and Zoho Inventory APIs.
        Logs payloads, headers, URLs, and mocks JSON responses.
        """
        po_cost = po.total_cost
        details = po.details

        # 1. PUSH TO SHOPIFY
        # Mocks creating a draft order or purchasing sync
        shopify_url = (
            "https://retailgpt-enterprise.myshopify.com/admin/api/2024-04/orders.json"
        )
        shopify_payload = {
            "order": {
                "line_items": [
                    {
                        "title": item.get("product_name"),
                        "quantity": item.get("quantity"),
                        "price": item.get("unit_cost"),
                    }
                    for item in details
                ],
                "financial_status": "pending",
                "note": f"Auto-generated PO-{po.id} from RetailGPT stress mitigation",
            }
        }

        logger.info(f"[SHOPIFY SYNC] POST {shopify_url} | Payload: {shopify_payload}")
        # Simulated response from Shopify
        shopify_response = {
            "order": {
                "id": 89472938472,
                "created_at": "2026-06-05T17:50:00Z",
                "total_price": str(po_cost),
                "currency": "INR",
                "status": "created",
            }
        }

        # Log Shopify Sync to AuditLog
        shopify_log = AuditLog(
            user=operator,
            action="shopify_sync_po",
            resource=f"PO {po.id}",
            detail=f"Synced PO-{po.id} (₹{po_cost:,.2f}) to Shopify Order ID 89472938472",
            ip_address="127.0.0.1",
        )
        db.add(shopify_log)

        # 2. PUSH TO ZOHO INVENTORY
        zoho_url = "https://inventory.zoho.com/api/v1/purchaseorders"
        zoho_payload = {
            "purchaseorder_number": f"PO-{po.id}",
            "date": "2026-06-05",
            "delivery_date": (
                po.expected_delivery_date.date().isoformat()
                if po.expected_delivery_date
                else None
            ),
            "line_items": [
                {
                    "name": item.get("product_name"),
                    "quantity": item.get("quantity"),
                    "rate": item.get("unit_cost"),
                }
                for item in details
            ],
            "custom_fields": [
                {"label": "TriggerSource", "value": "RetailGPT Decision Engine"}
            ],
        }

        logger.info(f"[ZOHO SYNC] POST {zoho_url} | Payload: {zoho_payload}")
        # Simulated response from Zoho
        zoho_response = {
            "code": 0,
            "message": "Purchase Order has been created.",
            "purchaseorder": {
                "purchaseorder_id": "zoho_po_987654",
                "purchaseorder_number": f"PO-{po.id}",
                "status": "issued",
            },
        }

        # Log Zoho Sync to AuditLog
        zoho_log = AuditLog(
            user=operator,
            action="zoho_sync_po",
            resource=f"PO {po.id}",
            detail=f"Synced PO-{po.id} (₹{po_cost:,.2f}) to Zoho PO ID zoho_po_987654",
            ip_address="127.0.0.1",
        )
        db.add(zoho_log)
        db.commit()

        return {
            "shopify": {"status_code": 201, "response": shopify_response},
            "zoho": {"status_code": 200, "response": zoho_response},
        }

    @staticmethod
    def sync_transfer_to_external(
        db: Session,
        transfer: InventoryTransfer,
        sku: str,
        from_wh: str,
        to_wh: str,
        operator: str,
    ) -> Dict[str, Any]:
        """
        Simulates pushing a Stock Transfer to Shopify and Zoho Inventory.
        """
        # 1. PUSH TO SHOPIFY INVENTORY ADJUSTMENT
        # Mocks adjusting quantity in Shopify locations
        shopify_url = "https://retailgpt-enterprise.myshopify.com/admin/api/2024-04/inventory_levels/adjust.json"
        shopify_payload = {
            "location_id": 98452,
            "inventory_item_id": 10294,
            "available_adjustment": -int(transfer.quantity),
        }

        logger.info(f"[SHOPIFY SYNC] POST {shopify_url} | Payload: {shopify_payload}")
        shopify_response = {
            "inventory_level": {
                "inventory_item_id": 10294,
                "location_id": 98452,
                "available": 150,
            }
        }

        shopify_log = AuditLog(
            user=operator,
            action="shopify_sync_transfer",
            resource=f"Transfer {transfer.id}",
            detail=f"Adjusted Shopify Location 98452 stock for SKU {sku} by -{transfer.quantity:.0f} units",
            ip_address="127.0.0.1",
        )
        db.add(shopify_log)

        # 2. PUSH TO ZOHO TRANSFER ORDER
        zoho_url = "https://inventory.zoho.com/api/v1/transferorders"
        zoho_payload = {
            "from_warehouse_name": from_wh,
            "to_warehouse_name": to_wh,
            "transfer_number": f"TO-{transfer.id}",
            "line_items": [{"sku": sku, "quantity": transfer.quantity}],
        }

        logger.info(f"[ZOHO SYNC] POST {zoho_url} | Payload: {zoho_payload}")
        zoho_response = {
            "code": 0,
            "message": "Transfer Order has been created.",
            "transfer_order": {
                "transfer_order_id": "zoho_to_345678",
                "transfer_number": f"TO-{transfer.id}",
                "status": "pending",
            },
        }

        zoho_log = AuditLog(
            user=operator,
            action="zoho_sync_transfer",
            resource=f"Transfer {transfer.id}",
            detail=f"Created Zoho Transfer Order TO-{transfer.id} (zoho_to_345678)",
            ip_address="127.0.0.1",
        )
        db.add(zoho_log)
        db.commit()

        return {
            "shopify": {"status_code": 200, "response": shopify_response},
            "zoho": {"status_code": 200, "response": zoho_response},
        }
