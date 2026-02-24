from dj_rest_auth.views import LoginView as DjRestAuthLoginView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from api.serializers import UserSerializer
from api.models import User
from api.models.academic import SystemSetting


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(DjRestAuthLoginView):
    """
    Custom login view that returns user data in response.
    Extends dj-rest-auth LoginView to include user details.
    Also enforces portal-specific login restrictions from SystemSetting.
    """
    authentication_classes = []  # No authentication - prevents session/CSRF checks
    permission_classes = [AllowAny]  # Allow unauthenticated access to login

    def post(self, request, *args, **kwargs):
        """
        Before proceeding with login, check if the portal for this
        user type has been disabled by administrators.
        We check early using the email field before full auth.
        """
        email = request.data.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                system_settings = SystemSetting.load()

                # Admins are never restricted
                if user.user_type != 'admin' and not user.is_superuser:
                    if user.user_type == 'staff' and system_settings.disable_staff_login:
                        raise PermissionDenied(
                            system_settings.staff_maintenance_message or
                            "Staff portal is temporarily unavailable."
                        )
                    if user.user_type == 'student' and system_settings.disable_student_login:
                        raise PermissionDenied(
                            system_settings.student_maintenance_message or
                            "Student portal is temporarily unavailable."
                        )
            except User.DoesNotExist:
                pass  # Let the normal login flow handle invalid credentials

        return super().post(request, *args, **kwargs)

    def get_response(self):
        """Override to include user data in response"""
        # Get user data
        user_serializer = UserSerializer(self.user)

        # Return custom response with user data
        data = {
            'detail': 'Login successful',
            'user': user_serializer.data
        }

        response = Response(data, status=200)
        return response


class CheckAdminView(APIView):
    """
    View to check if an email belongs to an admin user.
    Used for maintenance mode login flow.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=400)

        try:
            user = User.objects.get(email=email)
            is_admin = user.user_type == 'admin' or user.is_superuser
            return Response({'is_admin': is_admin})
        except User.DoesNotExist:
            return Response({'is_admin': False})
