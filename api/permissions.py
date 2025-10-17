from rest_framework import permissions


class IsSchoolAdmin(permissions.BasePermission):
    """
    Permission check for Admin users only.
    Allows only authenticated users with user_type='admin'.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type == 'admin'
        )


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

