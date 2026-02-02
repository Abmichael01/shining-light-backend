"""
Simple HTML Receipt Generator
Generates HTML receipts that can be printed or saved as PDF by the browser
"""

from datetime import datetime


def generate_receipt_html(payment):
    """
    Generate HTML receipt for fee payment
    
    Args:
        payment: FeePayment instance
        
    Returns:
        str: HTML content for the receipt
    """
    student = payment.student
    
    # Get student name with fallback
    try:
        student_name = student.get_full_name()
    except:
        student_name = getattr(student, 'full_name', 'N/A')
    
    # Get school name
    school_name = student.school.name if hasattr(student, 'school') and student.school else "Shining Light Schools"
    
    # Get class name
    class_name = student.class_model.name if student.class_model else "N/A"
    
    # Get session and term
    session_name = payment.session.name if payment.session else "N/A"
    term_name = payment.session_term.term_name if payment.session_term else "N/A"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Payment Receipt - {payment.receipt_number}</title>
        <style>
            @media print {{
                body {{ margin: 0; }}
                .no-print {{ display: none; }}
            }}
            
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 20px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            
            .receipt {{
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            
            .header {{
                text-align: center;
                border-bottom: 3px solid #1e40af;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            
            .school-name {{
                font-size: 24px;
                font-weight: bold;
                color: #1e40af;
                margin-bottom: 10px;
            }}
            
            .receipt-title {{
                font-size: 20px;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }}
            
            .receipt-number {{
                font-size: 14px;
                color: #666;
            }}
            
            .section {{
                margin-bottom: 25px;
            }}
            
            .section-title {{
                font-size: 16px;
                font-weight: bold;
                color: #1e40af;
                margin-bottom: 15px;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 5px;
            }}
            
            .info-row {{
                display: flex;
                padding: 8px 0;
                border-bottom: 1px solid #f3f4f6;
            }}
            
            .info-label {{
                font-weight: bold;
                width: 200px;
                color: #374151;
            }}
            
            .info-value {{
                flex: 1;
                color: #6b7280;
            }}
            
            .amount-box {{
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin: 30px 0;
            }}
            
            .amount-label {{
                font-size: 14px;
                opacity: 0.9;
                margin-bottom: 5px;
            }}
            
            .amount-value {{
                font-size: 32px;
                font-weight: bold;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 2px solid #e5e7eb;
                color: #9ca3af;
                font-size: 12px;
            }}
            
            .print-button {{
                background: #1e40af;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                margin: 20px auto;
                display: block;
            }}
            
            .print-button:hover {{
                background: #1e3a8a;
            }}
        </style>
    </head>
    <body>
        <div class="receipt">
            <div class="header">
                <div class="school-name">{school_name.upper()}</div>
                <div class="receipt-title">PAYMENT RECEIPT</div>
                <div class="receipt-number">Receipt No: {payment.receipt_number}</div>
            </div>
            
            <div class="section">
                <div class="section-title">STUDENT INFORMATION</div>
                <div class="info-row">
                    <div class="info-label">Name:</div>
                    <div class="info-value">{student_name}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Admission Number:</div>
                    <div class="info-value">{student.admission_number or 'N/A'}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Class:</div>
                    <div class="info-value">{class_name}</div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">PAYMENT DETAILS</div>
                <div class="info-row">
                    <div class="info-label">Date:</div>
                    <div class="info-value">{payment.payment_date.strftime('%B %d, %Y')}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Fee Type:</div>
                    <div class="info-value">{payment.fee_type.name}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Payment Method:</div>
                    <div class="info-value">{payment.get_payment_method_display()}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Reference Number:</div>
                    <div class="info-value">{payment.reference_number or 'N/A'}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">School Session:</div>
                    <div class="info-value">{session_name}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Term:</div>
                    <div class="info-value">{term_name}</div>
                </div>
            </div>
            
            <div class="amount-box">
                <div class="amount-label">AMOUNT PAID</div>
                <div class="amount-value">₦{payment.amount:,.2f}</div>
            </div>
            
            <div class="footer">
                <p>This receipt is computer-generated and is valid without a signature.</p>
                <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
        </div>
        
        <button class="print-button no-print" onclick="window.print()">Print Receipt</button>
        
        <script>
            // Auto-print on load (optional)
            // window.onload = function() {{ window.print(); }};
        </script>
    </body>
    </html>
    """
    
    return html
