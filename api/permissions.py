from rest_framework import permissions

class IsSchoolAdmin(permissions.BasePermission):
    """
    Permission check for Admin users only.
    Allows only authenticated users with user_type='admin'.
    """
    
    def has_permission(self, request, view):
        user = request.user
        if not hasattr(request, 'user') or not request.user.is_authenticated:
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
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False
        
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for admin
        return getattr(request.user, 'user_type', None) == 'admin'


class IsAdminOrStaff(permissions.BasePermission):
    """
    Permission check for Admin or Staff users.
    Allows authenticated users with user_type='admin' or 'staff'.
    """
    
    def has_permission(self, request, view):
        user = request.user
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False
        
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True
        
        return getattr(user, 'user_type', None) in ['admin', 'staff', 'principal']


class IsAdminOrStaffOrStudent(permissions.BasePermission):
    """
    Permission check for Admin, Staff, or Student users.
    - Admin/Staff: Full access
    - Students: Read-only access to their own data only
    """
    
    def has_permission(self, request, view):
        user = request.user
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False
        
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True
        
        user_type = getattr(user, 'user_type', None)
        
        # Admin and staff have full access
        if user_type in ['admin', 'staff', 'principal']:
            return True
        
        # Students have read-only access (GET, HEAD, OPTIONS)
        if user_type == 'student':
            return request.method in permissions.SAFE_METHODS
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """
        Students can only access their own student subjects
        """
        user = request.user
        user_type = getattr(user, 'user_type', None)
        
        # Admin and staff have full access
        if user_type in ['admin', 'staff', 'principal']:
            return True
        
        # Students can only access their own data, or public data
        if user_type == 'student':
            # If the object has a student field, ensure it matches the current user
            if hasattr(obj, 'student') and hasattr(obj.student, 'user'):
                return obj.student.user == user
            
            # For other objects (like Assignments), we rely on has_permission ( SAFE_METHODS ) 
            # and get_queryset for filtering
            return request.method in permissions.SAFE_METHODS


class IsApplicant(permissions.BasePermission):
    """
    Permission check for applicant users.
    Allows authenticated users with user_type='applicant'.
    """
    
    def has_permission(self, request, view):
        user = request.user
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            print(f"❌ IsApplicant: User not authenticated")
            return False
        
        user_type = getattr(user, 'user_type', None)
        print(f"🔍 IsApplicant check: user={user.email}, user_type={user_type}")
        
        return user_type == 'applicant'
