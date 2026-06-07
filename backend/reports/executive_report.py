from reportlab.platypus import SimpleDocTemplate, Paragraph

from reportlab.lib.styles import getSampleStyleSheet


class ExecutiveReport:

    def generate(self, path, content):

        doc = SimpleDocTemplate(path)

        styles = getSampleStyleSheet()

        elements = [
            Paragraph("RetailGPT Report", styles["Title"]),
            Paragraph(content, styles["BodyText"]),
        ]

        doc.build(elements)
