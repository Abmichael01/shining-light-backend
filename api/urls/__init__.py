from django.urls import path, include
from api.views import LoginView
from api.views.dashboard import admin_dashboard_stats
from api.views.config import school_configs

app_name = 'api'

urlpatterns = [
    # Custom login view (returns user data)
    path('auth/login/', LoginView.as_view(), name='login'),
    
    # Other dj-rest-auth endpoints (logout, user, password change)
    path('auth/', include('dj_rest_auth.urls')),
    
    # Dashboard
    path('dashboard/stats/', admin_dashboard_stats, name='admin-dashboard-stats'),
    
    # Configs (centralized config data for caching)
    path('configs/', school_configs, name='school-configs'),
    
    # Academic endpoints (schools, sessions, classes, subjects, etc.)
    path('', include('api.urls.academic')),
    
    # Student endpoints (students, biodata, guardians, documents, etc.)
    path('', include('api.urls.student')),
    
    # Staff endpoints (staff, education, salary, loans, etc.)
    path('', include('api.urls.staff')),
    
    # Fee endpoints (fee types, payments, etc.)
    path('', include('api.urls.fee')),
]

