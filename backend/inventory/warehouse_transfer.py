from __future__ import annotations

from typing import Dict, List


class WarehouseTransferOptimizer:
    """Recommends inter-warehouse stock transfers to balance inventory."""

    def optimize_transfer(
        self,
        sku: str,
        warehouses: List[Dict],
        forecast: float,
    ) -> Dict:
        """
        Given a list of warehouses with their stock levels and a shared forecast,
        recommend transfers from overstocked to understocked warehouses.
        """
        total_stock = sum(w.get("stock", 0) for w in warehouses)
        per_warehouse_target = forecast / max(len(warehouses), 1)
        transfers = []

        surplus = []
        deficit = []

        for w in warehouses:
            stock = w.get("stock", 0)
            name = w.get("name", "unknown")
            diff = stock - per_warehouse_target
            if diff > 0:
                surplus.append({"name": name, "surplus": diff})
            elif diff < 0:
                deficit.append({"name": name, "deficit": abs(diff)})

        for d in deficit:
            for s in surplus:
                transfer_qty = min(s["surplus"], d["deficit"])
                if transfer_qty > 0:
                    transfers.append(
                        {
                            "from": s["name"],
                            "to": d["name"],
                            "sku": sku,
                            "quantity": round(transfer_qty, 2),
                        }
                    )
                    s["surplus"] -= transfer_qty
                    d["deficit"] -= transfer_qty

        return {
            "sku": sku,
            "total_stock": total_stock,
            "per_warehouse_target": round(per_warehouse_target, 2),
            "transfers": transfers,
            "transfer_count": len(transfers),
        }


warehouse_transfer_optimizer = WarehouseTransferOptimizer()
