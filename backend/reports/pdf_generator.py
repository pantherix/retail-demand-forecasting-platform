from __future__ import annotations

from pathlib import Path
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


class PDFReportGenerator:

    def __init__(self):

        self.styles = getSampleStyleSheet()

    def build_header(self, elements, title):

        elements.append(Paragraph(title, self.styles["Title"]))

        elements.append(Spacer(1, 20))

        elements.append(
            Paragraph(f"Generated: " f"{datetime.utcnow()}", self.styles["Normal"])
        )

        elements.append(Spacer(1, 20))

    def build_summary(self, elements, summary):

        elements.append(Paragraph("Executive Summary", self.styles["Heading1"]))

        elements.append(Paragraph(summary, self.styles["BodyText"]))

        elements.append(Spacer(1, 20))

    def build_kpi_table(self, elements, kpis):

        data = [["Metric", "Value"]]

        for key, value in kpis.items():

            data.append([str(key), str(value)])

        table = Table(data, colWidths=[220, 220])

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        elements.append(table)

        elements.append(Spacer(1, 20))

    def build_inventory_section(self, elements, inventory):

        elements.append(Paragraph("Inventory Analysis", self.styles["Heading1"]))

        rows = [["Metric", "Value"]]

        for k, v in inventory.items():

            rows.append([k, str(v)])

        table = Table(rows)

        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 1, colors.black)]))

        elements.append(table)

        elements.append(Spacer(1, 20))

    def build_risk_section(self, elements, risks):

        elements.append(Paragraph("Risk Assessment", self.styles["Heading1"]))

        for risk in risks:

            elements.append(Paragraph(f"• {risk}", self.styles["BodyText"]))

        elements.append(Spacer(1, 20))

    def generate(self, output_file, executive_summary, kpis, inventory, risks):

        doc = SimpleDocTemplate(output_file)

        elements = []

        self.build_header(elements, "RetailGPT Enterprise Report")

        self.build_summary(elements, executive_summary)

        self.build_kpi_table(elements, kpis)

        self.build_inventory_section(elements, inventory)

        self.build_risk_section(elements, risks)

        doc.build(elements)

        return {"success": True, "file": output_file}


pdf_generator = PDFReportGenerator()
