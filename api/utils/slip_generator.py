"""
Application Slip PDF Generator
Generates professional PDF slips for applicants
"""

from io import BytesIO
from reportlab.lib.pagesizes import A4 
from reportlab.lib.units import cm, inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors  
from reportlab.platypus import Table, TableStyle
import qrcode 
from django.conf import settings
from django.core.files.base import ContentFile
import os
from datetime import datetime
 

class SlipPDFGenerator:
    """Generate application slip PDFs"""
    
    def __init__(self, student, slip):
        self.student = student
        self.slip = slip
        self.width, self.height = A4
        self.buffer = BytesIO()
        
    def generate(self):
        """Generate the PDF and return the file"""
        c = canvas.Canvas(self.buffer, pagesize=A4)
        
        # Draw header
        self._draw_header(c)
        
        # Draw applicant details
        self._draw_applicant_details(c)
        
        # Draw QR code
        self._draw_qr_code(c)
        
        # Draw footer
        self._draw_footer(c)
        
        c.showPage()
        c.save()
        
        # Get PDF content
        self.buffer.seek(0)
        return self.buffer
    
    def _draw_header(self, c):
        """Draw header with school info"""
        # School name
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(self.width / 2, self.height - 2*cm, 
                           self.student.school.name.upper())
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(colors.HexColor("#1e40af"))
        c.drawCentredString(self.width / 2, self.height - 3*cm, 
                           "APPLICATION SLIP")
        c.setFillColor(colors.black)
        
        # Academic session
        c.setFont("Helvetica", 12)
        current_year = datetime.now().year
        c.drawCentredString(self.width / 2, self.height - 3.8*cm, 
                           f"Academic Session: {current_year}/{current_year + 1}")
        
        # Draw line
        c.setStrokeColor(colors.HexColor("#1e40af"))
        c.setLineWidth(2)
        c.line(2*cm, self.height - 4.5*cm, self.width - 2*cm, self.height - 4.5*cm)
        
    def _draw_applicant_details(self, c):
        """Draw applicant information"""
        y_position = self.height - 6*cm
        left_margin = 3*cm
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left_margin, y_position, "APPLICANT INFORMATION")
        
        y_position -= 1.2*cm
        
        # Get biodata
        biodata = getattr(self.student, 'biodata', None)
        full_name = ""
        if biodata:
            full_name = f"{biodata.surname} {biodata.first_name} {biodata.other_names or ''}".strip().upper()
        
        # Details table data
        details = [
            ["Application Number:", self.slip.application_number],
            ["Full Name:", full_name or "N/A"],
            ["Class Applied For:", self.student.class_model.name if self.student.class_model else "N/A"],
            ["Email:", self.student.user.email],
            ["Submission Date:", self.slip.generated_at.strftime("%B %d, %Y")],
        ]
        
        # Draw details
        c.setFont("Helvetica", 11)
        for label, value in details:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(left_margin, y_position, label)
            c.setFont("Helvetica", 11)
            c.drawString(left_margin + 5*cm, y_position, str(value))
            y_position -= 0.7*cm
        
        # SCREENING DATE - Highlighted
        y_position -= 1*cm
        c.setStrokeColor(colors.HexColor("#dc2626"))
        c.setFillColor(colors.HexColor("#fee2e2"))
        c.rect(left_margin - 0.5*cm, y_position - 2.5*cm, 
               self.width - 6*cm, 3*cm, fill=1, stroke=1)
        
        c.setFillColor(colors.HexColor("#dc2626"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left_margin, y_position - 0.5*cm, "📅 SCREENING/INTERVIEW DATE")
        
        y_position -= 1.3*cm
        
        # screening date in large font
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(left_margin, y_position, "Report on:")
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(colors.HexColor("#dc2626"))
        screening_date = self.slip.screening_date.strftime("%B %d, %Y") if self.slip.screening_date else "TO BE ANNOUNCED"
        c.drawString(left_margin + 3.5*cm, y_position, screening_date)
        
        y_position -= 0.8*cm
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(left_margin, y_position, 
                    "Time: 9:00 AM • Report 30 minutes early")
        
        # Important notice box
        y_position -= 2*cm
        c.setStrokeColor(colors.HexColor("#10b981"))
        c.setFillColor(colors.HexColor("#d1fae5"))
        c.rect(left_margin - 0.5*cm, y_position - 2.5*cm, 
               self.width - 6*cm, 3*cm, fill=1, stroke=1)
        
        c.setFillColor(colors.HexColor("#065f46"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(left_margin, y_position - 0.5*cm, "✓ APPLICATION SUBMITTED SUCCESSFULLY")
        
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(left_margin, y_position - 1.2*cm, 
                    "Bring this slip on the screening day. Admission will NOT be granted without")
        c.drawString(left_margin, y_position - 1.7*cm, 
                    "this slip. You will be notified via email about your admission status.")
        c.drawString(left_margin, y_position - 2.2*cm, 
                    "For inquiries, contact us via email.")
        
    def _draw_qr_code(self, c):
        """Draw QR code"""
        from reportlab.lib.utils import ImageReader
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr_data = f"APP:{self.slip.application_number}|SEAT:{self.slip.seat_number}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert PIL Image to ReportLab ImageReader
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Use ImageReader to wrap the BytesIO
        img_reader = ImageReader(qr_buffer)
        
        # Draw QR code on PDF
        qr_size = 3*cm
        c.drawImage(img_reader, self.width - 5.5*cm, self.height - 12*cm, 
                   width=qr_size, height=qr_size)
        
        # QR code label
        c.setFont("Helvetica", 8)
        c.drawCentredString(self.width - 4*cm, self.height - 12.5*cm, 
                           "Scan for verification")
        
    def _draw_footer(self, c):
        """Draw footer"""
        y_position = 3*cm
        
        c.setStrokeColor(colors.grey)
        c.setLineWidth(1)
        c.line(2*cm, y_position, self.width - 2*cm, y_position)
        
        y_position -= 0.8*cm
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.grey)
        c.drawCentredString(self.width / 2, y_position, 
                           "This is a computer-generated document and does not require a signature.")
        
        y_position -= 0.5*cm
        c.drawCentredString(self.width / 2, y_position, 
                           f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        
        # Contact info
        y_position -= 0.8*cm
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(self.width / 2, y_position, 
                           "For inquiries, contact:")
        y_position -= 0.5*cm
        c.setFont("Helvetica", 9)
        c.drawCentredString(self.width / 2, y_position, 
                           getattr(settings, 'CONTACT_EMAIL', 'info@school.com'))


def generate_slip_pdf(student, slip):
    """
    Generate application slip PDF
    
    Args:
        student: Student instance
        slip: ApplicationSlip instance
        
    Returns:
        ContentFile: PDF file content
    """
    generator = SlipPDFGenerator(student, slip)
    pdf_buffer = generator.generate()
    
    filename = f"slip_{slip.application_number}_{slip.seat_number}.pdf"
    return ContentFile(pdf_buffer.read(), name=filename)
