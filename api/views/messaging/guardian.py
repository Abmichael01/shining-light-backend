from rest_framework import views, response, status, permissions
from django.utils import timezone
from api.models import Student, GuardianMessage
from api.utils.sms import send_bulk_sms
from api.utils.email import send_bulk_email, get_student_recipient_emails
from django.core.mail import get_connection

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
            
        sms_recipients = []
        sms_records = []
        bulk_sms_text = f"Dear Parent/Guardian: {message}"
        if len(bulk_sms_text) > 160:
             bulk_sms_text = bulk_sms_text[:157] + "..."

        try:
            for student in students:
                contacts, primary_guardian = self._get_guardian_contacts(student, channel)
                
                if not contacts:
                    if channel == 'email':
                        GuardianMessage.objects.create(
                            sender=request.user,
                            student=student,
                            channel=channel,
                            subject=subject,
                            content=message,
                            status='failed',
                            error_message="No contact info found"
                        )
                    else:
                        sms_records.append(GuardianMessage(
                            sender=request.user,
                            student=student,
                            channel=channel,
                            subject=subject,
                            content=message,
                            status='failed',
                            error_message="No contact info found"
                        ))
                    failure_count += 1
                    missing_count += 1
                    continue

                student_name = student.get_full_name()
                
                if channel == 'sms':
                    contact = contacts[0]
                    sms_recipients.append(contact)
                    sms_records.append(GuardianMessage(
                        sender=request.user,
                        student=student,
                        recipient_guardian=primary_guardian,
                        channel=channel,
                        subject=subject,
                        content=message,
                        status='pending'
                    ))
                else:
                    # Personalize Email
                    personalized_email = f"<h3>Dear Parent/Guardian of {student_name},</h3><br>{message}"
                    success, res_msg = send_bulk_email(contacts, subject, personalized_email, connection=connection)
                    
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
                            error_message=res_msg
                        )
                        failure_count += 1
                        if len(results) < 100:
                            results.append({"student": student.id, "status": "failed", "reason": res_msg})

            # Process bulk SMS after loop
            if channel == 'sms' and sms_recipients:
                success, res_data = send_bulk_sms(sms_recipients, bulk_sms_text)
                now = timezone.now()
                
                for record in sms_records:
                    if record.status == 'pending':
                        if success:
                            record.status = 'sent'
                            record.sent_at = now
                            success_count += 1
                            if len(results) < 100:
                                results.append({"student": record.student_id, "status": "sent"})
                        else:
                            record.status = 'failed'
                            record.error_message = str(res_data)
                            failure_count += 1
                            if len(results) < 100:
                                results.append({"student": record.student_id, "status": "failed", "reason": str(res_data)})
                                
                GuardianMessage.objects.bulk_create(sms_records)
            elif channel == 'sms' and sms_records:
                print("Bulk Failed Insert Records Only:", sms_records)
                GuardianMessage.objects.bulk_create(sms_records)

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
