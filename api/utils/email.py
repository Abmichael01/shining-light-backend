"""
Email utilities for sending various notifications
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.crypto import get_random_string
import datetime
from django.utils.html import strip_tags

def wrap_with_base_template(subject, content):
    """
    Wraps the provided HTML content in the school's professional base template.
    """
    context = {
        'subject': subject,
        'content': content,
        'year': datetime.datetime.now().year,
    }
    try:
        return render_to_string('emails/base_template.html', context)
    except Exception as e:
        print(f"Template rendering failed: {e}")
        # Fallback to just the raw content if template missing
        return content
def generate_password(length=12):
    """
    Generate a secure random password
    Contains uppercase, lowercase, and numbers
    """
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    return get_random_string(length, chars)


def get_student_recipient_emails(student):
    """
    Resolve the best email recipient(s) for a student.

    Since most primary/secondary school students don't have their own
    email, this prioritises guardian (parent) emails over the student's
    own account email.

    Resolution order:
      1. Primary contact guardian email
      2. Any guardian email (father -> mother -> guardian)
      3. Student's own user account email (last resort)

    Returns a list of at least one email address, or an empty list if
    none found.
    """
    emails = []

    try:
        guardians = student.guardians.all()

        # Priority 1: primary contact with an email
        primary = guardians.filter(is_primary_contact=True).first()
        if primary and primary.email:
            emails.append(primary.email)

        # Priority 2: any other guardian with an email (avoid duplicates)
        for guardian in guardians.order_by('guardian_type'):
            if guardian.email and guardian.email not in emails:
                emails.append(guardian.email)
    except Exception:
        pass

    # Last resort: student's own account email
    if not emails:
        student_email = student.user.email if hasattr(student, 'user') and student.user else None
        if student_email:
            emails.append(student_email)

    return emails


def send_student_registration_email(student, password, request=None):
    """
    Send welcome email to newly registered student with login credentials
    
    Args:
        student: Student model instance
        password: Generated password (plain text)
        request: HTTP request object (optional, for getting domain)
    """
    try:
        recipient_emails = get_student_recipient_emails(student)
        
        if not recipient_emails:
            print(f"Warning: No email found for student {student.admission_number}")
            return False
        
        # Use the first (best) email for the login credentials line in the template.
        # The user account email is what they use to log in.
        student_login_email = student.user.email if hasattr(student, 'user') and student.user else recipient_emails[0]

        # Prepare context for template
        context = {
            'student_name': student.get_full_name(),
            'admission_number': student.admission_number,
            'email': student_login_email,
            'password': password,
            'class_name': student.class_model.name if student.class_model else 'Not assigned',
            'school_name': student.school.name if student.school else 'Shining Light School',
            'portal_url': request.build_absolute_uri('/portals/login') if request else 'http://localhost:3000/portals/login',
            'year': datetime.datetime.now().year,
        }
        
        # Render email template
        subject = f'Welcome to Shining Light School - Login Credentials'
        html_message = render_to_string('emails/student_registration.html', context)
        
        # Create plain text version (fallback)
        plain_message = f"""
Welcome to Shining Light School!

Dear Parent/Guardian of {context['student_name']},

Your ward's registration has been successfully completed.

Student Information:
- Name: {context['student_name']}
- Admission Number: {context['admission_number']}
- Class: {context['class_name']}
- School: {context['school_name']}

Login Credentials for Student Portal:
- Email/Username: {context['email']}
- Temporary Password: {context['password']}

Please log in to the student portal at: {context['portal_url']}

IMPORTANT: Change the password after the first login.

Best regards,
Shining Light School Administration
        """
        
        # Send email to all resolved guardian/parent emails
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_emails
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
        
        print(f"Registration email sent to {recipient_emails} for student {student.admission_number}")
        return True
        
    except Exception as e:
        print(f"Error sending registration email: {str(e)}")
        return False


def send_staff_registration_email(staff, password, request=None):
    """
    Send welcome email to newly registered staff with login credentials.

    Args:
        staff: Staff model instance
        password: Generated password (plain text)
        request: HTTP request object (optional, for building portal URL)
    """
    try:
        staff_email = staff.user.email if hasattr(staff, 'user') and staff.user else None

        if not staff_email:
            print(f"Warning: No email found for staff {staff.staff_id}")
            return False

        context = {
            'staff_name': staff.get_full_name(),
            'staff_id': staff.staff_id,
            'staff_type': staff.get_staff_type_display(),
            'zone': staff.get_zone_display(),
            'email': staff_email,
            'password': password,
            'portal_url': request.build_absolute_uri('/portals/staff') if request else 'http://localhost:3000/portals/staff',
            'year': datetime.datetime.now().year,
        }

        subject = 'Staff Portal Credentials - Shining Light School'
        template_name = 'emails/staff_registration.html'
        html_message = render_to_string(template_name, context) if template_exists(template_name) else None

        plain_message = f"""
Welcome to Shining Light School!

Dear {context['staff_name']},

Your staff portal account has been created.

Staff Information:
- Name: {context['staff_name']}
- Staff ID: {context['staff_id']}
- Staff Type: {context['staff_type']}
- Zone: {context['zone']}

Login Credentials:
- Email/Username: {context['email']}
- Temporary Password: {context['password']}

Portal URL: {context['portal_url']}

IMPORTANT: Change your password immediately after logging in.

Best regards,
Shining Light School Administration
"""

        if html_message:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[staff_email],
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send()
        else:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[staff_email],
                fail_silently=False,
            )

        print(f"Staff registration email sent to {staff_email} for staff {staff.staff_id}")
        return True

    except Exception as e:
        print(f"Error sending staff registration email: {str(e)}")
        return False


def send_password_reset_email(user, reset_link):
    """
    Send password reset email to user
    
    Args:
        user: User model instance
        reset_link: Password reset URL
    """
    try:
        context = {
            'user_name': user.get_full_name() if hasattr(user, 'get_full_name') else user.email,
            'reset_link': reset_link,
            'year': datetime.datetime.now().year,
        }
        
        subject = 'Password Reset Request - Shining Light School'
        html_message = render_to_string('emails/password_reset.html', context) if template_exists('emails/password_reset.html') else None
        
        plain_message = f"""
Password Reset Request

Dear {context['user_name']},

We received a request to reset your password for your Shining Light School account.

Click the link below to reset your password:
{reset_link}

This link will expire in 24 hours.

If you did not request a password reset, please ignore this email.

Best regards,
Shining Light School Administration
        """
        
        if html_message:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send()
        else:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        
        return True
        
    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
        return False


def send_withdrawal_status_email(withdrawal, status_type):
    """
    Send email notification for withdrawal status updates
    
    Args:
        withdrawal: WithdrawalRequest model instance
        status_type: 'success' or 'failed'
    """
    try:
        staff = withdrawal.staff
        staff_email = staff.user.email if hasattr(staff, 'user') and staff.user else None
        
        if not staff_email:
            return False
            
        context = {
            'staff_name': staff.get_full_name(),
            'amount': withdrawal.amount,
            'reference': withdrawal.reference_number,
            'account_details': f"{withdrawal.bank_name} - {withdrawal.account_number}",
            'status': status_type,
            'reason': withdrawal.rejection_reason if status_type == 'failed' else None,
            'year': datetime.datetime.now().year,
        }
        
        subject = f'Withdrawal {status_type.title()} - Shining Light School'
        
        if status_type == 'success':
            content = f"""
<p>Dear {context['staff_name']},</p>
<p>Your withdrawal of <strong>₦{context['amount']:,}</strong> has been successfully processed.</p>
<div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
    <p style="margin: 5px 0;"><strong>Transaction Details:</strong></p>
    <ul style="list-style: none; padding: 0;">
        <li>Reference: {context['reference']}</li>
        <li>Destination: {context['account_details']}</li>
        <li>Status: <span style="color: #10b981; font-weight: bold;">Completed</span></li>
    </ul>
</div>
<p>The funds should arrive in your bank account shortly.</p>
"""
            plain_message = f"Dear {context['staff_name']}, Your withdrawal of ₦{context['amount']:,} has been successfully processed. Reference: {context['reference']}."
        else:
            content = f"""
<p>Dear {context['staff_name']},</p>
<p>Your withdrawal of <strong>₦{context['amount']:,}</strong> could not be processed.</p>
<div style="background-color: #fef2f2; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #fee2e2;">
    <p style="margin: 5px 0;"><strong>Transaction Details:</strong></p>
    <ul style="list-style: none; padding: 0;">
        <li>Reference: {context['reference']}</li>
        <li>Status: <span style="color: #ef4444; font-weight: bold;">Failed</span></li>
        <li>Reason: {context['reason']}</li>
    </ul>
</div>
<p>Please contact administration or try again later.</p>
"""
            plain_message = f"Dear {context['staff_name']}, Your withdrawal of ₦{context['amount']:,} could not be processed. Reason: {context['reason']}."
        
        html_message = wrap_with_base_template(subject, content)
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[staff_email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
        return True
    except Exception as e:
        print(f"Error sending withdrawal email: {str(e)}")
        return False



def send_staff_funding_receipt(wallet, amount, reference):
    """
    Send receipt for staff wallet funding
    
    Args:
        wallet: StaffWallet model instance
        amount: Amount funded
        reference: Transaction reference
    """
    try:
        staff = wallet.staff
        staff_email = staff.user.email if hasattr(staff, 'user') and staff.user else None
        
        if not staff_email:
            return False
            
        context = {
            'staff_name': staff.get_full_name(),
            'amount': amount,
            'reference': reference,
            'balance': wallet.wallet_balance,
            'date': datetime.datetime.now().strftime("%B %d, %Y"),
            'year': datetime.datetime.now().year,
        }
        
        subject = 'Wallet Funding Receipt - Shining Light School'
        
        content = f"""
<p>Dear {context['staff_name']},</p>
<p>Your wallet has been successfully funded.</p>
<div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
    <p style="margin: 5px 0;"><strong>Transaction Details:</strong></p>
    <ul style="list-style: none; padding: 0;">
        <li>Amount: <strong>₦{context['amount']:,}</strong></li>
        <li>Reference: {context['reference']}</li>
        <li>Date: {context['date']}</li>
    </ul>
    <p style="margin: 15px 0 0 0; font-size: 18px;">Current Balance: <strong>₦{context['balance']:,}</strong></p>
</div>
<p>Thank you for using Shining Light School Portal.</p>
"""
        plain_message = f"Dear {context['staff_name']}, Your wallet has been successfully funded with ₦{context['amount']:,}. Current Balance: ₦{context['balance']:,}."
        
        html_message = wrap_with_base_template(subject, content)
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[staff_email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
        return True
    except Exception as e:
        print(f"Error sending funding receipt: {str(e)}")
        return False


def send_student_fee_receipt(payment):
    """
    Send receipt for student fee payment
    
    Args:
        payment: FeePayment model instance
    """
    try:
        student = payment.student

        recipient_emails = get_student_recipient_emails(student)

        if not recipient_emails:
            print(f"Warning: No email found for student {student.admission_number}")
            return False
            
        context = {
            'student_name': student.get_full_name(),
            'admission_number': student.admission_number,
            'amount': payment.amount,
            'purpose': payment.fee_type.name if payment.fee_type else "School Fees",
            'reference': payment.reference_number,
            'date': payment.payment_date,
            'year': datetime.datetime.now().year,
        }
        
        subject = 'Payment Receipt - Shining Light School'
        
        content = f"""
<p>Dear Parent/Guardian of {context['student_name']},</p>
<p>We have received a payment for your ward.</p>
<div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
    <p style="margin: 5px 0;"><strong>Payment Details:</strong></p>
    <ul style="list-style: none; padding: 0;">
        <li>Student: {context['student_name']} ({context['admission_number']})</li>
        <li>Purpose: {context['purpose']}</li>
        <li>Amount: <strong>₦{context['amount']:,}</strong></li>
        <li>Reference: {context['reference']}</li>
        <li>Date: {context['date']}</li>
    </ul>
</div>
<p>This email serves as your official receipt.</p>
"""
        plain_message = f"Payment receipt for {context['student_name']}. Amount: ₦{context['amount']:,}. Purpose: {context['purpose']}. Reference: {context['reference']}."
        
        html_message = wrap_with_base_template(subject, content)
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_emails
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
        return True
    except Exception as e:
        print(f"Error sending fee receipt: {str(e)}")
        return False


def template_exists(template_name):
    """Check if a template file exists"""
    from django.template.loader import get_template
    try:
        get_template(template_name)
        return True
    except:
        return False


def send_bulk_email(recipient_list, subject, message_body, connection=None):
    """
    Send mass emails to a list of recipients.
    """
    try:
        from django.utils.html import strip_tags
        
        # Use send_mail which handles mass mailing efficiently or loop.
        # For very large lists, we should use send_mass_mail or a background task.
        
        if not message_body.strip().startswith('<!DOCTYPE html>'):
            message_body = wrap_with_base_template(subject, message_body)
            
        plain_message = strip_tags(message_body)
        
        from django.core.mail import EmailMultiAlternatives
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEFAULT_FROM_EMAIL],
            bcc=recipient_list,
            connection=connection
        )
        email.attach_alternative(message_body, "text/html")
        email.send(fail_silently=False)
        
        return True, f"Emails sent to {len(recipient_list)} recipients"
    except Exception as e:
        print(f"Error sending bulk email: {str(e)}")
        return False, str(e)


def send_login_notification_email(user, request=None):
    """
    Send a notification email when a new login occurs.
    """
    try:
        user_email = user.email
        if not user_email:
            return False

        # Get device info from request if available
        user_agent = 'Unknown Device'
        ip_address = 'Unknown IP'
        
        if request:
            user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown Device')
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR', 'Unknown IP')

        context = {
            'user_name': user.get_full_name() if hasattr(user, 'get_full_name') else 'User',
            'email': user_email,
            'time': datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            'device': user_agent,
            'ip': ip_address,
            'year': datetime.datetime.now().year,
        }

        subject = 'New Login Alert - Shining Light School'

        content = f"""
<p>Dear {context['user_name']},</p>
<p>A new login to your Shining Light School account was detected.</p>
<div style="background-color: #fff7ed; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #ffedd5;">
    <p style="margin: 5px 0;"><strong>Login Details:</strong></p>
    <ul style="list-style: none; padding: 0;">
        <li>Account: {context['email']}</li>
        <li>Time: {context['time']}</li>
        <li>Device: {context['device']}</li>
        <li>IP Address: {context['ip']}</li>
    </ul>
</div>
<p>If this was you, you can safely ignore this email. If you did not authorize this login, please change your password immediately.</p>
"""
        plain_message = f"New login detected for {context['email']} at {context['time']} from {context['device']} ({context['ip']})."
        
        html_message = wrap_with_base_template(subject, content)
        
        recipient_list = [user_email]
        
        # If user is a student, also notify guardians
        if user.user_type == 'student' and hasattr(user, 'student_profile'):
            student_recipients = get_student_recipient_emails(user.student_profile)
            for email in student_recipients:
                if email not in recipient_list:
                    recipient_list.append(email)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
        return True
    except Exception as e:
        print(f"Error sending login notification: {str(e)}")
        return False

