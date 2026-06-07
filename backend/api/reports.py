from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import FileResponse

from reports.pdf_generator import pdf_generator

router = APIRouter(prefix="/reports", tags=["Reports"])

REPORT_DIR = "./generated_reports"

Path(REPORT_DIR).mkdir(parents=True, exist_ok=True)


@router.get("/health")
def health():

    return {"module": "reports", "status": "healthy"}


@router.post("/executive")
def executive_report():

    try:

        report_file = f"{REPORT_DIR}/" f"executive_report.pdf"

        summary = """

        Revenue growing steadily.

        Inventory health stable.

        2 critical SKUs require
        immediate attention.

        """

        kpis = {
            "Revenue": "₹1.25 Cr",
            "Inventory": "₹92 Lakh",
            "Forecast Accuracy": "92.4%",
            "Critical SKUs": 7,
        }

        inventory = {
            "Inventory Value": "₹92 Lakh",
            "Inventory Health": "84%",
            "Turnover": "8.3",
        }

        risks = [
            "SKU-205 stockout risk",
            "SKU-101 reorder required",
            "SKU-440 demand spike",
        ]

        pdf_generator.generate(
            output_file=report_file,
            executive_summary=summary,
            kpis=kpis,
            inventory=inventory,
            risks=risks,
        )

        return {"success": True, "file": report_file}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download")
def download_report():

    file_path = f"{REPORT_DIR}/" f"executive_report.pdf"

    if not Path(file_path).exists():

        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        file_path, media_type="application/pdf", filename="RetailGPT_Report.pdf"
    )


@router.post("/risk-report")
def risk_report():

    try:

        report_file = f"{REPORT_DIR}/" f"risk_report.pdf"

        summary = """

        Risk Assessment Report

        Critical products detected.

        Immediate replenishment
        recommended.

        """

        kpis = {"Critical": 3, "High": 5, "Medium": 10, "Low": 20}

        inventory = {"Affected SKUs": 8, "Revenue Exposure": "₹14 Lakh"}

        risks = ["Critical stockout", "Revenue loss risk", "Supplier delay risk"]

        pdf_generator.generate(
            output_file=report_file,
            executive_summary=summary,
            kpis=kpis,
            inventory=inventory,
            risks=risks,
        )

        return {"success": True, "file": report_file}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecast-report")
def forecast_report():

    try:

        report_file = f"{REPORT_DIR}/" f"forecast_report.pdf"

        summary = """

        Forecast Outlook

        Strong demand growth
        expected next month.

        """

        kpis = {"Forecast": 85400, "Accuracy": "92.4%", "Growth": "+14%"}

        inventory = {"Required Stock": 92000, "Current Stock": 71000}

        risks = ["Demand surge", "Inventory shortage"]

        pdf_generator.generate(
            output_file=report_file,
            executive_summary=summary,
            kpis=kpis,
            inventory=inventory,
            risks=risks,
        )

        return {"success": True, "file": report_file}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))
