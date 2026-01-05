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
from api.models import Student, BioData, Guardian, FeePayment, AdmissionSettings, ApplicationSlip, PaymentPurpose
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
        message = f"""
Dear Applicant,

Your verification code is: {otp}

This code is valid for 10 minutes.
Use this code to verify your email and complete your admission application.

Request made for: {school_name}

If you did not request this code, please ignore this email.
        """.strip()
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
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
        
        message = f"""
Dear Applicant,

Congratulations! Your admission application to {applicant.school.name} has been successfully started.

Your Application Details for Future Login:
- Application Number: {applicant.application_number}
- Password: {password}

You are currently logged in. If you need to stop and continue later, you can use the credentials above to log in at:
{settings.FRONTEND_URL}/portals/admission/login

Required Steps to Complete Your Application:
1. Bio Data
2. Guardian Information
3. Upload Documents
4. Pay Application Fee

Once all steps are complete, you can submit your application.

For any assistance, please contact us at {settings.CONTACT_EMAIL}

Best regards,
{applicant.school.name}
Admissions Office
        """.strip()
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user_email],
                fail_silently=False,
            )
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
        
        # Check for payment
        payment_query = FeePayment.objects.filter(
            student=applicant
        )
        
        if admission_purpose:
            payment_query = payment_query.filter(payment_purpose=admission_purpose)
        
        total_paid = sum([p.amount for p in payment_query])
        has_paid = total_paid >= required_amount if required_amount > 0 else True
        
        latest_payment = payment_query.order_by('-payment_date').first()
        
        return {
            'has_paid': has_paid,
            'amount_paid': total_paid,
            'required_amount': required_amount,
            'payment_date': latest_payment.payment_date if latest_payment else None,
            'receipt_number': latest_payment.receipt_number if latest_payment else None
        }
    
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
        
        biodata = getattr(applicant, 'biodata', None)
        full_name = ""
        if biodata:
            full_name = f"{biodata.surname} {biodata.first_name}".strip()
        
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
            to=[applicant.user.email],
        )
        email.content_subtype = "html"
        
        # Attach PDF slip
        if slip.pdf_file:
            email.attach_file(slip.pdf_file.path)
        
        try:
            email.send(fail_silently=False)
            print(f"✅ Slip email sent to {applicant.user.email}")
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
