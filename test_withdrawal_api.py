#!/usr/bin/env python
"""
Test script for withdrawal API endpoints
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from api.models import Staff, StaffBeneficiary, StaffWallet

User = get_user_model()

# Get a staff user
staff_user = User.objects.filter(user_type='staff').first()
if not staff_user:
    print("❌ No staff user found")
    exit(1)

staff = Staff.objects.filter(user=staff_user).first()
if not staff:
    print("❌ No staff profile found")
    exit(1)

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
    print(f"First 5 banks: {[b['name'] for b in banks[:5]]}")
else:
    print(f"Error: {response.json()}")

# Test 3: Create a beneficiary
print("\n➕ Test 3: Create beneficiary")
beneficiary_data = {
    "bank_name": "Access Bank",
    "bank_code": "044",
    "account_number": "0123456789",
    "account_name": "Test User Account"
}
response = client.post('/api/beneficiaries/', beneficiary_data, format='json')
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 201:
    beneficiary_id = response.json()['id']
    
    # Test 4: Create withdrawal request
    print("\n💰 Test 4: Create withdrawal request")
    wallet = StaffWallet.objects.get(staff=staff)
    print(f"Current wallet balance: ₦{wallet.wallet_balance}")
    
    withdrawal_data = {
        "amount": 5000,
        "beneficiary_id": beneficiary_id
    }
    response = client.post('/api/staff/withdrawal-requests/', withdrawal_data, format='json')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Check wallet balance after
    wallet.refresh_from_db()
    print(f"New wallet balance: ₦{wallet.wallet_balance}")

print("\n✅ All tests completed!")
