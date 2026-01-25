from rest_framework import serializers
from api.models import (
    Staff,
    LoanApplication,
    LoanPayment,
    StaffWallet,
    LoanTenure,
    User
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
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, allow_null=True)
    amount_paid = serializers.SerializerMethodField()
    amount_remaining = serializers.SerializerMethodField()
    loan_payments = LoanPaymentSerializer(many=True, read_only=True)
    
    # Tenure selection
    tenure_id = serializers.IntegerField(write_only=True, required=False)
    tenure_name = serializers.CharField(source='tenure.name', read_only=True)
    
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
