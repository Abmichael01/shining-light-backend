from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from api.models import User, Student

class MultiFieldModelBackend(ModelBackend):
    """
    Custom authentication backend that allows authenticating using:
    1. Email (default)
    2. Application Number (for applicants)
    3. Admission Number (for enrolled students)
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None
            
        user = None
        
        # 1. Try Email lookup (standard)
        try:
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            # 2. Try Student Application Number
            try:
                student = Student.objects.get(application_number__iexact=username)
                user = student.user
            except Student.DoesNotExist:
                # 3. Try Student Admission Number
                try:
                    student = Student.objects.get(admission_number__iexact=username)
                    user = student.user
                except Student.DoesNotExist:
                    # 4. Try Student ID (the primary key 'id' like STU-XXX)
                    try:
                        student = Student.objects.get(id__iexact=username)
                        user = student.user
                    except Student.DoesNotExist:
                        return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
