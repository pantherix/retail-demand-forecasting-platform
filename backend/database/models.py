from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Roles ─────────────────────────────────────────────────────────────────────
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(100), unique=True, nullable=False)
    permissions = Column(JSON, default=dict)  # {"can_approve_po": true, "can_transfer": true}
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    username   = Column(String(100), unique=True, nullable=False)
    full_name  = Column(String(255))
    hashed_pw  = Column(String(255), nullable=False)
    role       = Column(String(50), default="analyst")   # admin | manager | analyst
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Suppliers ─────────────────────────────────────────────────────────────────
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    lead_time_days = Column(Integer, default=7)
    reliability_score = Column(Float, default=95.0)  # 0 to 100
    fill_rate = Column(Float, default=98.0)          # 0 to 100
    contact_info = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    products = relationship("Product", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


# ── Products (SKUs) ───────────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), index=True)
    subcategory = Column(String(100), nullable=True)
    base_price = Column(Float, nullable=False, default=0.0)
    unit_cost = Column(Float, nullable=False, default=0.0)
    lead_time_days = Column(Integer, default=7)
    safety_stock = Column(Float, default=0.0)
    reorder_point = Column(Float, default=0.0)
    abc_class = Column(String(10), default="C")  # A | B | C
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="products")
    inventory_items = relationship("InventoryItem", back_populates="product", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="product", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="product", cascade="all, delete-orphan")
    risk_scores = relationship("RiskScore", back_populates="product", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="product", cascade="all, delete-orphan")
    transfers = relationship("InventoryTransfer", back_populates="product", cascade="all, delete-orphan")


# ── Warehouses ────────────────────────────────────────────────────────────────
class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    location = Column(String(255), nullable=True)
    capacity = Column(Float, default=10000.0)  # max units
    utilization = Column(Float, default=0.0)    # percent 0 to 100
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory_items = relationship("InventoryItem", back_populates="warehouse", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="warehouse", cascade="all, delete-orphan")
    transfers_from = relationship("InventoryTransfer", foreign_keys="[InventoryTransfer.from_warehouse_id]", back_populates="from_warehouse", cascade="all, delete-orphan")
    transfers_to = relationship("InventoryTransfer", foreign_keys="[InventoryTransfer.to_warehouse_id]", back_populates="to_warehouse", cascade="all, delete-orphan")


# ── Inventory (Stock on Hand) ─────────────────────────────────────────────────
class InventoryItem(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    current_stock = Column(Float, default=0.0)
    safety_stock_override = Column(Float, nullable=True)
    reorder_point_override = Column(Float, nullable=True)
    minimum_order_qty = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="inventory_items")
    warehouse = relationship("Warehouse", back_populates="inventory_items")


# ── Sales ─────────────────────────────────────────────────────────────────────
class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)
    price = Column(Float, nullable=False, default=0.0)
    cost = Column(Float, nullable=False, default=0.0)
    transaction_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="sales")
    warehouse = relationship("Warehouse", back_populates="sales")


# ── Forecasts ─────────────────────────────────────────────────────────────────
class Forecast(Base):
    __tablename__ = "forecasts_new"  # unique name to avoid conflicts with old run table

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    forecast_date = Column(DateTime, nullable=False, index=True)
    expected_demand = Column(Float, nullable=False, default=0.0)
    forecast_confidence = Column(Float, default=80.0)  # MAPE/Accuracy based
    accuracy = Column(Float, default=80.0)             # Historical Accuracy score
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="forecasts")


# ── Risk Scores ───────────────────────────────────────────────────────────────
class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    revenue_at_risk = Column(Float, default=0.0)
    profit_at_risk = Column(Float, default=0.0)
    financial_priority = Column(Integer, default=3)      # 1 = Critical, 2 = High, 3 = Med, 4 = Low
    forecast_confidence = Column(Float, default=85.0)     # confidence metric from forecast run
    expected_stockout_days = Column(Float, default=0.0)
    recommended_action = Column(String(100), default="Monitor")
    urgency = Column(Float, default=0.0)                  # 0 to 1
    root_causes = Column(JSON, default=list)              # ["low stock", "lead time delay"]
    service_level = Column(Float, default=95.0)           # expected service level
    reorder_quantity = Column(Float, default=0.0)
    assigned_to = Column(String(100), nullable=True)      # username of assigned operator
    status = Column(String(50), default="Open")           # Open | In Progress | Resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="risk_scores")


# ── Purchase Orders ───────────────────────────────────────────────────────────
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    expected_delivery_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="Draft")  # Draft | Pending Approval | Ordered | In Transit | Delivered | Cancelled
    total_cost = Column(Float, default=0.0)
    details = Column(JSON, default=list)  # [{"sku": "SKU-101", "quantity": 100, "unit_cost": 1.8}]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="purchase_orders")


# ── Transfers ─────────────────────────────────────────────────────────────────
class InventoryTransfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, default=0.0)
    status = Column(String(50), default="Pending")  # Pending | Shipped | Received | Cancelled
    transfer_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id], back_populates="transfers_from")
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id], back_populates="transfers_to")
    product = relationship("Product", back_populates="transfers")


# ── Alerts ────────────────────────────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    type = Column(String(100), nullable=False)  # Stockout Risk | Overstock | Revenue Exposure | Supplier Delay
    message = Column(String(500), nullable=False)
    severity = Column(String(50), default="Medium")  # Critical | High | Medium | Low
    status = Column(String(50), default="Active")     # Active | Snoozed | Resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="alerts")


# ── Datasets (Compatibility) ──────────────────────────────────────────────────
class Dataset(Base):
    __tablename__ = "datasets"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(255), nullable=False)
    filename      = Column(String(255))
    rows          = Column(Integer)
    columns       = Column(Integer)
    sku_count     = Column(Integer)
    quality_score = Column(Float)
    date_from     = Column(String(20))
    date_to       = Column(String(20))
    owner         = Column(String(100))
    uploaded_at   = Column(DateTime, default=datetime.utcnow)


# ── Forecast Runs (Compatibility) ─────────────────────────────────────────────
class ForecastRun(Base):
    __tablename__ = "forecasts"

    id          = Column(Integer, primary_key=True, index=True)
    sku         = Column(String(100), nullable=False, index=True)
    model_name  = Column(String(100))
    horizon     = Column(Integer)
    total_forecast = Column(Float)
    mae         = Column(Float)
    rmse        = Column(Float)
    mape        = Column(Float)
    dataset_id  = Column(Integer)
    created_at  = Column(DateTime, default=datetime.utcnow)


# ── Training Runs (Compatibility) ─────────────────────────────────────────────
class TrainingRun(Base):
    __tablename__ = "training_runs"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), nullable=False)
    model_name = Column(String(100))
    rmse = Column(Float)
    mae = Column(Float)
    mape = Column(Float)
    samples = Column(Integer)
    features = Column(Integer)
    dataset_id = Column(Integer)
    model_path = Column(String(500))
    trained_at = Column(DateTime, default=datetime.utcnow)


# ── Simulation Runs (Compatibility) ───────────────────────────────────────────
class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100))
    scenario_name = Column(String(100))
    baseline_forecast = Column(Float)
    simulated_demand = Column(Float)
    revenue = Column(Float)
    profit = Column(Float)
    stockout_risk = Column(String(20))
    inventory_gap = Column(Float)
    params = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Reports (Compatibility) ───────────────────────────────────────────────────
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(50))   # executive | risk | forecast
    file_path = Column(String(500))
    generated_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Audit Log (Compatibility) ─────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(100))
    action = Column(String(100))
    resource = Column(String(100))
    detail = Column(Text)
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
