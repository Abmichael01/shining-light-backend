from dj_rest_auth.views import LoginView as DjRestAuthLoginView
from rest_framework.response import Response
from api.serializers import UserSerializer


class LoginView(DjRestAuthLoginView):
    """
    Custom login view that returns user data in response
    Extends dj-rest-auth LoginView to include user details
    """
    
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

