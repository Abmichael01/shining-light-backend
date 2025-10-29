# Authentication package
from rest_framework.authentication import SessionAuthentication, BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from api.services.cbt_session import CBTSessionService


class CsrfEnforcedSessionAuthentication(SessionAuthentication):
    """
    Custom SessionAuthentication that enforces CSRF validation on all requests.
    
    By default, DRF's SessionAuthentication only enforces CSRF on unsafe methods.
    This class ensures CSRF token validation is always performed for better security.
    """
    
    def enforce_csrf(self, request):
        """
        Enforce CSRF validation on all authenticated requests.
        This prevents CSRF attacks by ensuring the request came from our frontend.
        """
        return super().enforce_csrf(request)


class CBTSessionAuthentication(BaseAuthentication):
    """
    Custom authentication for CBT sessions
    """
    
    def authenticate(self, request):
        """
        Authenticate using CBT session token
        """
        # Get session token from header or cookie
        session_token = self._get_session_token(request)
        
        print(f"DEBUG: CBT Auth - Session token: {session_token}")
        
        if not session_token:
            print("DEBUG: CBT Auth - No session token found")
            return None
        
        try:
            # Validate session
            session_data = CBTSessionService.validate_session(session_token)
            print(f"DEBUG: CBT Auth - Session validated successfully for student: {session_data.get('student_admission_number')}")
            
            # Create a custom user object for CBT sessions
            cbt_user = CBTSessionUser(session_data)
            
            return (cbt_user, session_token)
            
        except ValueError as e:
            # Invalid or expired session
            print(f"DEBUG: CBT Auth - Session validation failed: {str(e)}")
            return None
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return 'CBT-Session'
    
    def _get_session_token(self, request):
        """
        Extract session token from request
        """
        # Check Authorization header first
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('CBT-Session '):
            return auth_header.split(' ')[1]
        
        # Check custom header
        session_token = request.META.get('HTTP_X_CBT_SESSION')
        if session_token:
            return session_token
        
        # Check cookie
        return request.COOKIES.get('cbt_session_token')


class CBTSessionUser:
    """
    Custom user object for CBT sessions
    """
    
    def __init__(self, session_data):
        self.session_data = session_data
        self.is_authenticated = True
        self.is_anonymous = False
        self.user_type = 'cbt_student'
        
        # Student information - minimal data for authentication only
        self.id = session_data['student_id']
        self.admission_number = session_data['student_admission_number']
        self.first_name = 'Student'  # Default name
        self.last_name = ''
        self.class_name = None
        
        # Session information
        self.session_token = session_data['session_token']
        self.created_at = session_data['created_at']
        self.expires_at = session_data['expires_at']
        self.last_activity = session_data['last_activity']
    
    def get_full_name(self):
        return f"Student {self.admission_number}"
    
    def get_short_name(self):
        return "Student"
    
    def has_perm(self, perm, obj=None):
        # CBT students have limited permissions
        return False
    
    def has_module_perms(self, app_label):
        # CBT students have no module permissions
        return False
    
    def is_staff(self):
        return False
    
    def is_superuser(self):
        return False
    
    def get_session_data(self):
        """Get full session data"""
        return self.session_data
     
    def refresh_session(self):
        """Refresh the session"""
        return CBTSessionService.refresh_session(self.session_token)
    
    def terminate_session(self):
        """Terminate the session"""
        return CBTSessionService.terminate_session(self.session_token)