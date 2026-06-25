"""Enterprise intelligence schema for Decision Intelligence System."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from backend.database.models import Base


class DecisionSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionAction(str, Enum):
    ORDER_NOW = "order_now"
    INCREASE_ORDER = "increase_order"
    HOLD = "hold"
    REDUCE_ORDER = "reduce_order"
    LIQUIDATE = "liquidate"
    MONITOR = "monitor"


class DataQualityLevel(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


# ── Financial Impact & Decisions ──────────────────────────────────────────────
class FinancialImpact(Base):
    __tablename__ = "financial_impacts"
    __table_args__ = (
        Index("ix_financial_impacts_sku_created", "sku", "created_at"),
        Index("ix_financial_impacts_portfolio_date", "portfolio_id", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    portfolio_id = Column(String(100), nullable=False, index=True)
    sku = Column(String(100), nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)

    # Financial Metrics
    revenue_at_risk = Column(Float, default=0.0)
    potential_loss = Column(Float, default=0.0)
    potential_savings = Column(Float, default=0.0)
    inventory_carrying_cost = Column(Float, default=0.0)
    stockout_cost = Column(Float, default=0.0)

    # Forecast Impact
    demand_forecast = Column(Float)
    forecast_confidence = Column(Float)
    forecast_accuracy_score = Column(Float)

    # Inventory Impact
    current_stock = Column(Float)
    days_of_cover = Column(Float)
    reorder_point = Column(Float)
    safety_stock = Column(Float)

    # Decision
    recommended_action = Column(String(50), default=DecisionAction.MONITOR.value)
    action_priority = Column(Integer, default=0)
    urgency_score = Column(Float, default=0.0)

    # Explainability
    impact_drivers = Column(JSON, default=dict)
    risk_factors = Column(JSON, default=dict)
    confidence_interval = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Decision Feed (Action-Oriented) ────────────────────────────────────────────
class DecisionFeedItem(Base):
    __tablename__ = "decision_feed_items"
    __table_args__ = (
        Index("ix_decision_feed_created", "created_at"),
        Index("ix_decision_feed_severity", "severity"),
        Index("ix_decision_feed_acknowledged", "is_acknowledged"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Feed Metadata
    portfolio_id = Column(String(100), nullable=False, index=True)
    decision_id = Column(String(100), nullable=False, unique=True)

    # Content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    action_required = Column(String(100), nullable=False)

    # Context
    sku = Column(String(100), nullable=False)
    category = Column(String(100))
    severity = Column(String(20), default=DecisionSeverity.MEDIUM.value)

    # Financial Impact
    financial_impact = Column(Float, default=0.0)
    impact_type = Column(String(50))  # revenue_risk, cost_reduction, margin_improvement

    # Execution
    estimated_execution_time_min = Column(Float, default=0.0)
    estimated_execution_time_max = Column(Float, default=0.0)
    estimated_effort_points = Column(Float, default=0.0)

    # Metadata
    supporting_data = Column(JSON, default=dict)
    explainability = Column(JSON, default=dict)
    related_skus = Column(JSON, default=list)

    # Lifecycle
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    is_actioned = Column(Boolean, default=False)
    actioned_by = Column(String(100), nullable=True)
    actioned_at = Column(DateTime, nullable=True)
    action_result = Column(JSON, default=dict)

    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── SKU Intelligence & Profiling ───────────────────────────────────────────────
class SKUProfile(Base):
    __tablename__ = "sku_profiles"
    __table_args__ = (
        Index("ix_sku_profiles_portfolio", "portfolio_id"),
        Index("ix_sku_profiles_updated", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    portfolio_id = Column(String(100), nullable=False, index=True)
    sku = Column(String(100), nullable=False, index=True)
    sku_name = Column(String(255))
    category = Column(String(100))
    subcategory = Column(String(100))
    supplier_id = Column(String(100))

    # Classification
    revenue_contributor = Column(String(50))  # top_tier, growth, niche, declining
    inventory_class = Column(String(20))  # A, B, C
    demand_pattern = Column(String(50))  # steady, seasonal, trending, volatile

    # Financial Metrics (12-month rolling)
    annual_revenue = Column(Float, default=0.0)
    gross_margin_pct = Column(Float, default=0.0)
    margin_contribution = Column(Float, default=0.0)

    # Inventory Metrics
    avg_daily_sales = Column(Float, default=0.0)
    inventory_turnover = Column(Float, default=0.0)
    stockout_frequency_12m = Column(Integer, default=0)
    overstock_frequency_12m = Column(Integer, default=0)

    # Forecast Health
    forecast_accuracy_mape = Column(Float, default=0.0)
    forecast_bias = Column(Float, default=0.0)
    forecast_volatility = Column(Float, default=0.0)
    model_name = Column(String(100))

    # Risk Profile
    data_quality_level = Column(String(20), default=DataQualityLevel.GOOD.value)
    demand_volatility_index = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=0)
    minimum_order_quantity = Column(Integer, default=1)

    # Performance Score
    overall_health_score = Column(Float, default=0.0)

    # Drill-down Data
    variance_analysis = Column(JSON, default=dict)
    segment_performance = Column(JSON, default=dict)
    seasonal_factors = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Revenue at Risk Analysis ───────────────────────────────────────────────────
class RevenueAtRisk(Base):
    __tablename__ = "revenue_at_risk"
    __table_args__ = (
        Index("ix_rar_portfolio_date", "portfolio_id", "analysis_date"),
        Index("ix_rar_severity", "severity_classification"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    portfolio_id = Column(String(100), nullable=False, index=True)
    analysis_date = Column(DateTime, default=datetime.utcnow, index=True)
    horizon_days = Column(Integer, default=30)

    # Portfolio Level
    total_potential_revenue_at_risk = Column(Float, default=0.0)
    total_stockout_cost_exposure = Column(Float, default=0.0)
    total_overstock_cost_exposure = Column(Float, default=0.0)
    total_opportunity_cost = Column(Float, default=0.0)

    # Distribution
    skus_at_risk_count = Column(Integer, default=0)
    critical_stockouts_projected = Column(Integer, default=0)
    excess_inventory_skus = Column(Integer, default=0)

    # Classification
    severity_classification = Column(String(20), default=DecisionSeverity.MEDIUM.value)

    # Mitigation
    potential_mitigation_revenue = Column(Float, default=0.0)
    recommended_actions_count = Column(Integer, default=0)

    # Details
    sku_breakdown = Column(JSON, default=dict)
    risk_by_category = Column(JSON, default=dict)
    time_series_projection = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)


# ── Advanced Filtering & Search ────────────────────────────────────────────────
class SearchFilter(Base):
    __tablename__ = "search_filters"
    __table_args__ = (Index("ix_search_filters_user", "user_id"),)

    id = Column(Integer, primary_key=True, index=True)

    # Ownership
    user_id = Column(String(100), nullable=False, index=True)
    portfolio_id = Column(String(100), nullable=False)

    # Filter Definition
    name = Column(String(100), nullable=False)
    description = Column(Text)
    filter_type = Column(String(50))  # saved, dynamic, alert

    # Criteria (JSON for flexibility)
    criteria = Column(JSON, default=dict)

    # Metadata
    is_pinned = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Data Quality Monitoring ────────────────────────────────────────────────────
class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"
    __table_args__ = (Index("ix_dqr_portfolio_date", "portfolio_id", "report_date"),)

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    portfolio_id = Column(String(100), nullable=False, index=True)
    report_date = Column(DateTime, default=datetime.utcnow, index=True)
    data_period_from = Column(DateTime)
    data_period_to = Column(DateTime)

    # Overall Quality
    overall_quality_score = Column(Float, default=0.0)
    completeness_pct = Column(Float, default=100.0)
    accuracy_score = Column(Float, default=0.0)
    consistency_score = Column(Float, default=0.0)
    timeliness_score = Column(Float, default=0.0)

    # Record Statistics
    total_records = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    invalid_records = Column(Integer, default=0)
    missing_values = Column(Integer, default=0)
    duplicate_records = Column(Integer, default=0)
    outliers_detected = Column(Integer, default=0)

    # Issues
    issues_found = Column(JSON, default=dict)
    warnings = Column(JSON, default=list)
    remediation_steps = Column(JSON, default=list)

    # Field-Level Quality
    field_quality_scores = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)


# ── Audit & Compliance History ────────────────────────────────────────────────
class DecisionAuditLog(Base):
    __tablename__ = "decision_audit_logs"
    __table_args__ = (
        Index("ix_audit_log_user_date", "user_id", "event_date"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Actor & Context
    user_id = Column(String(100), nullable=False, index=True)
    user_email = Column(String(255))
    user_role = Column(String(50))

    # Event
    event_type = Column(
        String(100), nullable=False
    )  # view, filter, export, acknowledge, action
    event_date = Column(DateTime, default=datetime.utcnow, index=True)

    # Resource
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255), nullable=False, index=True)
    portfolio_id = Column(String(100), nullable=False)

    # Change
    change_before = Column(JSON, nullable=True)
    change_after = Column(JSON, nullable=True)

    # Details
    description = Column(Text)
    ip_address = Column(String(50))
    session_id = Column(String(100))

    # Compliance
    is_export = Column(Boolean, default=False)
    export_format = Column(String(50), nullable=True)
    export_row_count = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ── Export & Report History ────────────────────────────────────────────────────
class ExportRecord(Base):
    __tablename__ = "export_records"
    __table_args__ = (Index("ix_export_user_date", "user_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)

    # Ownership
    user_id = Column(String(100), nullable=False, index=True)
    portfolio_id = Column(String(100), nullable=False)

    # Export Details
    export_type = Column(String(50), nullable=False)  # csv, excel, pdf, json
    format_details = Column(JSON, default=dict)

    # Content
    exported_resource = Column(String(100), nullable=False)  # decisions, skus, rar, etc
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    file_size_bytes = Column(Integer, default=0)

    # File Info
    file_path = Column(String(500))
    file_hash = Column(String(64))
    s3_uri = Column(String(255), nullable=True)

    # Metadata
    title = Column(String(255))
    description = Column(Text)
    filters_applied = Column(JSON, default=dict)

    # Retention & Security
    retention_days = Column(Integer, default=90)
    expires_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False)
    access_log = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    downloaded_at = Column(DateTime, nullable=True)


# ── Recommendation Engine ──────────────────────────────────────────────────────
class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_portfolio_created", "portfolio_id", "created_at"),
        Index("ix_recommendations_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    portfolio_id = Column(String(100), nullable=False, index=True)
    recommendation_id = Column(String(100), nullable=False, unique=True)
    sku = Column(String(100), nullable=False, index=True)

    # Content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    recommendation_type = Column(String(50))  # order, hold, liquidate, monitor

    # Reasoning
    rule_id = Column(String(100))
    confidence_score = Column(Float, default=0.0)
    supporting_metrics = Column(JSON, default=dict)
    model_explanation = Column(JSON, default=dict)

    # Impact
    predicted_impact_revenue = Column(Float, default=0.0)
    predicted_impact_cost = Column(Float, default=0.0)
    predicted_impact_margin = Column(Float, default=0.0)

    # Parameters
    recommended_quantity = Column(Float, nullable=True)
    recommended_timing = Column(DateTime, nullable=True)
    price_point_suggested = Column(Float, nullable=True)

    # Lifecycle
    status = Column(
        String(50), default="active"
    )  # active, implemented, rejected, expired
    implementation_deadline = Column(DateTime, nullable=True)

    # Feedback
    user_feedback = Column(String(50), nullable=True)  # useful, neutral, not_useful
    user_notes = Column(Text, nullable=True)

    # Tracking
    implementation_notes = Column(Text, nullable=True)
    actual_results = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
