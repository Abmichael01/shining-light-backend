"""
Staff Wallet Receipt Generator
Generates HTML receipts for wallet transactions
"""

from datetime import datetime

def generate_wallet_receipt_html(transaction):
    """
    Generate HTML receipt for staff wallet transaction
    
    Args:
        transaction: StaffWalletTransaction instance
        
    Returns:use 
        str: HTML content for the receipt
    """
    staff = transaction.wallet.staff
    
    # Get staff name
    try:
        staff_name = staff.get_full_name()
    except:
        staff_name = "N/A"
    
    # Get school name
    school_name = staff.school.name if staff.school else "Shining Light Schools"
    
    # Format date
    transaction_date_str = transaction.created_at.strftime('%B %d, %Y')
    
    # Format amount
    amount_str = f"₦{transaction.amount:,.2f}"
    
    # Get current datetime
    generated_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    
    # Transaction Type Display
    tx_type_display = transaction.get_transaction_type_display().upper()
    category_display = transaction.get_category_display()
    
    # Color logic
    amount_color_class = "credit-box" if transaction.transaction_type == 'credit' else "debit-box"
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Transaction Receipt - {reference}</title>
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
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin: 30px 0;
            }}
            
            .credit-box {{
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            }}
            
            .debit-box {{
                background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
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
                <div class="school-name">{school_name_upper}</div>
                <div class="receipt-title">WALLET TRANSACTION RECEIPT</div>
                <div class="receipt-number">Ref: {reference}</div>
            </div>
            
            <div class="section">
                <div class="section-title">STAFF INFORMATION</div>
                <div class="info-row">
                    <div class="info-label">Name:</div>
                    <div class="info-value">{staff_name}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Staff ID:</div>
                    <div class="info-value">{staff_id}</div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">TRANSACTION DETAILS</div>
                <div class="info-row">
                    <div class="info-label">Date:</div>
                    <div class="info-value">{transaction_date}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Type:</div>
                    <div class="info-value">{tx_type}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Category:</div>
                    <div class="info-value">{category}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Status:</div>
                    <div class="info-value">{status}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Description:</div>
                    <div class="info-value">{description}</div>
                </div>
            </div>
            
            <div class="amount-box {amount_color_class}">
                <div class="amount-label">AMOUNT</div>
                <div class="amount-value">{amount}</div>
            </div>
            
            <div class="footer">
                <p>This receipt is computer-generated and is valid without a signature.</p>
                <p>Generated on {generated_time}</p>
            </div>
        </div>
        
        <script>
            // Auto-print on load (optional)
            // window.onload = function() {{ window.print(); }};
        </script>
    </body>
    </html>
    """.format(
        reference=transaction.reference,
        school_name_upper=school_name.upper(),
        staff_name=staff_name,
        staff_id=staff.staff_id,
        transaction_date=transaction_date_str,
        tx_type=tx_type_display,
        category=category_display,
        status=transaction.get_status_display().upper(),
        description=transaction.description,
        amount=amount_str,
        generated_time=generated_time,
        amount_color_class=amount_color_class
    )
    
    return html
