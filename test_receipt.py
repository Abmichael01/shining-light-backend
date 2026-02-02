#!/usr/bin/env python3
"""
Test receipt generation
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import FeePayment
from api.utils.simple_receipt_generator import generate_receipt_html

# Get first payment
try:
    payment = FeePayment.objects.first()
    if payment:
        print(f"Testing receipt for payment ID: {payment.id}")
        print(f"Receipt number: {payment.receipt_number}")
        
        html = generate_receipt_html(payment)
        print("\n✓ Receipt generated successfully!")
        print(f"HTML length: {len(html)} characters")
        
        # Save to file for inspection
        with open('/tmp/test_receipt.html', 'w') as f:
            f.write(html)
        print("✓ Saved to /tmp/test_receipt.html")
    else:
        print("No payments found in database")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
