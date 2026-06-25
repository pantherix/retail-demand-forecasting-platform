"""Decision Intelligence API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_manager
from backend.database.intelligence import (
    DecisionAuditLog,
    DecisionFeedItem,
    ExportRecord,
    FinancialImpact,
    RevenueAtRisk,
    SKUProfile,
)
from backend.database.models import User
from backend.database.session import get_db
from backend.intelligence.engine import (
    DataQualityMonitor,
    DecisionFeedGenerator,
    FinancialImpactAnalyzer,
    RevenueAtRiskAnalyzer,
    SKUIntelligenceEngine,
)

router = APIRouter(prefix="/intelligence", tags=["Decision Intelligence"])


# ── Request/Response Models ───────────────────────────────────────────────────
class FinancialImpactRequest(BaseModel):
    portfolio_id: str
    sku: str
    current_stock: float
    demand_forecast: float
    forecast_accuracy: float
    daily_sales_rate: float
    unit_cost: float
    retail_price: float
    lead_time_days: int
    safety_stock: float
    reorder_point: float
    carrying_cost_pct: float = 0.25
    stockout_cost_multiplier: float = 2.5


class DecisionFeedRequest(BaseModel):
    portfolio_id: str
    skus: List[str] = []
    severity_filter: Optional[List[str]] = None
    action_filter: Optional[List[str]] = None
    limit: int = Field(default=50, ge=1, le=1000)
    sort_by: str = "urgency"  # urgency, severity, financial_impact, created
    include_acknowledged: bool = False


class SearchFilterRequest(BaseModel):
    name: str
    description: Optional[str] = None
    filter_type: str  # saved, dynamic, alert
    criteria: Dict[str, Any]
    is_pinned: bool = False


class ExportRequest(BaseModel):
    portfolio_id: str
    export_type: str  # csv, excel, pdf, json
    exported_resource: str
    title: str
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    include_metadata: bool = True


# ── Financial Impact Analysis ─────────────────────────────────────────────────
@router.post("/financial-impact/compute")
def compute_financial_impact(
    payload: FinancialImpactRequest, db: Session = Depends(get_db)
):
    """Compute comprehensive financial impact for a SKU."""
    try:
        impact = FinancialImpactAnalyzer.compute_impact(
            sku=payload.sku,
            portfolio_id=payload.portfolio_id,
            current_stock=payload.current_stock,
            demand_forecast=payload.demand_forecast,
            forecast_accuracy=payload.forecast_accuracy,
            daily_sales_rate=payload.daily_sales_rate,
            unit_cost=payload.unit_cost,
            retail_price=payload.retail_price,
            lead_time_days=payload.lead_time_days,
            safety_stock=payload.safety_stock,
            reorder_point=payload.reorder_point,
            carrying_cost_pct=payload.carrying_cost_pct,
            stockout_cost_multiplier=payload.stockout_cost_multiplier,
        )

        # Store in database
        db_impact = FinancialImpact(
            portfolio_id=payload.portfolio_id,
            sku=payload.sku,
            date=datetime.utcnow(),
            revenue_at_risk=impact["revenue_at_risk"],
            potential_loss=impact["potential_loss"],
            potential_savings=impact["potential_savings"],
            inventory_carrying_cost=impact["inventory_carrying_cost"],
            stockout_cost=impact["stockout_cost"],
            demand_forecast=payload.demand_forecast,
            forecast_confidence=payload.forecast_accuracy,
            current_stock=payload.current_stock,
            days_of_cover=impact["days_of_cover"],
            reorder_point=payload.reorder_point,
            safety_stock=payload.safety_stock,
            recommended_action=impact["action"],
            urgency_score=impact["urgency_score"],
            impact_drivers=impact["impact_drivers"],
            risk_factors=impact["risk_factors"],
            confidence_interval=impact["confidence_interval"],
        )
        db.add(db_impact)
        db.commit()
        db.refresh(db_impact)

        return {
            "success": True,
            "impact": impact,
            "stored_id": db_impact.id,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/financial-impact/portfolio/{portfolio_id}")
def get_portfolio_impacts(
    portfolio_id: str,
    days: int = Query(1, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get recent financial impacts for a portfolio."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        impacts = (
            db.query(FinancialImpact)
            .filter(
                FinancialImpact.portfolio_id == portfolio_id,
                FinancialImpact.date >= cutoff_date,
            )
            .all()
        )

        return {
            "portfolio_id": portfolio_id,
            "count": len(impacts),
            "impacts": [
                {
                    "id": i.id,
                    "sku": i.sku,
                    "revenue_at_risk": i.revenue_at_risk,
                    "days_of_cover": i.days_of_cover,
                    "action": i.recommended_action,
                    "severity": i.impact_drivers.get("severity", "unknown"),
                    "created_at": i.created_at.isoformat(),
                }
                for i in impacts
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Decision Feed ─────────────────────────────────────────────────────────────
@router.post("/feed/generate")
def generate_decision_feed(payload: DecisionFeedRequest, db: Session = Depends(get_db)):
    """Generate action-oriented decision feed."""
    try:
        query = db.query(FinancialImpact).filter(
            FinancialImpact.portfolio_id == payload.portfolio_id,
        )

        if payload.skus:
            query = query.filter(FinancialImpact.sku.in_(payload.skus))

        if payload.severity_filter:
            query = query.filter(
                FinancialImpact.impact_drivers.contains(
                    {"severity": payload.severity_filter[0]}
                )
            )

        impacts = query.all()

        # Generate feed items
        feed_items = []
        for impact in impacts:
            feed_data = {
                "sku": impact.sku,
                "revenue_at_risk": impact.revenue_at_risk,
                "days_of_cover": impact.days_of_cover,
                "action": impact.recommended_action,
                "severity": impact.impact_drivers.get("severity", "medium"),
                "impact_drivers": impact.impact_drivers,
                "risk_factors": impact.risk_factors,
            }

            feed_item = DecisionFeedGenerator.generate_feed_item(
                feed_data, impact.sku, payload.portfolio_id
            )

            # Store feed item
            decision_id = f"decision_{uuid.uuid4().hex[:12]}"
            db_feed = DecisionFeedItem(
                portfolio_id=payload.portfolio_id,
                decision_id=decision_id,
                title=feed_item["title"],
                description=feed_item["description"],
                action_required=feed_item["action_required"],
                sku=impact.sku,
                severity=feed_item["severity"],
                financial_impact=feed_item["financial_impact"],
                impact_type=feed_item["impact_type"],
                estimated_execution_time_min=feed_item["estimated_execution_time_min"],
                estimated_execution_time_max=feed_item["estimated_execution_time_max"],
                estimated_effort_points=feed_item["estimated_effort_points"],
                supporting_data=feed_item["supporting_data"],
                related_skus=feed_item["related_skus"],
            )
            db.add(db_feed)
            feed_items.append(feed_item)

        # Sort
        if payload.sort_by == "urgency":
            feed_items.sort(
                key=lambda x: -x.get("supporting_data", {}).get("urgency_score", 0)
            )
        elif payload.sort_by == "financial_impact":
            feed_items.sort(key=lambda x: -x.get("financial_impact", 0))

        db.commit()

        return {
            "portfolio_id": payload.portfolio_id,
            "count": len(feed_items),
            "feed": feed_items[: payload.limit],
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feed/{portfolio_id}")
def get_decision_feed(
    portfolio_id: str,
    severity: Optional[str] = None,
    acknowledged: bool = Query(False),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Retrieve decision feed for portfolio."""
    try:
        query = db.query(DecisionFeedItem).filter(
            DecisionFeedItem.portfolio_id == portfolio_id,
        )

        if severity:
            query = query.filter(DecisionFeedItem.severity == severity)

        if not acknowledged:
            query = query.filter(DecisionFeedItem.is_acknowledged == False)

        items = query.order_by(DecisionFeedItem.created_at.desc()).limit(limit).all()

        return {
            "portfolio_id": portfolio_id,
            "count": len(items),
            "feed": [
                {
                    "id": item.id,
                    "decision_id": item.decision_id,
                    "title": item.title,
                    "description": item.description,
                    "action": item.action_required,
                    "severity": item.severity,
                    "financial_impact": item.financial_impact,
                    "estimated_effort": item.estimated_effort_points,
                    "created_at": item.created_at.isoformat(),
                    "is_acknowledged": item.is_acknowledged,
                }
                for item in items
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feed/{feed_id}/acknowledge")
def acknowledge_feed_item(
    feed_id: int,
    user_id: str = Body(...),
    db: Session = Depends(get_db),
):
    """Mark feed item as acknowledged."""
    try:
        item = db.query(DecisionFeedItem).filter(DecisionFeedItem.id == feed_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Feed item not found")

        item.is_acknowledged = True
        item.acknowledged_by = user_id
        item.acknowledged_at = datetime.utcnow()
        db.commit()

        return {"success": True, "acknowledged_at": item.acknowledged_at.isoformat()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ── SKU Intelligence ───────────────────────────────────────────────────────────
@router.post("/sku-profile/build")
def build_sku_profile(
    portfolio_id: str = Body(...),
    sku: str = Body(...),
    sales_data: Dict[str, Any] = Body(...),
    forecast_data: Dict[str, Any] = Body(...),
    inventory_data: Dict[str, float] = Body(...),
    financial_data: Dict[str, float] = Body(...),
    db: Session = Depends(get_db),
):
    """Build comprehensive SKU intelligence profile."""
    try:
        # Convert sales data to DataFrame
        import pandas as pd

        df_sales = pd.DataFrame(sales_data)

        profile = SKUIntelligenceEngine.build_sku_profile(
            sku=sku,
            portfolio_id=portfolio_id,
            sales_data=df_sales,
            forecast_data=forecast_data,
            inventory_data=inventory_data,
            financial_data=financial_data,
        )

        # Store profile
        db_profile = SKUProfile(
            portfolio_id=portfolio_id,
            sku=sku,
            revenue_contributor=profile["revenue_contributor"],
            inventory_class=profile["inventory_class"],
            demand_pattern=profile["demand_pattern"],
            annual_revenue=profile["annual_revenue"],
            gross_margin_pct=profile["gross_margin_pct"],
            margin_contribution=profile["margin_contribution"],
            avg_daily_sales=profile["avg_daily_sales"],
            inventory_turnover=profile["inventory_turnover"],
            stockout_frequency_12m=profile["stockout_frequency_12m"],
            overstock_frequency_12m=profile["overstock_frequency_12m"],
            forecast_accuracy_mape=profile["forecast_accuracy_mape"],
            forecast_bias=profile["forecast_bias"],
            forecast_volatility=profile["forecast_volatility"],
            data_quality_level=profile["data_quality_level"],
            demand_volatility_index=profile["demand_volatility_index"],
            overall_health_score=profile["overall_health_score"],
            variance_analysis=profile["variance_analysis"],
        )
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)

        return {
            "success": True,
            "profile_id": db_profile.id,
            "profile": profile,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sku-profile/{portfolio_id}/{sku}")
def get_sku_profile(portfolio_id: str, sku: str, db: Session = Depends(get_db)):
    """Get SKU profile."""
    try:
        profile = (
            db.query(SKUProfile)
            .filter(
                SKUProfile.portfolio_id == portfolio_id,
                SKUProfile.sku == sku,
            )
            .order_by(SKUProfile.updated_at.desc())
            .first()
        )

        if not profile:
            raise HTTPException(status_code=404, detail="SKU profile not found")

        return {
            "sku": profile.sku,
            "revenue_contributor": profile.revenue_contributor,
            "inventory_class": profile.inventory_class,
            "demand_pattern": profile.demand_pattern,
            "annual_revenue": profile.annual_revenue,
            "margin_contribution": profile.margin_contribution,
            "forecast_accuracy": profile.forecast_accuracy_mape,
            "health_score": profile.overall_health_score,
            "variance_analysis": profile.variance_analysis,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Revenue at Risk Analysis ───────────────────────────────────────────────────
@router.post("/revenue-at-risk/compute")
def compute_revenue_at_risk(
    portfolio_id: str = Body(...),
    sku_impacts: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
):
    """Compute portfolio revenue at risk."""
    try:
        rar = RevenueAtRiskAnalyzer.compute_portfolio_rar(
            sku_impacts=sku_impacts,
            portfolio_id=portfolio_id,
        )

        # Store analysis
        db_rar = RevenueAtRisk(
            portfolio_id=portfolio_id,
            analysis_date=datetime.utcnow(),
            total_potential_revenue_at_risk=rar["total_revenue_at_risk"],
            total_stockout_cost_exposure=rar["total_stockout_cost"],
            total_overstock_cost_exposure=rar["total_overstock_cost"],
            skus_at_risk_count=rar["skus_at_risk"],
            critical_stockouts_projected=rar["critical_stockouts"],
            excess_inventory_skus=rar["excess_inventory_skus"],
            severity_classification=rar["severity"],
            recommended_actions_count=rar["recommended_actions_count"],
            sku_breakdown={
                item["sku"]: item["revenue_at_risk"] for item in rar["top_risks"]
            },
            risk_by_category=rar["risk_by_category"],
        )
        db.add(db_rar)
        db.commit()
        db.refresh(db_rar)

        return {
            "success": True,
            "analysis_id": db_rar.id,
            "rar": rar,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue-at-risk/{portfolio_id}")
def get_revenue_at_risk(
    portfolio_id: str,
    days: int = Query(1, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get latest revenue at risk analysis."""
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        analysis = (
            db.query(RevenueAtRisk)
            .filter(
                RevenueAtRisk.portfolio_id == portfolio_id,
                RevenueAtRisk.created_at >= cutoff,
            )
            .order_by(RevenueAtRisk.created_at.desc())
            .first()
        )

        if not analysis:
            raise HTTPException(status_code=404, detail="No RAR analysis found")

        return {
            "total_at_risk": analysis.total_potential_revenue_at_risk,
            "critical_count": analysis.critical_stockouts_projected,
            "excess_count": analysis.excess_inventory_skus,
            "severity": analysis.severity_classification,
            "top_risks": analysis.sku_breakdown,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Data Quality Monitoring ────────────────────────────────────────────────────
@router.post("/data-quality/assess")
def assess_data_quality(
    portfolio_id: str = Body(...),
    data: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
):
    """Assess data quality."""
    try:
        import pandas as pd

        df = pd.DataFrame(data)

        quality_report = DataQualityMonitor.assess_quality(df)

        return {
            "quality_score": quality_report["overall_quality_score"],
            "completeness": quality_report["completeness_pct"],
            "issues": quality_report["issues"],
            "field_scores": quality_report["field_scores"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Audit & Compliance ─────────────────────────────────────────────────────────
@router.post("/audit/log")
def log_audit_event(
    user_id: str = Body(...),
    event_type: str = Body(...),
    resource_type: str = Body(...),
    resource_id: str = Body(...),
    portfolio_id: str = Body(...),
    description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Log audit event for compliance tracking."""
    try:
        audit_log = DecisionAuditLog(
            user_id=user_id,
            event_type=event_type,
            event_date=datetime.utcnow(),
            resource_type=resource_type,
            resource_id=resource_id,
            portfolio_id=portfolio_id,
            description=description,
        )
        db.add(audit_log)
        db.commit()

        return {"success": True, "log_id": audit_log.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/logs/{portfolio_id}")
def get_audit_logs(
    portfolio_id: str,
    limit: int = Query(100, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Retrieve audit logs."""
    try:
        logs = (
            db.query(DecisionAuditLog)
            .filter(
                DecisionAuditLog.portfolio_id == portfolio_id,
            )
            .order_by(DecisionAuditLog.event_date.desc())
            .limit(limit)
            .all()
        )

        return {
            "count": len(logs),
            "logs": [
                {
                    "id": log.id,
                    "user": log.user_id,
                    "event": log.event_type,
                    "resource": log.resource_type,
                    "timestamp": log.event_date.isoformat(),
                }
                for log in logs
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Export & Reporting ─────────────────────────────────────────────────────────
@router.post("/export/create")
def create_export(
    payload: ExportRequest,
    user_id: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Create and track export."""
    try:
        export = ExportRecord(
            user_id=user_id,
            portfolio_id=payload.portfolio_id,
            export_type=payload.export_type,
            exported_resource=payload.exported_resource,
            title=payload.title,
            description=payload.title,
            filters_applied=payload.filters_applied,
            file_path=f"exports/{uuid.uuid4()}.{payload.export_type}",
            retention_days=90,
        )
        db.add(export)
        db.commit()
        db.refresh(export)

        # Log audit event
        audit = DecisionAuditLog(
            user_id=user_id,
            event_type="export",
            event_date=datetime.utcnow(),
            resource_type="export",
            resource_id=str(export.id),
            portfolio_id=payload.portfolio_id,
            is_export=True,
            export_format=payload.export_type,
        )
        db.add(audit)
        db.commit()

        return {
            "success": True,
            "export_id": export.id,
            "file_path": export.file_path,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/history/{portfolio_id}")
def get_export_history(
    portfolio_id: str,
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Get export history."""
    try:
        exports = (
            db.query(ExportRecord)
            .filter(
                ExportRecord.portfolio_id == portfolio_id,
            )
            .order_by(ExportRecord.created_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "count": len(exports),
            "exports": [
                {
                    "id": exp.id,
                    "title": exp.title,
                    "type": exp.export_type,
                    "created_at": exp.created_at.isoformat(),
                    "file_path": exp.file_path,
                }
                for exp in exports
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
