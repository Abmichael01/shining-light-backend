from rest_framework import serializers
from api.models import (
    Staff,
    LoanApplication,
    LoanPayment,
    StaffWallet,
    LoanTenure,
    User,
    WithdrawalRequest,
    StaffBeneficiary
)

class StaffWalletSerializer(serializers.ModelSerializer):
    """Serializer for StaffWallet model"""
    
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    
    class Meta:
        model = StaffWallet
        fields = [
            'id',
            'staff',
            'staff_name',
            'wallet_balance',
            'account_number',
            'bank_name',
            'account_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'staff', 'wallet_balance', 'paystack_customer_code', 'created_at', 'updated_at']


class StaffWalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for StaffWalletTransaction model"""
    
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        from api.models import StaffWalletTransaction
        model = StaffWalletTransaction
        fields = [
            'id',
            'wallet',
            'transaction_type',
            'transaction_type_display',
            'category',
            'category_display',
            'amount',
            'reference',
            'status',
            'status_display',
            'description',
            'created_at',
        ]
        read_only_fields = ['id', 'wallet', 'created_at']


class LoanTenureSerializer(serializers.ModelSerializer):
    """Serializer for LoanTenure"""
    class Meta:
        model = LoanTenure
        fields = ['id', 'name', 'duration_months', 'interest_rate', 'is_active']


class LoanPaymentSerializer(serializers.ModelSerializer):
    """Serializer for LoanPayment model"""
    
    application_number = serializers.CharField(source='loan_application.application_number', read_only=True)
    processed_by_email = serializers.EmailField(source='processed_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = LoanPayment
        fields = [
            'id',
            'loan_application',
            'application_number',
            'amount',
            'payment_date',
            'month',
            'year',
            'reference_number',
            'notes',
            'created_at',
            'processed_by',
            'processed_by_email'
        ]
        read_only_fields = ['id', 'created_at']


class LoanApplicationSerializer(serializers.ModelSerializer):
    """Serializer for LoanApplication model"""
    
    staff_name = serializers.SerializerMethodField()
    staff_id = serializers.CharField(source='staff.staff_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_email = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    amount_remaining = serializers.SerializerMethodField()
    loan_payments = LoanPaymentSerializer(many=True, read_only=True)
    
    # Tenure selection
    tenure_id = serializers.IntegerField(write_only=True, required=False)
    tenure_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LoanApplication
        fields = [
            'id',
            'application_number',
            'staff',
            'staff_name',
            'staff_id',
            'loan_amount',
            'interest_rate',
            'total_amount',
            'repayment_period_months',
            'monthly_deduction',
            'purpose',
            'status',
            'status_display',
            'application_date',
            'approval_date',
            'disbursement_date',
            'reviewed_by',
            'reviewed_by_email',
            'review_notes',
            'rejection_reason',
            'amount_paid',
            'amount_remaining',
            'loan_payments',
            'tenure_id',
            'tenure_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'application_number',
            'staff',
            'total_amount',
            'monthly_deduction',
            'application_date',
            'interest_rate', 
            'repayment_period_months', 
            'created_at',
            'updated_at'
        ]
    
    def get_staff_name(self, obj):
        """Return staff member's full name"""
        return obj.staff.get_full_name()
    
    def get_amount_paid(self, obj):
        """Return total amount paid"""
        return obj.get_amount_paid()
    
    def get_amount_remaining(self, obj):
        """Return remaining loan balance"""
        return obj.get_amount_remaining()

    def get_reviewed_by_email(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.email
        return None

    def get_tenure_name(self, obj):
        if obj.tenure:
            return obj.tenure.name
        return None

    def create(self, validated_data):
        """Handle tenure selection"""
        tenure_id = validated_data.pop('tenure_id', None)
        if tenure_id:
            try:
                tenure = LoanTenure.objects.get(id=tenure_id)
                validated_data['tenure'] = tenure
                # FORCE 0% Interest
                validated_data['interest_rate'] = 0 
                validated_data['repayment_period_months'] = tenure.duration_months
            except LoanTenure.DoesNotExist:
                raise serializers.ValidationError({"tenure_id": "Invalid tenure selected"})
        else:
             # Default 0 if no tenure
             validated_data['interest_rate'] = 0
        
        return super().create(validated_data)


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """Serializer for WithdrawalRequest"""
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    staff_id = serializers.CharField(source='staff.staff_id', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    beneficiary_id = serializers.IntegerField(write_only=True, required=True)
    
    class Meta:
        model = WithdrawalRequest
        fields = [
            'id',
            'reference_number',
            'staff',
            'staff_name',
            'staff_id',
            'amount',
            'account_number',
            'bank_name',
            'account_name',
            'status',
            'processed_by',
            'processed_by_name',
            'rejection_reason',
            'admin_notes',
            'created_at',
            'updated_at',
            'processed_at',
            'beneficiary_id'
        ]
        read_only_fields = [
            'id', 'staff', 'status', 'processed_by', 
            'processed_at', 'rejection_reason', 
            'admin_notes', 'created_at', 'updated_at'
        ]


    def create(self, validated_data):
        beneficiary_id = validated_data.pop('beneficiary_id')
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'staff'):
            raise serializers.ValidationError("Only staff members can make withdrawal requests")
            
        staff = request.user.staff
        
        try:
            beneficiary = StaffBeneficiary.objects.get(id=beneficiary_id, staff=staff)
        except StaffBeneficiary.DoesNotExist:
            raise serializers.ValidationError({"beneficiary_id": "Invalid beneficiary selected"})

        # Check balance
        try:
            wallet = staff.wallet
        except StaffWallet.DoesNotExist:
             raise serializers.ValidationError({"amount": "You do not have a wallet"})

        if wallet.wallet_balance < validated_data['amount']:
             raise serializers.ValidationError({"amount": "Insufficient wallet balance"})

        # Update validated_data with snapshot
        validated_data['staff'] = staff
        validated_data['account_number'] = beneficiary.account_number
        validated_data['bank_name'] = beneficiary.bank_name
        validated_data['account_name'] = beneficiary.account_name
        validated_data['status'] = 'processing' # Set to processing immediately
        
        # 1. Deduct Balance & create Transaction (Atomic ideally)
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Deduct balance
                wallet.wallet_balance -= validated_data['amount']
                wallet.save()
                
                # Create Withdrawal Request
                withdrawal = super().create(validated_data)
                
                # Create Transaction Record
                from api.models import StaffWalletTransaction
                StaffWalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='debit',
                    category='withdrawal',
                    amount=withdrawal.amount,
                    reference=withdrawal.reference_number,
                    status='pending', # Pending until webhook confirms success
                    description=f"Withdrawal to {beneficiary.bank_name} - {beneficiary.account_number}"
                )
        except Exception as e:
            raise serializers.ValidationError({"error": f"Failed to process withdrawal: {str(e)}"})

        # 2. Initiate Paystack Transfer
        from api.utils.paystack import Paystack
        paystack = Paystack()
        
        # Ensure recipient code exists
        recipient_code = beneficiary.paystack_recipient_code
        if not recipient_code:
            recipient = paystack.create_transfer_recipient(
                name=beneficiary.account_name,
                account_number=beneficiary.account_number,
                bank_code=beneficiary.bank_code
            )
            if recipient:
                recipient_code = recipient.get('recipient_code')
                beneficiary.paystack_recipient_code = recipient_code
                beneficiary.save()
        
        if recipient_code:
            transfer = paystack.initiate_transfer(
                amount=withdrawal.amount,
                recipient_code=recipient_code,
                reference=withdrawal.reference_number,
                reason=f"Withdrawal for {staff.get_full_name()}"
            )
            if transfer:
                withdrawal.transfer_code = transfer.get('transfer_code')
                withdrawal.save()
            else:
                # If transfer initiation fails, refund and delete
                wallet.wallet_balance += withdrawal.amount
                wallet.save()
                
                # Mark transaction as failed or delete it? 
                # Better to update status to failed
                tx = StaffWalletTransaction.objects.filter(reference=withdrawal.reference_number).first()
                if tx:
                    tx.status = 'failed'
                    tx.save()
                
                withdrawal.status = 'rejected'
                withdrawal.rejection_reason = "Failed to initiate transfer with Paystack"
                withdrawal.save()
                
                raise serializers.ValidationError({
                    "non_field_errors": ["Failed to initiate withdrawal. Your wallet has been refunded."]
                })
        else:
             # Refund
             wallet.wallet_balance += withdrawal.amount
             wallet.save()
             
             tx = StaffWalletTransaction.objects.filter(reference=withdrawal.reference_number).first()
             if tx:
                tx.status = 'failed'
                tx.save()
             
             withdrawal.delete()
             raise serializers.ValidationError({
                 "beneficiary_id": ["Could not verify this beneficiary with Paystack. Wallet refunded."]
             })
                
        return withdrawal


class StaffBeneficiarySerializer(serializers.ModelSerializer):
    """Serializer for StaffBeneficiary"""
    class Meta:
        model = StaffBeneficiary
        fields = [
            'id',
            'staff',
            'bank_name',
            'bank_code',
            'account_number',
            'account_name',
            'is_verified',
            'created_at'
        ]
        read_only_fields = ['id', 'staff', 'is_verified', 'created_at']
