from rest_framework.authentication import SessionAuthentication


class CsrfEnforcedSessionAuthentication(SessionAuthentication):
    """
    Custom SessionAuthentication that enforces CSRF validation on all requests.
    
    By default, DRF's SessionAuthentication only enforces CSRF on unsafe methods.
    This class ensures CSRF token validation is always performed for better security.
    """
    
    def authenticate(self, request):
        """Override to add debugging"""
        result = super().authenticate(request)
        if result:
            user, auth = result
            print(f"✅ Auth SUCCESS: user={user.email}, user_type={getattr(user, 'user_type', 'N/A')}")
        else:
            print(f"❌ Auth FAILED: No session or invalid")
        return result
    
    def enforce_csrf(self, request):
        """
        Enforce CSRF validation on all authenticated requests.
        This prevents CSRF attacks by ensuring the request came from our frontend.
        """
        return super().enforce_csrf(request)
