from dj_rest_auth.views import LoginView as DjRestAuthLoginView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from api.serializers import UserSerializer


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(DjRestAuthLoginView):
    """
    Custom login view that returns user data in response
    Extends dj-rest-auth LoginView to include user details
    CSRF exempt to allow anyone to attempt login
    """
    authentication_classes = []  # No authentication - prevents session/CSRF checks
    permission_classes = [AllowAny]  # Allow unauthenticated access to login
    
    def get_response(self):
        """Override to include user data in response"""
        serializer_class = self.get_response_serializer()
        
        # Get user data
        user_serializer = UserSerializer(self.user)
        
        # Return custom response with user data
        data = {
            'detail': 'Login successful',
            'user': user_serializer.data
        }
        
        response = Response(data, status=200)
        return response
