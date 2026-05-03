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
        user = User.objects.filter(email__iexact=username).first()
        
        if not user:
            # 2. Try Student Application Number
            student = Student.objects.filter(application_number__iexact=username).first()
            if student:
                user = student.user
            else:
                # 3. Try Student Admission Number
                student = Student.objects.filter(admission_number__iexact=username).first()
                if student:
                    user = student.user
                else:
                    # 4. Try Student ID (the primary key 'id' like STU-XXX)
                    student = Student.objects.filter(id__iexact=username).first()
                    if student:
                        user = student.user
                    else:
                        return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
