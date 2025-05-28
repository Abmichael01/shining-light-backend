# accounts/views.py
from dj_rest_auth.views import LoginView as BaseLoginView, LogoutView as BaseLogoutView
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from django.contrib.auth import logout as django_logout
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer
from django.conf import settings


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "detail": "Registration successful",
                "email": user.email,
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(BaseLoginView):
    def get_response(self):
        response = super().get_response()

        if not self.user:
            return response

        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Get cookie settings from settings.py
        cookie_settings = {
            'httponly': settings.JWT_COOKIE_HTTPONLY,
            'secure': settings.JWT_COOKIE_SECURE,
            'samesite': settings.JWT_COOKIE_SAMESITE,
            'path': settings.JWT_COOKIE_PATH,
        }

        if hasattr(settings, 'JWT_COOKIE_DOMAIN') and settings.JWT_COOKIE_DOMAIN:
            cookie_settings['domain'] = settings.JWT_COOKIE_DOMAIN

        # Set access token cookie
        response.set_cookie(
            key='access_token',
            value=access_token,
            **cookie_settings
        )

        # Set refresh token cookie (longer expiration)
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            **cookie_settings,
        )

        return response
    
class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        # Get refresh token from cookie
        refresh_token = request.COOKIES.get('refresh_token')

        # Optional: Blacklist the refresh token if using token revocation
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass  # Token may already be expired or invalid

        # Prepare response
        response = JsonResponse({"detail": "Successfully logged out."})
        
        # Delete cookies
        response.delete_cookie('access_token', path='/', samesite=settings.JWT_COOKIE_SAMESITE)
        response.delete_cookie('refresh_token', path='/', samesite=settings.JWT_COOKIE_SAMESITE)

        # Django logout (for session-based auth fallback)
        django_logout(request)

        return response
    
class RefreshTokenView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response(
                {"detail": "Refresh token not found"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
        except Exception as e:
            return Response(
                {"detail": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        response = JsonResponse({
            "detail": "Access token refreshed",
            "access_token": new_access_token
        })
        response.set_cookie(
            key='access_token',
            value=new_access_token,
            httponly=True,
            secure=False,  # Set to True in production
            samesite='Lax',
            path='/',
            max_age=3600  # 1 hour
        )
        return response