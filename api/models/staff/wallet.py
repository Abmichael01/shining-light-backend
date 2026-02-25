from django.db import models
from django.utils.translation import gettext_lazy as _
from .staff import Staff

class StaffWallet(models.Model):
    """Staff digital wallet for loan disbursements and repayments"""
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name='wallet')
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    paystack_customer_code = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=20, blank=True, help_text="Virtual Account Number")
    bank_name = models.CharField(max_length=100, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'staff_wallets'
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - Wallet (₦{self.wallet_balance:,.2f})"

    def create_virtual_account(self):
        from api.utils.paystack import Paystack
        paystack = Paystack()
        
        email = self.staff.user.email if self.staff.user.email else f"staff_{self.staff.staff_id}@school.com"
        customer = paystack.create_customer(
            email=email, first_name=self.staff.first_name, last_name=self.staff.surname, phone=self.staff.phone_number
        )
        
        if customer and 'customer_code' in customer:
            self.paystack_customer_code = customer['customer_code']
            self.save()
            dva = paystack.create_dedicated_account(self.paystack_customer_code)
            if dva:
                bank_data = dva.get('bank', {})
                self.account_number = dva.get('account_number')
                self.bank_name = bank_data.get('name', 'Wema Bank')
                self.account_name = dva.get('account_name', f"{self.staff.get_full_name()}")
                self.save()
                return True
        return False


class StaffWalletTransaction(models.Model):
    """History of all transactions on a staff wallet"""
    
    TRANSACTION_TYPES = [('credit', 'Credit'), ('debit', 'Debit')]
    CATEGORY_CHOICES = [
        ('funding', 'Wallet Funding'), ('withdrawal', 'Withdrawal'),
        ('loan_disbursement', 'Loan Disbursement'), ('loan_repayment', 'Loan Repayment'),
        ('salary', 'Salary Payment'), ('other', 'Other'),
    ]
    STATUS_CHOICES = [('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')]

    wallet = models.ForeignKey(StaffWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.CharField(max_length=255)
    
    transfer_code = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=20, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'staff_wallet_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"{self.wallet.staff.get_full_name()} - {self.get_transaction_type_display()} ₦{self.amount} ({self.status})"
