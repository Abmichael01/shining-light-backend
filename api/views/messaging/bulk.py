from rest_framework import views, response, status, permissions
from django.shortcuts import get_object_or_404
from api.models import Student, Staff
from api.utils.sms import send_sms, send_bulk_sms
from api.utils.email import send_bulk_email, get_student_recipient_emails

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
            
        success, res_data = send_sms(phone_number, message)
        
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
            success, res_data = send_bulk_sms(recipients, message)
            
            if success:
                # EbulkSMS returns total sent count in response occasionally, but we'll assume length of recipients if successful
                return response.Response({
                    "message": f"Successfully queued SMS to {len(recipients)} recipients via EbulkSMS",
                    "details": res_data
                })
            else:
                return response.Response({
                    "error": "Failed to send bulk SMS via EbulkSMS",
                    "details": res_data
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
