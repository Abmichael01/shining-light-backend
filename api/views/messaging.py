from rest_framework import views, response, status, permissions
from django.shortcuts import get_object_or_404
from django.utils import timezone
from api.models import Student, Staff, User, Guardian, GuardianMessage
from api.utils.sms import send_sms as termii_send_sms
from api.utils.email import send_bulk_email, get_student_recipient_emails
from django.core.mail import get_connection
import logging

logger = logging.getLogger(__name__)

class SendSMSView(views.APIView):
    """
    Send single SMS to a student or staff
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        target_type = request.data.get('target_type')  # 'student' or 'staff'
        target_id = request.data.get('target_id')
        message = request.data.get('message')
        
        if not all([target_type, target_id, message]):
            return response.Response(
                {"error": "target_type, target_id, and message are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        phone_number = None
        if target_type == 'student':
            student = get_object_or_404(Student, id=target_id)
            # Try to get phone from primary guardian
            primary_guardian = student.guardians.filter(is_primary_contact=True).first()
            if primary_guardian:
                phone_number = primary_guardian.phone_number
            else:
                # Fallback to any guardian
                any_guardian = student.guardians.first()
                if any_guardian:
                    phone_number = any_guardian.phone_number
        elif target_type == 'staff':
            staff = get_object_or_404(Staff, id=target_id)
            phone_number = staff.phone_number
        else:
            return response.Response(
                {"error": "Invalid target_type. Use 'student' or 'staff'"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not phone_number:
            return response.Response(
                {"error": f"Target {target_type} does not have a phone number (checked guardians for student)"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        success, res_data = termii_send_sms(phone_number, message)
        
        if success:
            return response.Response({
                "message": "SMS sent successfully",
                "details": res_data
            })
        else:
            return response.Response({
                "error": res_data
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BulkMessagingView(views.APIView):
    """
    Send bulk SMS or Email to multiple targets
    """
    permission_classes = [permissions.IsAdminUser]

    def _get_student_phone(self, student):
        primary = student.guardians.filter(is_primary_contact=True).first()
        if primary: return primary.phone_number
        any_g = student.guardians.first()
        if any_g: return any_g.phone_number
        return None

    def post(self, request):
        channel = request.data.get('channel')  # 'sms' or 'email'
        target_group = request.data.get('target_group')  # 'all_students', 'all_staff', 'custom'
        custom_targets = request.data.get('custom_targets', []) # IDs or Emails/Phones
        subject = request.data.get('subject', 'Shining Light School Notification')
        message = request.data.get('message')
        
        if not all([channel, target_group, message]):
            return response.Response(
                {"error": "channel, target_group, and message are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        recipients = []
        
        # Determine recipients based on target_group
        if target_group == 'all_students':
            students = Student.objects.filter(status='enrolled')
            if channel == 'sms':
                for s in students:
                    phone = self._get_student_phone(s)
                    if phone: recipients.append(phone)
            else:
                for s in students:
                    recipients.extend(get_student_recipient_emails(s))
        elif target_group in ['all_staff', 'teaching_staff', 'non_teaching_staff']:
            query = {'user__is_active': True}
            if target_group == 'teaching_staff':
                query['staff_type'] = 'teaching'
            elif target_group == 'non_teaching_staff':
                query['staff_type'] = 'non_teaching'
            
            staff_list = Staff.objects.filter(**query)
            
            if channel == 'sms':
                recipients = [s.phone_number for s in staff_list if s.phone_number]
            else:
                recipients = [s.user.email for s in staff_list if s.user and s.user.email]
        elif target_group == 'specific_class':
            class_id = request.data.get('class_id')
            if not class_id:
                return response.Response({"error": "class_id is required for specific_class target"}, status=status.HTTP_400_BAD_REQUEST)
            students = Student.objects.filter(status='enrolled', class_model_id=class_id)
            if channel == 'sms':
                for s in students:
                    phone = self._get_student_phone(s)
                    if phone: recipients.append(phone)
            else:
                for s in students:
                    recipients.extend(get_student_recipient_emails(s))
        elif target_group == 'custom':
            recipients = custom_targets
        else:
            return response.Response({"error": "Invalid target_group"}, status=status.HTTP_400_BAD_REQUEST)

        if not recipients:
            return response.Response({"error": "No valid recipients found"}, status=status.HTTP_400_BAD_REQUEST)

        # Remove duplicates and empty values
        recipients = list(set([str(r).strip() for r in recipients if r]))

        if channel == 'sms':
            count = 0
            errors = []
            for phone in recipients:
                success, _ = termii_send_sms(phone, message)
                if success:
                    count += 1
                else:
                    errors.append(phone)
            
            return response.Response({
                "message": f"Successfully sent SMS to {count} recipients",
                "failed_count": len(errors),
                "failed_recipients": errors if len(errors) < 20 else "Too many to list"
            })
        
        elif channel == 'email':
            success, res_msg = send_bulk_email(recipients, subject, message)
            if success:
                summary = f"Bulk email sent to {len(recipients)} resolved recipients."
                if target_group == 'all_students':
                     summary = f"Student broadcast sent to {len(recipients)} resolved parent/guardian emails."
                return response.Response({"message": summary})
            else:
                return response.Response({"error": res_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return response.Response({"error": "Invalid channel"}, status=status.HTTP_400_BAD_REQUEST)

class GuardianMessagingView(views.APIView):
    """
    Send messages specifically to guardians and record history.
    """
    permission_classes = [permissions.IsAdminUser]

    def _get_guardian_contacts(self, student, channel):
        """
        Get all valid contacts for a student's guardians.
        Falls back to student user if no guardian exists.
        """
        guardians = student.guardians.all()
        
        if channel == 'sms':
            # For SMS, we usually want one primary recipient recorded
            primary = guardians.filter(is_primary_contact=True).first() or guardians.first()
            if primary:
                return [primary.phone_number], primary
            return [], None
        else:
            # For Email, we can get all guardian emails
            emails = get_student_recipient_emails(student)
            primary = guardians.filter(is_primary_contact=True).first() or guardians.first()
            return emails, primary

    def post(self, request):
        channel = request.data.get('channel')  # 'sms' or 'email'
        student_ids = request.data.get('student_ids', [])
        target_group = request.data.get('target_group')  # 'all_students', 'specific_class', 'custom'
        class_id = request.data.get('class_id')
        subject = request.data.get('subject', 'Shining Light School Notification')
        message = request.data.get('message')

        if not all([channel, message]):
            return response.Response(
                {"error": "channel and message are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        students = Student.objects.none()

        # Determine students based on target params
        if target_group == 'all_students':
            students = Student.objects.filter(status='enrolled')
        elif target_group == 'specific_class':
            if not class_id:
                return response.Response({"error": "class_id is required for specific_class target"}, status=status.HTTP_400_BAD_REQUEST)
            students = Student.objects.filter(status='enrolled', class_model_id=class_id)
        elif target_group == 'custom' or student_ids:
            # If student_ids provided directly or via custom group
            ids = student_ids or request.data.get('custom_targets', []) # In frontend we might send IDs in custom_targets
            # Filter to ensure IDs are valid numbers/strings
            # Handle list of strings or integers
            valid_ids = [str(id) for id in ids if str(id).strip()]
            students = Student.objects.filter(id__in=valid_ids)
        
        if not students.exists():
             return response.Response({"error": "No valid students found"}, status=status.HTTP_400_BAD_REQUEST)

        success_count = 0
        failure_count = 0
        missing_count = 0
        results = []

        connection = None
        if channel == 'email':
            connection = get_connection()
            connection.open()

        try:
            for student in students:
                contacts, primary_guardian = self._get_guardian_contacts(student, channel)
                
                if not contacts:
                    GuardianMessage.objects.create(
                        sender=request.user,
                        student=student,
                        channel=channel,
                        subject=subject,
                        content=message,
                        status='failed',
                        error_message="No contact info found"
                    )
                    failure_count += 1
                    missing_count += 1
                    continue

                success = False
                error_msg = None
                student_name = student.get_full_name()
                
                if channel == 'sms':
                    # ... (rest of logic)
                # Use only the first contact for SMS recorded in GuardianMessage
                contact = contacts[0]
                # Personalize SMS
                personalized_sms = f"Dear Parent of {student_name}: {message}"
                if len(personalized_sms) > 160: # Truncate if too long for single SMS
                     personalized_sms = personalized_sms[:157] + "..."
                
                success, res_data = termii_send_sms(contact, personalized_sms)
                if not success:
                    error_msg = str(res_data)
            else:
                # Use all recipient emails
                # Personalize Email
                personalized_email = f"<h3>Dear Parent/Guardian of {student_name},</h3><br>{message}"
                success, res_msg = send_bulk_email(contacts, subject, personalized_email, connection=connection)
                if not success:
                    error_msg = res_msg

            if success:
                GuardianMessage.objects.create(
                    sender=request.user,
                    student=student,
                    recipient_guardian=primary_guardian,
                    channel=channel,
                    subject=subject,
                    content=message,
                    status='sent',
                    sent_at=timezone.now()
                )
                success_count += 1
                if len(results) < 100:
                    results.append({"student": student.id, "status": "sent"})
            else:
                GuardianMessage.objects.create(
                    sender=request.user,
                    student=student,
                    recipient_guardian=primary_guardian,
                    channel=channel,
                    subject=subject,
                    content=message,
                    status='failed',
                    error_message=error_msg
                )
                failure_count += 1
                if len(results) < 100:
                    results.append({"student": student.id, "status": "failed", "reason": error_msg})

        finally:
            if connection:
                connection.close()

        res_msg = f"Processed {students.count()} families. Success: {success_count}, Failure: {failure_count}."
        if missing_count > 0:
            res_msg += f" {missing_count} students skipped due to missing contact info."

        return response.Response({
            "message": res_msg,
            "results": results
        })
