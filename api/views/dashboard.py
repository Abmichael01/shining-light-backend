"""
Dashboard statistics views
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.permissions import IsSchoolAdmin


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def admin_dashboard_stats(request):
    """
    Get dashboard statistics for admin overview
    Returns counts for applications, students, schools, etc.
    """
    
    # TODO: Replace with actual database queries
    # For now, return zeros as requested
    stats = {
        'total_applications': 0,
        'pending_applications': 0,
        'accepted_students': 0,
        'rejected_applications': 0,
        'total_students': 0,
        'active_schools': 0,
    }
    
    return Response(stats)

