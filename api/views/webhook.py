from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import os
import hmac
import hashlib
from django.conf import settings
from django.utils import timezone
from api.models.fee import FeeType, FeePayment, PaymentPurpose
from api.models.student import Student
from api.models.staff import StaffWallet
from api.utils.email import (
    send_staff_funding_receipt,
    send_student_fee_receipt
)

@api_view(['POST'])
@permission_classes([AllowAny])
def paystack_webhook(request):
    """
    Handle Paystack webhook notifications for:
    1. Student Fees (Checkout)
    2. Admission Payments (Checkout)
    3. Staff Wallet Funding (Dedicated Account Transfer)
    """
    try:
        # Get Paystack secret key
        paystack_secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', os.getenv('PAYSTACK_SECRET_KEY'))
        
        if not paystack_secret_key:
            return Response({'error': 'Webhook not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Verify webhook signature
        signature = request.headers.get('X-Paystack-Signature', '')
        body = request.body
        
        # Compute expected signature
        expected_signature = hmac.new(
            paystack_secret_key.encode('utf-8'),
            body,
            hashlib.sha512
        ).hexdigest()
        
        if signature != expected_signature:
            print("❌ Invalid webhook signature")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Process webhook data
        data = request.data
        event = data.get('event')
        
        # --- SCENARIO: Paystack Transfers (Payouts/Withdrawals) ---
        if event in ['transfer.success', 'transfer.failed', 'transfer.reversed']:
            from api.models import StaffWalletTransaction
            transfer_data = data.get('data', {})
            transfer_code = transfer_data.get('transfer_code')
            reference = transfer_data.get('reference')
            
            # First try by reference (our WTH-... format)
            tx = StaffWalletTransaction.objects.filter(reference=reference, category='withdrawal').first()
            if not tx:
                # Fallback to transfer_code
                tx = StaffWalletTransaction.objects.filter(transfer_code=transfer_code, category='withdrawal').first()
                
            if tx:
                if event == 'transfer.success':
                    if tx.status != 'success':
                        # Balance was ALREADY deducted at creation time.
                        tx.status = 'success'
                        tx.processed_at = timezone.now()
                        tx.save()
                        
                        print(f"✅ Withdrawal Success: {tx.reference}")
                        
                elif event in ['transfer.failed', 'transfer.reversed']:
                    if tx.status not in ['failed', 'rejected']:
                         # Refund the wallet!
                        wallet = tx.wallet
                        wallet.wallet_balance += tx.amount
                        wallet.save()
                        
                        tx.status = 'failed'
                        tx.save()
                        
                        print(f"❌ Withdrawal Failed: {tx.reference} (Refunded)")
                
                return Response({'status': 'success'}, status=status.HTTP_200_OK)
            else:
                print(f"⚠️ Transfer event received but no matching withdrawal found: {reference} / {transfer_code}")
                return Response({'message': 'Transfer not matched'}, status=status.HTTP_200_OK)
        
        if event != 'charge.success':
            return Response({'message': 'Event ignored'}, status=status.HTTP_200_OK)
        
        payment_data = data.get('data', {})
        reference = payment_data.get('reference')
        metadata = payment_data.get('metadata', {})
        customer_data = payment_data.get('customer', {})
        customer_code = customer_data.get('customer_code')
        amount_paid = float(payment_data.get('amount', 0)) / 100  # Convert kobo to Naira
        
        if not reference:
            return Response({'error': 'No reference provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"🔔 Webhook received for {reference} (₦{amount_paid})")

        # --- SCENARIO 1: Staff Wallet Funding (via Dedicated Account) ---
        # Identified by Customer Code matching a StaffWallet
        if customer_code:
            wallet = StaffWallet.objects.filter(paystack_customer_code=customer_code).first()
            if wallet:
                # 1. Idempotency Check
                from api.models import StaffWalletTransaction
                
                # Check if we already processed this reference
                if StaffWalletTransaction.objects.filter(reference=reference).exists():
                    print(f"⚠️ Duplicate webhook for {reference}")
                    return Response({'message': 'Transaction already processed'}, status=status.HTTP_200_OK)
                
                # 2. Credit Wallet
                wallet.wallet_balance += type(wallet.wallet_balance)(amount_paid) # Decimal conversion
                wallet.save()
                
                # 3. Create Transaction Record
                StaffWalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='credit',
                    category='funding',
                    amount=amount_paid,
                    reference=reference,
                    status='success',
                    description=f"Wallet funding via Paystack"
                )
                
                print(f"💰 Wallet Funded: {wallet.staff.get_full_name()} +₦{amount_paid}")
                
                # Send Receipt
                send_staff_funding_receipt(wallet, amount_paid, reference)
                
                return Response({'status': 'success', 'message': 'Wallet funded'}, status=status.HTTP_200_OK)

        # --- SCENARIO 2: Student/Admission Payments ---
        
        # Determine payment type and get student
        student = None
        payment_purpose_code = metadata.get('purpose', 'general')
        
        # Handle admission payments (ADM-APP123-XXXXXXXX or ADM-APP-2025-0003-XXXXXXXX)
        if reference.startswith('ADM-'):
            try:
                # Remove 'ADM-' prefix and the random suffix (last 8 chars after last dash)
                # Reference format: ADM-{app_number}-{random_8_chars}
                # But sometimes it might just be ADM-{app_number}
                # Let's try to match by exact application number contained in ref
                
                parts = reference[4:].rsplit('-', 1)  # Split from right, once to remove UUID
                app_number = parts[0] if len(parts) > 0 else reference[4:]
                
                # Check directly first
                student = Student.objects.filter(application_number=app_number).first()
                if not student:
                     # Try searching if reference contains it
                     # This is heuristic. Best to trust metadata if available.
                     pass

                payment_purpose_code = 'admission'
            except Exception as e:
                print(f"❌ Error parsing admission ref: {e}")
        
        # Handle student payments with student ID in metadata (Preferred)
        if not student and metadata.get('student_id'):
            try:
                student = Student.objects.get(id=metadata['student_id'])
            except Student.DoesNotExist:
                print(f"❌ Student not found for ID: {metadata['student_id']}")
        
        # Handle student payments with admission number in metadata
        if not student and metadata.get('admission_number'):
            try:
                student = Student.objects.get(admission_number=metadata['admission_number'])
            except Student.DoesNotExist:
                print(f"❌ Student not found for admission number: {metadata['admission_number']}")
        
        if not student and not reference.startswith('ADM-'):
             # If strictly ADM, we might accept it even if student obj creation is delayed? 
             # No, Student must exist for Admission too (Applicant).
             pass

        if not student:
            print(f"❌ No student identified for reference: {reference}")
            return Response({'error': 'Student not identified'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if payment already recorded
        existing = FeePayment.objects.filter(student=student, reference_number=reference).exists()
        if existing:
            print(f"⚠️ Payment already recorded: {reference}")
            return Response({'message': 'Payment already recorded'}, status=status.HTTP_200_OK)
        
        # Get or create payment purpose
        payment_purpose, _ = PaymentPurpose.objects.get_or_create(
            code=payment_purpose_code,
            defaults={
                'name': metadata.get('purpose_name', payment_purpose_code.replace('_', ' ').title()),
                'description': f'Payment for {payment_purpose_code}'
            }
        )
        
        # Get fee type from metadata or find matching one
        fee_type_id = metadata.get('fee_type_id')
        fee_type = None
        
        if fee_type_id:
            try:
                fee_type = FeeType.objects.get(id=fee_type_id)
            except FeeType.DoesNotExist:
                print(f"❌ Fee type not found: {fee_type_id}")
                # We can continue without fee_type if it's generic admission?
                # But FeePayment requires fee_type usually? 
                # Model definition check: fee_type = models.ForeignKey(FeeType, ... null=True?)
                # Usually Not Null.
                pass
        
        if not fee_type and payment_purpose_code == 'admission':
             # Fallback: Find admission fee type for school
             fee_type = FeeType.objects.filter(school=student.school, name__icontains='Admission').first()

        if not fee_type:
             print("❌ Could not determine Fee Type. Cannot record payment.")
             return Response({'error': 'Fee Type required'}, status=status.HTTP_400_BAD_REQUEST)


        # Record Payment
        payment = FeePayment.objects.create(
            student=student,
            fee_type=fee_type,
            amount=amount_paid,
            payment_method='online',
            payment_date=timezone.now().date(),
            reference_number=reference,
            notes=f"Paystack Webhook: {reference}",
            processed_by=None # System
        )
        
        print(f"✅ Payment recorded: {payment.id} for {student.get_full_name()}")
        
        # Send Receipt
        send_student_fee_receipt(payment)
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Webhook Error: {str(e)}")
        # Return 200 to prevent Paystack from retrying endlessly if it's a logic error on our side
        # But 500 if transient.
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
