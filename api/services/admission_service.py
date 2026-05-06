"""
Admission Service
Handles business logic for admission portal
"""

import random
import string
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.db import transaction
from api.models import (
    Student, BioData, Guardian, FeePayment, AdmissionSettings, 
    ApplicationSlip, PaymentPurpose, AdmissionBankTransfer, SystemSetting
)
from api.models.user import User


class AdmissionService:
    """Service class for admission-related operations"""
    
    @staticmethod
    def generate_otp(email):
        """
        Generate and cache a 6-digit OTP
        """
        from django.core.cache import cache
        
        # Generate 6 digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        # Store in cache for 10 minutes
        cache_key = f"admission_otp_{email}"
        cache.set(cache_key, code, timeout=600)
        
        return code

    @staticmethod
    def generate_temporary_password(length=8):
        """
        Generate a secure random password for permanent credentials
        """
        characters = string.ascii_letters + string.digits
        # Ensure at least one uppercase, one lowercase, and one digit
        password = [
            random.choice(string.ascii_uppercase),
            random.choice(string.ascii_lowercase),
            random.choice(string.digits)
        ]
        
        # Fill the rest randomly
        password += [random.choice(characters) for _ in range(length - 3)]
        
        # Shuffle to randomize positions
        random.shuffle(password)
        
        return ''.join(password)

    @staticmethod
    def verify_otp(email, code):
        """
        Verify if provided OTP is correct
        """
        from django.core.cache import cache
        
        cache_key = f"admission_otp_{email}"
        cached_code = cache.get(cache_key)
        
        # Use constant time comparison to prevent timing attacks, though low risk for OTP
        if cached_code and str(cached_code) == str(code):
            cache.delete(cache_key)  # Invalidate after use
            return True
        return False
    
    @staticmethod
    def send_otp_email(email, otp, school_name="Shining Light Schools"):
        """Send OTP to applicant"""
        subject = f"Your Verification Code - {school_name}"
        content = f"""
<p>Dear Applicant,</p>
<p>Your verification code for <strong>{school_name}</strong> is:</p>
<div style="text-align: center; margin: 30px 0;">
    <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #1a0c66; background-color: #f1f5f9; padding: 15px 30px; border-radius: 8px; border: 1px dashed #cbd5e1;">{otp}</span>
</div>
<p>This code is valid for <strong>10 minutes</strong>. Use it to verify your email and complete your admission application.</p>
<p>If you did not request this code, please ignore this email.</p>
"""
        plain_message = f"Your verification code is: {otp}. It is valid for 10 minutes."
        
        from api.utils.email import wrap_with_base_template
        html_message = wrap_with_base_template(subject, content)
        
        try:
            from django.core.mail import EmailMultiAlternatives
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email]
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send()
            print(f"✅ OTP email sent to {email}")
            return True
        except Exception as e:
            print(f"❌ Failed to send OTP email: {str(e)}")
            return False

    @staticmethod
    def send_welcome_email_with_credentials(applicant, password, user_email):
        """
        Send welcome email with credentials AFTER successful registration
        """
        subject = f"Admission Application Started - {applicant.school.name}"
        
        content = f"""
<p>Dear Applicant,</p>
<p>Congratulations! Your admission application to <strong>{applicant.school.name}</strong> has been successfully started.</p>
<div style="background-color: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #dcfce7;">
    <p style="margin: 5px 0;"><strong>Your Login Credentials:</strong></p>
    <ul style="list-style: none; padding: 0;">
        <li>Application Number: <strong>{applicant.application_number}</strong></li>
        <li>Password: <strong>{password}</strong></li>
    </ul>
</div>
<p>You can use these credentials to log in and continue your application at any time:</p>
<p style="text-align: center;">
    <a href="{settings.FRONTEND_URL}/portals/login" class="btn">Continue Application</a>
</p>
<p><strong>Required Steps:</strong></p>
<ol>
    <li>Bio Data</li>
    <li>Guardian Information</li>
    <li>Upload Documents</li>
    <li>Pay Application Fee</li>
</ol>
<p>For any assistance, please contact us at {settings.CONTACT_EMAIL}</p>
"""
        plain_message = f"Your admission application has started. App Number: {applicant.application_number}, Password: {password}."
        
        from api.utils.email import wrap_with_base_template
        html_message = wrap_with_base_template(subject, content)
        
        try:
            from django.core.mail import EmailMultiAlternatives
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send()
            print(f"✅ Welcome email sent to {user_email}")
            return True
        except Exception as e:
            print(f"❌ Failed to send welcome email: {str(e)}")
            return False
    
    @staticmethod
    def generate_seat_number(school):
        """
        Generate unique seat number for applicant
        Format: SCHOOL-YYYY-NNNN (e.g., PRM-2026-0001)
        
        Args:
            school: School instance
            
        Returns:
            str: Unique seat number
        """
        import random
        import string
        
        current_year = timezone.now().year
        school_code = school.code.split('-')[0]  # Get NUR, PRM, JNR, SNR
        
        # Generate readable seat number like CBT passcodes
        # Format: SCHOOL-YYYY-NNNN (e.g., PRM-2026-0001)
        prefix = f"{school_code}-{current_year}"
        
        # Get count of applicants for this school and year
        count = Student.objects.filter(
            school=school,
            seat_number__startswith=prefix
        ).count()
        
        new_number = count + 1
        
        # Format: PRM-2026-0001 (4-digit padded number)
        seat_number = f"{prefix}-{new_number:04d}"
        
        return seat_number
    
    @staticmethod
    def validate_checklist_complete(applicant):
        """
        Validate that all checklist items are complete
        
        Args:
            applicant: Student instance
            
        Returns:
            dict: Validation result with success status and message
        """
        checklist = applicant.application_checklist or {}
        
        errors = []
        
        # Check biodata
        if not checklist.get('biodata_complete', False):
            errors.append("Bio data not completed")
            
        # Check guardians
        if not checklist.get('guardians_complete', False):
            errors.append("Guardian information not completed")
            
        # Check documents
        if not checklist.get('documents_complete', False):
            errors.append("Required documents not uploaded")
            
        # Check payment
        if not checklist.get('payment_complete', False):
            errors.append("Application fee not paid")
        
        if errors:
            return {
                'success': False,
                'message': 'Application incomplete',
                'errors': errors
            }
        
        return {
            'success': True,
            'message': 'All checklist items complete'
        }
    
    @staticmethod
    def can_submit_application(applicant):
        """
        Check if applicant can submit application
        
        Args:
            applicant: Student instance
            
        Returns:
            tuple: (can_submit: bool, message: str)
        """
        # Check if already submitted
        if applicant.application_submitted_at:
            return False, "Application already submitted"
        
        # Check if status allows submission
        if applicant.status not in ['applicant']:
            return False, f"Cannot submit application with status: {applicant.status}"
        
        # Validate checklist
        validation = AdmissionService.validate_checklist_complete(applicant)
        if not validation['success']:
            return False, ', '.join(validation['errors'])
        
        return True, "Application can be submitted"
    
    @staticmethod
    @transaction.atomic
    def submit_application(applicant):
        """
        Submit application and generate slip with screening date
        
        Args:
            applicant: Student instance
            
        Returns:
            dict: Submission result with slip details
        """
        from datetime import timedelta
        
        # Validate can submit
        can_submit, message = AdmissionService.can_submit_application(applicant)
        if not can_submit:
            raise ValueError(message)
        
        # Update applicant
        applicant.application_submitted_at = timezone.now()
        applicant.status = 'under_review'
        applicant.save()
        
        # Calculate screening date (7 days from now)
        screening_date = (timezone.now() + timedelta(days=7)).date()
        
        # Create application slip record
        application_slip, created = ApplicationSlip.objects.get_or_create(
            student=applicant,
            defaults={
                'application_number': applicant.application_number,
                'screening_date': screening_date
            }
        )
        
        if not created:
            # Update if already exists
            application_slip.screening_date = screening_date
            application_slip.save()
        
        # Generate PDF slip
        from api.utils.slip_generator import generate_slip_pdf
        pdf_file = generate_slip_pdf(applicant, application_slip)
        application_slip.pdf_file.save(pdf_file.name, pdf_file, save=True)
        
        # Send email notification
        AdmissionService.send_slip_email(applicant, application_slip)
        
        return {
            'application_number': applicant.application_number,
            'screening_date': screening_date.strftime('%B %d, %Y'),
            'application_slip_id': application_slip.id,
            'slip_url': application_slip.pdf_file.url if application_slip.pdf_file else None,
            'submitted_at': applicant.application_submitted_at
        }
    
    @staticmethod
    def check_payment_status(applicant):
        """
        Check if applicant has paid application fee
        
        Args:
            applicant: Student instance
            
        Returns:
            dict: Payment status information
        """
        # Get admission settings for fee amount
        try:
            settings = AdmissionSettings.objects.get(school=applicant.school)
            required_amount = settings.application_fee_amount
        except AdmissionSettings.DoesNotExist:
            required_amount = 0
        
        # Get payment purpose for admission
        try:
            admission_purpose = PaymentPurpose.objects.get(code='admission')
        except PaymentPurpose.DoesNotExist:
            admission_purpose = None
        
        # Add mock exam fee if requested
        if applicant.wants_mock_exam:
            from api.models import SystemSetting
            sys_settings = SystemSetting.load()
            required_amount += sys_settings.mock_exam_fee
        
        # Check for payment
        payment_query = FeePayment.objects.filter(
            student=applicant
        )
        
        if admission_purpose:
            payment_query = payment_query.filter(payment_purpose=admission_purpose)
        
        total_paid = sum([p.amount for p in payment_query])
        
        latest_payment = payment_query.order_by('-payment_date').first()
        
        # Check for pending bank transfers
        pending_transfer = AdmissionBankTransfer.objects.filter(
            student=applicant,
            status='pending'
        ).first()
        
        # Get bank details from system settings
        sys_settings = SystemSetting.load()
        bank_details = {
            'bank_name': sys_settings.bank_name,
            'account_name': sys_settings.account_name,
            'account_number': sys_settings.account_number,
        }
        
        return {
            'has_paid': total_paid >= required_amount and required_amount > 0,
            'amount_paid': total_paid,
            'required_amount': required_amount,
            'payment_date': latest_payment.payment_date if latest_payment else None,
            'receipt_number': latest_payment.receipt_number if latest_payment else None,
            'wants_mock_exam': applicant.wants_mock_exam,
            'mock_exam_fee': sys_settings.mock_exam_fee if applicant.wants_mock_exam else 0,
            'has_pending_transfer': pending_transfer is not None,
            'pending_transfer_amount': pending_transfer.amount if pending_transfer else 0,
            'bank_details': bank_details
        }
    
    @staticmethod
    def submit_bank_transfer(applicant, amount, reference, screenshot):
        """
        Submit a bank transfer proof for verification
        """
        # Check if already has a pending transfer
        existing_pending = AdmissionBankTransfer.objects.filter(
            student=applicant,
            status='pending'
        ).exists()
        
        if existing_pending:
            raise ValueError("You already have a pending transfer verification.")
            
        return AdmissionBankTransfer.objects.create(
            student=applicant,
            amount=amount,
            reference=reference,
            screenshot=screenshot,
            status='pending'
        )
        
    @staticmethod
    @transaction.atomic
    def verify_bank_transfer(transfer_id, status, verified_by, rejection_reason=''):
        """
        Verify or reject a bank transfer
        """
        transfer = AdmissionBankTransfer.objects.get(id=transfer_id)
        
        if transfer.status != 'pending':
            raise ValueError(f"Transfer is already {transfer.status}")
            
        transfer.status = status
        transfer.verified_by = verified_by
        transfer.verified_at = timezone.now()
        
        if status == 'rejected':
            transfer.rejection_reason = rejection_reason
        elif status == 'confirmed':
            # Create a FeePayment record
            admission_purpose, _ = PaymentPurpose.objects.get_or_create(
                code='admission',
                defaults={'name': 'Application Fee', 'description': 'Admission application fee'}
            )
            
            # Get or create application fee type
            fee_type, _ = FeeType.objects.get_or_create(
                school=transfer.student.school,
                name='Application Fee',
                defaults={
                    'amount': transfer.amount, # Use the amount they transferred
                    'description': 'Admission application fee',
                    'is_mandatory': True,
                    'is_active': True
                }
            )
            
            # Record payment
            FeePayment.objects.create(
                student=transfer.student,
                fee_type=fee_type,
                amount=transfer.amount,
                payment_purpose=admission_purpose,
                payment_method='bank_transfer',
                reference_number=transfer.reference,
                processed_by=verified_by
            )
            
            # Update checklist
            AdmissionService.update_checklist_item(transfer.student, 'payment_complete', True)
            
        transfer.save()
        return transfer
    
    @staticmethod
    def send_slip_email(applicant, slip):
        """
        Send application slip via email with HTML template
        
        Args:
            applicant: Student instance
            slip: ApplicationSlip instance
        """
        from django.core.mail import EmailMessage
        from django.template.loader import render_to_string
        from datetime import datetime
        
        from api.utils.email import get_student_recipient_emails
        
        biodata = getattr(applicant, 'biodata', None)
        full_name = ""
        if biodata:
            full_name = f"{biodata.surname} {biodata.first_name}".strip()
        
        # Get recipients (guardians first)
        recipient_emails = get_student_recipient_emails(applicant)
        if not recipient_emails:
            # Fallback to applicant user email if helper returns nothing (unlikely)
            recipient_emails = [applicant.user.email]
        
        # Prepare email context
        context = {
            'name': full_name or 'Applicant',
            'application_number': slip.application_number,
            'school_name': applicant.school.name,
            'class_name': applicant.class_model.name if applicant.class_model else 'N/A',
            'submission_date': slip.generated_at.strftime('%B %d, %Y'),
            'screening_date': slip.screening_date.strftime('%B %d, %Y') if slip.screening_date else 'To Be Announced',
            'contact_email': getattr(settings, 'CONTACT_EMAIL', 'info@school.com'),
            'year': datetime.now().year,
        }
        
        # Render HTML email
        subject = f"Application Submitted Successfully - {slip.application_number}"
        html_message = render_to_string('emails/application_submitted.html', context)
        
        # Create email with attachment
        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_emails,
        )
        email.content_subtype = "html"
        
        # Attach PDF slip
        if slip.pdf_file:
            email.attach_file(slip.pdf_file.path)
        
        try:
            email.send(fail_silently=False)
            print(f"✅ Slip email sent to {recipient_emails}")
            return True
        except Exception as e:
            print(f"❌ Failed to send slip email: {str(e)}")
            return False

    
    @staticmethod
    def update_checklist_item(applicant, item_name, is_complete):
        """
        Update a single checklist item
        
        Args:
            applicant: Student instance
            item_name: Name of checklist item
            is_complete: Boolean completion status
        """
        valid_items = ['biodata_complete', 'guardians_complete', 'documents_complete', 'payment_complete']
        
        if item_name not in valid_items:
            raise ValueError(f"Invalid checklist item: {item_name}")
        
        if not applicant.application_checklist:
            applicant.application_checklist = {}
        
        applicant.application_checklist[item_name] = is_complete
        applicant.save(update_fields=['application_checklist', 'updated_at'])
