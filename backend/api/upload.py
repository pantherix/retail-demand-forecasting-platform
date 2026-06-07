from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
import pandas as pd
import io
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import SalesRecord, InventoryRecord, SupplierRecord
from services.risk import detect_risks

router = APIRouter(prefix="/upload", tags=["Data Upload"])

@router.post("/csv", status_code=201)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {e}")
    # Expected columns: sku, demand, inventory, unit_price, supplier_name
    required_cols = {"sku", "demand", "inventory", "unit_price", "supplier_name"}
    if not required_cols.issubset(set(df.columns)):
        raise HTTPException(status_code=400, detail=f"CSV missing required columns: {required_cols - set(df.columns)}")
    # Upsert records
    for _, row in df.iterrows():
        # Inventory
        inv = db.query(InventoryRecord).filter_by(sku=row["sku"]).first()
        if inv:
            inv.inventory = row["inventory"]
            inv.unit_price = row["unit_price"]
        else:
            inv = InventoryRecord(sku=row["sku"], inventory=row["inventory"], unit_price=row["unit_price"])
            db.add(inv)
        # Supplier
        sup = db.query(SupplierRecord).filter_by(name=row["supplier_name"]).first()
        if not sup:
            sup = SupplierRecord(name=row["supplier_name"])
            db.add(sup)
        # Sales (historical demand)
        sale = db.query(SalesRecord).filter_by(sku=row["sku"]).first()
        if sale:
            sale.demand = row["demand"]
        else:
            sale = SalesRecord(sku=row["sku"], demand=row["demand"])
            db.add(sale)
    db.commit()
    # Detect risks after ingest
    risks = detect_risks(db)
    return {"status": "uploaded", "rows": len(df), "risks": risks}
