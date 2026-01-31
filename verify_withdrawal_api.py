#!/usr/bin/env python
"""
Verification script for withdrawal API endpoints.
Renamed to avoid pytest collection.
"""
import os
import django

# Set environment variables BEFORE setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
os.environ['ALLOWED_HOSTS'] = 'testserver,localhost,127.0.0.1'
os.environ['DEBUG'] = 'True'  # Force Debug to allow testserver host

django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from api.models import Staff, StaffBeneficiary, StaffWallet

def run_tests():
    User = get_user_model()

    # Get a staff user
    staff_user = User.objects.filter(user_type='staff').first()
    if not staff_user:
        print("❌ No staff user found")
        return

    staff = Staff.objects.filter(user=staff_user).first()
    if not staff:
        print("❌ No staff profile found")
        return

    print(f"✅ Testing with staff: {staff.get_full_name()} ({staff.staff_id})")

    # Create API client and authenticate
    client = APIClient()
    client.force_authenticate(user=staff_user)

    # Test 1: List beneficiaries
    print("\n📋 Test 1: List beneficiaries")
    response = client.get('/api/beneficiaries/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error content: {response.content.decode()}")

    # Test 2: List banks
    print("\n🏦 Test 2: List banks")
    response = client.get('/api/beneficiaries/list_banks/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        banks = response.json()
        print(f"Found {len(banks)} banks")
        # print(f"First 5 banks: {[b['name'] for b in banks[:5]]}")
    else:
        print(f"Error content: {response.content.decode()}")

    # Test 3: Create a beneficiary
    print("\n➕ Test 3: Create beneficiary")
    beneficiary_data = {
        "bank_name": "Access Bank",
        "bank_code": "044",
        "account_number": "0123456789",
        "account_name": "Test User Account"
    }
    
    # Check if exists first to avoid dupes logic (though serializer might handle it)
    existing = StaffBeneficiary.objects.filter(
        staff=staff, 
        account_number="0123456789", 
        bank_code="044"
    ).first()
    
    if existing:
        print("Beneficiary already exists, using existing ID.")
        beneficiary_id = existing.id
    else:
        response = client.post('/api/beneficiaries/', beneficiary_data, format='json')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            beneficiary_id = response.json()['id']
        else:
            print("Failed to create beneficiary")
            beneficiary_id = None

    if beneficiary_id:
        # Test 4: Create withdrawal request
        print("\n💰 Test 4: Create withdrawal request")
        
        # Ensure wallet exists
        wallet, created = StaffWallet.objects.get_or_create(staff=staff)
        if created:
            wallet.wallet_balance = 10000
            wallet.save()
            print("Created wallet with 10000 balance")
        elif wallet.wallet_balance < 5000:
            wallet.wallet_balance += 5000
            wallet.save()
            print("Top-up wallet for testing")
            
        print(f"Current wallet balance: ₦{wallet.wallet_balance}")
        
        withdrawal_data = {
            "amount": 5000,
            "beneficiary_id": beneficiary_id
        }
        response = client.post('/api/withdrawal-requests/', withdrawal_data, format='json')
        print(f"Testing URL: /api/withdrawal-requests/")

        print(f"Status: {response.status_code}")
        if response.status_code < 400:
             print(f"Response: {response.json()}")
             
             # Check wallet balance after
             wallet.refresh_from_db()
             print(f"New wallet balance: ₦{wallet.wallet_balance}")
        else:
             print(f"Error: {response.content.decode()}")


if __name__ == "__main__":
    run_tests()
