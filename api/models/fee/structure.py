from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum
from api.models.user import User
from api.models.academic import School, Class, SessionTerm, Session
from api.models.student import Student

class PaymentPurpose(models.Model):
    """Categorizes payments by functionality (admission, exams, tuition, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_purposes'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def clean(self):
        super().clean()
        if self.code and not self.code.islower():
            raise ValidationError({'code': 'Code must be lowercase with underscores'})


class FeeType(models.Model):
    """Define different types of fees (Admission, Tuition, etc.)"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    staff_children_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name='fee_types')
    applicable_classes = models.ManyToManyField(Class, blank=True, related_name='fee_types')
    max_installments = models.PositiveIntegerField(default=1)
    is_mandatory = models.BooleanField(default=True)
    is_recurring_per_term = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='fee_types_created')
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='required_by')
    active_terms = models.ManyToManyField(SessionTerm, blank=True, related_name='active_fees')
    
    class Meta:
        db_table = 'fee_types'
        ordering = ['school', 'name']
        unique_together = [['school', 'name']]
        indexes = [models.Index(fields=['school', 'is_active'])]
    
    def __str__(self):
        return f"{self.name} - {self.school.name} (₦{self.amount:,.2f})"
    
    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero.'})
        if self.max_installments < 1:
            raise ValidationError({'max_installments': 'Maximum installments must be at least 1.'})
    
    def get_applicable_amount(self, student):
        if self.staff_children_amount is not None and student.staff_parents.exists():
            return self.staff_children_amount
        return self.amount

    def is_applicable_to_class(self, class_id):
        if not self.applicable_classes.exists():
            return True
        return self.applicable_classes.filter(id=class_id).exists()
    
    def get_student_total_paid(self, student_id, session=None, session_term=None):
        from .payment import FeePayment
        filters = {'student_id': student_id, 'fee_type': self}
        if self.is_recurring_per_term and session_term:
            filters['session_term_id'] = session_term
        elif session:
            filters['session_id'] = session
        return FeePayment.objects.filter(**filters).aggregate(total=Sum('amount'))['total'] or 0
    
    def get_student_remaining(self, student_id, session=None, session_term=None):
        student = Student.objects.get(id=student_id)
        applicable_amount = self.get_applicable_amount(student)
        total_paid = self.get_student_total_paid(student_id, session, session_term)
        return max(0, applicable_amount - total_paid)
    
    def get_payment_status_context(self, student, session=None, session_term=None):
        from .payment import FeePayment
        applicable_amount = self.amount
        is_staff_child = getattr(student, 'is_staff_child_cached', student.staff_parents.exists())
        if self.staff_children_amount is not None and is_staff_child:
            applicable_amount = self.staff_children_amount
            
        filters = {'student': student, 'fee_type': self}
        if self.is_recurring_per_term:
            if session_term: filters['session_term'] = session_term
        elif session:
             filters['session'] = session
             
        payments_qs = FeePayment.objects.filter(**filters)
        total_paid = payments_qs.aggregate(total=Sum('amount'))['total'] or 0
        installments_made = payments_qs.count()
        
        status = 'unpaid'
        if total_paid >= applicable_amount: status = 'paid'
        elif total_paid > 0: status = 'partial'
        remaining = max(0, applicable_amount - total_paid)
        
        return {
            'applicable_amount': applicable_amount,
            'total_paid': total_paid,
            'amount_remaining': remaining,
            'status': status,
            'installments_made': installments_made,
            'is_staff_child': is_staff_child,
            'fee_type_id': self.id,
            'fee_type_name': self.name
        }

    def get_student_status(self, student_id, session=None, session_term=None):
        student = Student.objects.get(id=student_id)
        context = self.get_payment_status_context(student, session, session_term)
        return context['status']
