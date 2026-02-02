"""
Fee Receipt PDF Generator
Generates professional PDF receipts for student fee payments
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
 

class ReceiptPDFGenerator:
    """Generate fee payment receipt PDFs"""
    
    def __init__(self, payment):
        self.payment = payment
        self.student = payment.student
        self.width, self.height = A4
        self.buffer = BytesIO()
        
    def generate(self):
        """Generate the PDF and return the buffer"""
        c = canvas.Canvas(self.buffer, pagesize=A4)
        
        # Draw header
        self._draw_header(c)
        
        # Draw receipt details
        self._draw_details(c)
        
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
        school_name = self.student.school.name.upper() if getattr(self.student, 'school', None) else "SHINING LIGHT SCHOOL"
        c.drawCentredString(self.width / 2, self.height - 2*cm, school_name)
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(colors.HexColor("#1e40af"))
        c.drawCentredString(self.width / 2, self.height - 3*cm, 
                           "PAYMENT RECEIPT")
        c.setFillColor(colors.black)
        
        # Receipt Number
        c.setFont("Helvetica", 12)
        c.drawCentredString(self.width / 2, self.height - 3.8*cm, 
                           f"Receipt No: {self.payment.receipt_number}")
        
        # Draw line
        c.setStrokeColor(colors.HexColor("#1e40af"))
        c.setLineWidth(2)
        c.line(2*cm, self.height - 4.5*cm, self.width - 2*cm, self.height - 4.5*cm)
        
    def _draw_details(self, c):
        """Draw payment information"""
        y_position = self.height - 6*cm
        left_margin = 3*cm
        
        # Student Info Section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left_margin, y_position, "STUDENT INFORMATION")
        y_position -= 1.0*cm
        
        # Get student name with fallback
        try:
            full_name = self.student.get_full_name().upper()
        except:
            # Fallback to full_name field or construct from biodata
            biodata = getattr(self.student, 'biodata', None)
            if hasattr(self.student, 'full_name') and self.student.full_name:
                full_name = self.student.full_name.upper()
            elif biodata:
                full_name = f"{biodata.surname} {biodata.first_name}".upper()
            else:
                full_name = "N/A"
        
        details = [
            ["Name:", full_name],
            ["Admission No:", self.student.admission_number or "N/A"],
            ["Class:", self.student.class_model.name if self.student.class_model else "N/A"],
        ]
        
        c.setFont("Helvetica", 11)
        for label, value in details:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(left_margin, y_position, label)
            c.setFont("Helvetica", 11)
            c.drawString(left_margin + 4*cm, y_position, str(value))
            y_position -= 0.7*cm
            
        y_position -= 1.0*cm
        
        # Payment Info Section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left_margin, y_position, "PAYMENT DETAILS")
        y_position -= 1.0*cm
        
        payment_details = [
            ["Date:", self.payment.payment_date.strftime("%B %d, %Y")],
            ["Fee Type:", self.payment.fee_type.name],
            ["Method:", self.payment.get_payment_method_display()],
            ["Reference:", self.payment.reference_number or "N/A"],
            ["School Session:", self.payment.session.name if self.payment.session else "N/A"],
            ["Term:", self.payment.session_term.term_name if self.payment.session_term else "N/A"],
        ]
        
        for label, value in payment_details:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(left_margin, y_position, label)
            c.setFont("Helvetica", 11)
            c.drawString(left_margin + 4*cm, y_position, str(value))
            y_position -= 0.7*cm
            
        # Amount Box
        y_position -= 1.5*cm
        c.setStrokeColor(colors.HexColor("#10b981"))
        c.setFillColor(colors.HexColor("#d1fae5"))
        c.rect(left_margin - 0.5*cm, y_position - 1.5*cm, 
               self.width - 6*cm, 2*cm, fill=1, stroke=1)
        
        c.setFillColor(colors.HexColor("#065f46"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(left_margin, y_position, "AMOUNT PAID")
        
        c.setFont("Helvetica-Bold", 20)
        c.drawString(left_margin, y_position - 1.0*cm, f"₦{self.payment.amount:,.2f}")
        
    def _draw_qr_code(self, c):
        """Draw verification QR code"""
        from reportlab.lib.utils import ImageReader
        
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        # Format: REC:RCP-202X-XXXXXX|AMT:XXXXX
        qr_data = f"REC:{self.payment.receipt_number}|AMT:{self.payment.amount}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        img_reader = ImageReader(qr_buffer)
        
        qr_size = 3*cm
        c.drawImage(img_reader, self.width - 5.5*cm, self.height - 9*cm, 
                   width=qr_size, height=qr_size)
                   
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
                           "This receipt is computer-generated and is valid without a signature.")
        
        y_position -= 0.5*cm
        c.drawCentredString(self.width / 2, y_position, 
                           f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")


def generate_receipt_pdf(payment):
    """
    Generate fee receipt PDF
    
    Args:
        payment: FeePayment instance
        
    Returns:
        ContentFile: PDF file content
    """
    generator = ReceiptPDFGenerator(payment)
    pdf_buffer = generator.generate()
    
    filename = f"receipt_{payment.receipt_number}.pdf"
    return ContentFile(pdf_buffer.read(), name=filename)
