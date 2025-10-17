"""
Serializers for fee-related models
"""
from rest_framework import serializers
from api.models import FeeType, FeePayment, Student
from django.db.models import Sum
from django.utils import timezone


class FeeTypeSerializer(serializers.ModelSerializer):
    """Serializer for FeeType model"""
    
    school_name = serializers.CharField(source='school.name', read_only=True)
    applicable_class_names = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)
    payment_count = serializers.SerializerMethodField()
    total_collected = serializers.SerializerMethodField()
    
    class Meta:
        model = FeeType
        fields = [
            'id',
            'name',
            'description',
            'amount',
            'school',
            'school_name',
            'applicable_classes',
            'applicable_class_names',
            'max_installments',
            'is_mandatory',
            'is_recurring_per_term',
            'is_active',
            'created_at',
            'updated_at',
            'created_by',
            'created_by_email',
            'payment_count',
            'total_collected',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_applicable_class_names(self, obj):
        """Get names of applicable classes"""
        if not obj.applicable_classes.exists():
            return "All Classes"
        return ", ".join([c.name for c in obj.applicable_classes.all()])
    
    def get_payment_count(self, obj):
        """Get total number of payments for this fee type"""
        return obj.payments.count()
    
    def get_total_collected(self, obj):
        """Get total amount collected for this fee type"""
        total = obj.payments.aggregate(total=Sum('amount'))['total']
        return float(total) if total else 0.0


class FeePaymentSerializer(serializers.ModelSerializer):
    """Serializer for FeePayment model"""
    
    student_name = serializers.SerializerMethodField()
    student_admission_number = serializers.CharField(source='student.admission_number', read_only=True)
    fee_type_name = serializers.CharField(source='fee_type.name', read_only=True)
    fee_type_amount = serializers.DecimalField(
        source='fee_type.amount',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    session_name = serializers.CharField(source='session.name', read_only=True, allow_null=True)
    session_term_name = serializers.CharField(source='session_term.term_name', read_only=True, allow_null=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    processed_by_email = serializers.EmailField(source='processed_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = FeePayment
        fields = [
            'id',
            'student',
            'student_name',
            'student_admission_number',
            'fee_type',
            'fee_type_name',
            'fee_type_amount',
            'amount',
            'installment_number',
            'session',
            'session_name',
            'session_term',
            'session_term_name',
            'payment_date',
            'payment_method',
            'payment_method_display',
            'reference_number',
            'receipt_number',
            'notes',
            'created_at',
            'processed_by',
            'processed_by_email',
        ]
        read_only_fields = ['id', 'receipt_number', 'created_at']
    
    def get_student_name(self, obj):
        """Return student's full name"""
        return obj.student.get_full_name()


class StudentFeeStatusSerializer(serializers.Serializer):
    """Serializer for student fee status (for student portal)"""
    
    fee_type_id = serializers.IntegerField()
    fee_type_name = serializers.CharField()
    fee_type_description = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_remaining = serializers.DecimalField(max_digits=10, decimal_places=2)
    installments_made = serializers.IntegerField()
    installments_allowed = serializers.IntegerField()
    status = serializers.CharField()  # paid, partial, unpaid
    is_mandatory = serializers.BooleanField()
    is_recurring = serializers.BooleanField()
    payments = FeePaymentSerializer(many=True, read_only=True)


class RecordFeePaymentSerializer(serializers.Serializer):
    """Serializer for recording a fee payment"""
    
    student = serializers.IntegerField()
    fee_type = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_date = serializers.DateField(required=False)
    payment_method = serializers.ChoiceField(
        choices=FeePayment.PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    reference_number = serializers.CharField(required=False, allow_blank=True)
    session = serializers.IntegerField(required=False, allow_null=True)
    session_term = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate payment data"""
        # Validate amount
        if data['amount'] <= 0:
            raise serializers.ValidationError({
                'amount': 'Payment amount must be greater than zero.'
            })
        
        return data
    
    def create(self, validated_data):
        """Create fee payment"""
        # Get the request user for processed_by
        request = self.context.get('request')
        processed_by = request.user if request else None
        
        # Get existing payments to calculate installment number
        existing_payments = FeePayment.objects.filter(
            student_id=validated_data['student'],
            fee_type_id=validated_data['fee_type'],
            session_id=validated_data.get('session'),
            session_term_id=validated_data.get('session_term'),
        )
        
        installment_number = existing_payments.count() + 1
        
        # Create payment
        payment = FeePayment.objects.create(
            student_id=validated_data['student'],
            fee_type_id=validated_data['fee_type'],
            amount=validated_data['amount'],
            installment_number=installment_number,
            payment_date=validated_data.get('payment_date', timezone.now().date()),
            payment_method=validated_data.get('payment_method', 'cash'),
            reference_number=validated_data.get('reference_number', ''),
            session_id=validated_data.get('session'),
            session_term_id=validated_data.get('session_term'),
            notes=validated_data.get('notes', ''),
            processed_by=processed_by
        )
        
        return payment


