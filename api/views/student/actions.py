from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from api.models import Student
from api.serializers import (
    StudentSerializer,
    StudentRegistrationSerializer,
)

# Extenting StudentViewSet with actions via inheritance or mixins is possible, 
# but for simplicity in this refactor, we can just define the methods and 
# then include them in the final ViewSet or use a Mixin.
# I'll use a Mixin approach.

class StudentActionsMixin:
    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new student (admin creates student directly)
        This creates Student, BioData, Guardians in one transaction
        """
        serializer = StudentRegistrationSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        
        response_serializer = StudentSerializer(student)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve an application and convert to enrolled student
        Creates user account and updates status
        """
        student = self.get_object()
        
        if student.status not in ['applicant', 'under_review']:
            return Response(
                {'detail': 'Only applicants can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                from api.models import User
                from datetime import date
                
                if not student.user:
                    biodata = student.biodata
                    username = f"{biodata.first_name.lower()}.{biodata.surname.lower()}@school.com"
                    
                    user = User.objects.create_user(
                        email=username,
                        password=request.data.get('password', 'temp123'),
                        user_type='student'
                    )
                    student.user = user
                
                student.status = 'enrolled'
                student.acceptance_date = date.today()
                student.enrollment_date = date.today()
                student.reviewed_by = request.user
                student.review_date = date.today()
                student.save()
                
                return Response({
                    'detail': 'Application approved successfully',
                    'student': StudentSerializer(student).data
                })
                
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an application"""
        student = self.get_object()
        
        if student.status not in ['applicant', 'under_review']:
            return Response(
                {'detail': 'Only applicants can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_reason = request.data.get('rejection_reason', '')
        
        from datetime import date
        student.status = 'rejected'
        student.rejection_reason = rejection_reason
        student.reviewed_by = request.user
        student.review_date = date.today()
        student.save()
        
        return Response({'detail': 'Application rejected'})
    
    @action(detail=True, methods=['post'])
    def send_credentials(self, request, pk=None):
        """
        Send student login credentials via email
        Generates a new password and sends it to the student's email
        """
        student = self.get_object()
        
        if not student.user:
            return Response(
                {'detail': 'Student does not have a user account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from api.utils.email import generate_password, send_student_registration_email
            
            new_password = generate_password()
            student.user.set_password(new_password)
            student.user.save()
            
            email_sent = send_student_registration_email(student, new_password, request)
            
            if email_sent:
                return Response({
                    'detail': 'Credentials sent successfully',
                    'email': student.user.email
                })
            else:
                return Response(
                    {'detail': 'Failed to send email, but password was updated'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response(
                {'detail': f'Error sending credentials: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
