from rest_framework import permissions


class IsSchoolAdmin(permissions.BasePermission):
    """
    Permission check for Admin users only.
    Allows only authenticated users with user_type='admin'.
    """
    
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if getattr(user, 'is_superuser', False):
            return True

        return getattr(user, 'user_type', None) == 'admin'


class IsSchoolAdminOrReadOnly(permissions.BasePermission):
    """
    Permission check that allows:
    - Admins: Full access (GET, POST, PUT, PATCH, DELETE)
    - Other authenticated users: Read-only access (GET)
    - Unauthenticated users: No access
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for admin
        return request.user.user_type == 'admin'


class IsAdminOrStaff(permissions.BasePermission):
    """
    Permission check for Admin or Staff users.
    Allows authenticated users with user_type='admin' or 'staff'.
    """
    
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True
        
        return getattr(user, 'user_type', None) in ['admin', 'staff']

