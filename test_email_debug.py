
import os
from django.core.mail import send_mail
from django.conf import settings
from api.utils.email import send_bulk_email
from api.models import Staff

def test_single_email():
    print("Testing single email sending...")
    try:
        send_mail(
            'Test Single Email',
            'This is a test email from the backend terminal.',
            settings.DEFAULT_FROM_EMAIL,
            ['abmichael01@gmail.com'], # Replace with a safe test email if needed, or user's email
            fail_silently=False,
        )
        print("✅ Single email sent successfully.")
    except Exception as e:
        print(f"❌ Single email failed: {e}")

def test_bulk_function():
    print("\nTesting bulk email utility...")
    try:
        recipients = ['abmichael01@gmail.com'] # Test with one recipient
        success, msg = send_bulk_email(recipients, 'Test Bulk Email', '<p>This is a bulk email test.</p>')
        if success:
            print(f"✅ Bulk email sent successfully: {msg}")
        else:
            print(f"❌ Bulk email failed: {msg}")
    except Exception as e:
        print(f"❌ Bulk function error: {e}")

def test_staff_query():
    print("\nTesting Staff Query for Bulk Messaging...")
    teaching = Staff.objects.filter(staff_type='teaching', user__isnull=False)
    print(f"Found {teaching.count()} teaching staff with users.")
    
    non_teaching = Staff.objects.filter(staff_type='non_teaching', user__isnull=False)
    print(f"Found {non_teaching.count()} non-teaching staff with users.")
    
    recipients = [s.user.email for s in teaching if s.user.email]
    print(f"Teaching staff emails: {recipients}")

if __name__ == "__main__":
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        print("⚠️  WARNING: EMAIL_HOST_USER or EMAIL_HOST_PASSWORD not set in environment.")
    
    test_single_email()
    test_bulk_function()
    test_staff_query()
