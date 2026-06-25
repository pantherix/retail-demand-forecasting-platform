from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate


class ExecutiveReport:

    def generate(self, path, content):

        doc = SimpleDocTemplate(path)

        styles = getSampleStyleSheet()

        elements = [
            Paragraph("RetailGPT Report", styles["Title"]),
            Paragraph(content, styles["BodyText"]),
        ]

        doc.build(elements)
