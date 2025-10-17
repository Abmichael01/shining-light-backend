"""
Email utilities for sending various notifications
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.crypto import get_random_string
import datetime


def generate_password(length=12):
    """
    Generate a secure random password
    Contains uppercase, lowercase, and numbers
    """
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    return get_random_string(length, chars)


def send_student_registration_email(student, password, request=None):
    """
    Send welcome email to newly registered student with login credentials
    
    Args:
        student: Student model instance
        password: Generated password (plain text)
        request: HTTP request object (optional, for getting domain)
    """
    try:
        # Get student email from user account
        student_email = student.user.email if hasattr(student, 'user') and student.user else None
        
        if not student_email:
            print(f"Warning: No email found for student {student.admission_number}")
            return False
        
        # Prepare context for template
        context = {
            'student_name': student.get_full_name(),
            'admission_number': student.admission_number,
            'email': student_email,
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

Dear {context['student_name']},

Your registration has been successfully completed.

Student Information:
- Name: {context['student_name']}
- Admission Number: {context['admission_number']}
- Class: {context['class_name']}
- School: {context['school_name']}

Your Login Credentials:
- Email/Username: {context['email']}
- Temporary Password: {context['password']}

Please log in to the student portal at: {context['portal_url']}

IMPORTANT: Change your password after your first login.

Best regards,
Shining Light School Administration
        """
        
        # Send email
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student_email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
        
        print(f"Registration email sent to {student_email} for student {student.admission_number}")
        return True
        
    except Exception as e:
        print(f"Error sending registration email: {str(e)}")
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


def template_exists(template_name):
    """Check if a template file exists"""
    from django.template.loader import get_template
    try:
        get_template(template_name)
        return True
    except:
        return False

