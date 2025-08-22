# Create this as waste_classifier/pdf_report.py

import os
from io import BytesIO
from django.http import HttpResponse, FileResponse
from django.template.loader import get_template
from django.conf import settings
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF
from PIL import Image as PILImage
import datetime
import logging

logger = logging.getLogger(__name__)

class WasteClassificationPDFGenerator:
    """Generate PDF reports for waste classification results"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

    def setup_custom_styles(self):
        """Create custom paragraph styles for the PDF"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#34495e'),
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=colors.HexColor('#bdc3c7'),
            borderPadding=8,
            backColor=colors.HexColor('#ecf0f1')
        ))

        # Content style
        self.styles.add(ParagraphStyle(
            name='ContentText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_JUSTIFY,
            leftIndent=10,
            rightIndent=10
        ))

        # Highlight style
        self.styles.add(ParagraphStyle(
            name='HighlightText',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            textColor=colors.HexColor('#e74c3c'),
            fontName='Helvetica-Bold',
            leftIndent=10
        ))

        # Info box style
        self.styles.add(ParagraphStyle(
            name='InfoBox',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=12,
            textColor=colors.HexColor('#2980b9'),
            borderWidth=1,
            borderColor=colors.HexColor('#3498db'),
            borderPadding=10,
            backColor=colors.HexColor('#ebf3fd'),
            leftIndent=5,
            rightIndent=5
        ))

    def generate_pdf_report(self, classification, output_path=None):
        """
        Generate a comprehensive PDF report for waste classification

        Args:
            classification: WasteClassification model instance
            output_path: Optional file path to save PDF (if None, returns BytesIO)

        Returns:
            BytesIO buffer or saves to file
        """
        if output_path:
            buffer = open(output_path, 'wb')
        else:
            buffer = BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Build the PDF content
        story = []

        # Add header
        self._add_header(story, classification)

        # Add waste image if available
        if classification.image:
            self._add_waste_image(story, classification)

        # Add classification summary
        self._add_classification_summary(story, classification)

        # Add detailed sections
        self._add_disposal_section(story, classification)
        self._add_risk_assessment_section(story, classification)
        self._add_safety_measures_section(story, classification)
        self._add_additional_info_section(story, classification)

        # Add footer
        self._add_footer(story, classification)

        # Build PDF
        doc.build(story)

        if output_path:
            buffer.close()
            return output_path
        else:
            buffer.seek(0)
            return buffer

    def _add_header(self, story, classification):
        """Add report header with title and basic info"""
        # Main title
        title = Paragraph("🗑️ Waste Analysis Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 20))

        # Report info table
        report_data = [
            ['Report Generated:', datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')],
            ['Analysis Date:', classification.created_at.strftime('%B %d, %Y at %I:%M %p')],
            ['State/Region:', classification.get_state_display()],
            ['Report ID:', f"WR-{classification.id:06d}"]
        ]

        report_table = Table(report_data, colWidths=[2*inch, 3*inch])
        report_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#ecf0f1')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(report_table)
        story.append(Spacer(1, 30))

    def _add_waste_image(self, story, classification):
        """Add the analyzed waste image to the report"""
        try:
            if classification.image and os.path.exists(classification.image.path):
                # Open and resize image
                pil_img = PILImage.open(classification.image.path)

                # Calculate dimensions to fit within 4 inches width
                max_width = 4 * inch
                max_height = 3 * inch

                img_width, img_height = pil_img.size
                aspect_ratio = img_height / img_width

                if img_width > max_width / 72:  # Convert to points
                    new_width = max_width
                    new_height = new_width * aspect_ratio
                    if new_height > max_height:
                        new_height = max_height
                        new_width = new_height / aspect_ratio
                else:
                    new_width = img_width * 72 / 72  # Convert to points
                    new_height = img_height * 72 / 72

                # Add image to story
                img = Image(classification.image.path, width=new_width, height=new_height)

                # Center the image
                story.append(Paragraph("📸 Analyzed Waste Image", self.styles['SectionHeader']))
                story.append(Spacer(1, 10))

                # Create a table to center the image
                img_table = Table([[img]], colWidths=[6*inch])
                img_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))

                story.append(img_table)
                story.append(Spacer(1, 20))

        except Exception as e:
            # If image processing fails, add a note
            logger.warning(f"Could not add image to PDF: {e}")
            story.append(Paragraph("📸 Image Analysis", self.styles['SectionHeader']))
            story.append(Paragraph(
                "Note: Could not include waste image in report.",
                self.styles['InfoBox']
            ))
            story.append(Spacer(1, 20))

    def _add_classification_summary(self, story, classification):
        """Add classification results summary"""
        story.append(Paragraph("🔍 Classification Summary", self.styles['SectionHeader']))

        # Classification details table
        confidence_percent = round(classification.confidence_score * 100, 2) if classification.confidence_score else 0

        summary_data = [
            ['Waste Category:', classification.get_predicted_category_display()],
            ['Confidence Level:', f"{confidence_percent}%"],
            ['Description:', classification.waste_description or 'No description available']
        ]

        summary_table = Table(summary_data, colWidths=[1.5*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#2ecc71')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#d5f4e6')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#27ae60')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 25))

    def _add_disposal_section(self, story, classification):
        """Add disposal instructions section"""
        story.append(Paragraph("🗑️ Disposal Instructions", self.styles['SectionHeader']))

        if classification.disposal_instructions:
            story.append(Paragraph("General Disposal Method:", self.styles['HighlightText']))
            story.append(Paragraph(classification.disposal_instructions, self.styles['ContentText']))

        if classification.state_specific_laws:
            story.append(Paragraph("⚖️ State-Specific Regulations:", self.styles['HighlightText']))
            story.append(Paragraph(classification.state_specific_laws, self.styles['ContentText']))

        if classification.authorized_facilities:
            story.append(Paragraph("🏢 Authorized Facilities:", self.styles['HighlightText']))
            story.append(Paragraph(classification.authorized_facilities, self.styles['ContentText']))

        story.append(Spacer(1, 20))

    def _add_risk_assessment_section(self, story, classification):
        """Add risk assessment section"""
        story.append(Paragraph("⚠️ Risk Assessment", self.styles['SectionHeader']))

        if classification.health_hazards:
            story.append(Paragraph("🏥 Health Hazards:", self.styles['HighlightText']))
            story.append(Paragraph(classification.health_hazards, self.styles['ContentText']))

        if classification.environmental_risks:
            story.append(Paragraph("🌍 Environmental Risks:", self.styles['HighlightText']))
            story.append(Paragraph(classification.environmental_risks, self.styles['ContentText']))

        story.append(Spacer(1, 20))

    def _add_safety_measures_section(self, story, classification):
        """Add safety measures section"""
        story.append(Paragraph("🛡️ Safety Measures", self.styles['SectionHeader']))

        if classification.precautions:
            story.append(Paragraph("⚠️ Precautions:", self.styles['HighlightText']))
            story.append(Paragraph(classification.precautions, self.styles['ContentText']))

        if classification.protective_equipment:
            story.append(Paragraph("🥽 Protective Equipment:", self.styles['HighlightText']))
            story.append(Paragraph(classification.protective_equipment, self.styles['ContentText']))

        if classification.emergency_procedures:
            story.append(Paragraph("🚨 Emergency Procedures:", self.styles['HighlightText']))
            story.append(Paragraph(classification.emergency_procedures, self.styles['ContentText']))

        story.append(Spacer(1, 20))

    def _add_additional_info_section(self, story, classification):
        """Add additional information section"""
        story.append(Paragraph("📋 Additional Information", self.styles['SectionHeader']))

        if classification.recyclability_info:
            story.append(Paragraph("♻️ Recyclability Information:", self.styles['HighlightText']))
            story.append(Paragraph(classification.recyclability_info, self.styles['ContentText']))

        if classification.cost_implications:
            story.append(Paragraph("💰 Cost Implications:", self.styles['HighlightText']))
            story.append(Paragraph(classification.cost_implications, self.styles['ContentText']))

        story.append(Spacer(1, 20))

    def _add_footer(self, story, classification):
        """Add report footer with disclaimer and contact info"""
        story.append(Spacer(1, 30))

        # Disclaimer
        disclaimer_text = """
        <b>Disclaimer:</b> This analysis is generated using AI technology and is provided for informational purposes only.
        Always consult with local waste management authorities and follow official disposal guidelines for your region.
        The accuracy of this analysis depends on the quality of the provided image and may not be 100% accurate in all cases.
        """

        story.append(Paragraph("⚖️ Important Disclaimer", self.styles['SectionHeader']))
        story.append(Paragraph(disclaimer_text, self.styles['InfoBox']))

        # Contact information
        contact_text = """
        For more information about waste disposal in your area, contact your local municipal corporation or
        visit the official website of the Pollution Control Board in your state.
        """

        story.append(Paragraph("📞 Contact Information", self.styles['SectionHeader']))
        story.append(Paragraph(contact_text, self.styles['ContentText']))

        # Report end
        story.append(Spacer(1, 20))
        story.append(Paragraph(
            f"--- End of Report (Generated by EcoWaste AI) ---",
            self.styles['InfoBox']
        ))


def generate_waste_classification_pdf(classification):
    """
    Utility function to generate PDF report for a waste classification

    Args:
        classification: WasteClassification model instance

    Returns:
        BytesIO buffer containing the PDF
    """
    generator = WasteClassificationPDFGenerator()
    return generator.generate_pdf_report(classification)
