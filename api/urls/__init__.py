from django.urls import path, include
from api.views import LoginView, convert_html_to_pdf, convert_html_to_image, convert_multiple_html_to_pdf, convert_multiple_html_to_images_zip
from api.views.staff import staff_me, staff_students, staff_student_detail_update, staff_wallet, staff_wallet_transactions
from api.views.student import student_me
from api.views.dashboard import admin_dashboard_stats, student_growth_chart, payment_growth_chart, staff_dashboard_stats, staff_recent_assignments, student_dashboard_stats
from api.views.config import school_configs
from api.views.upload import FileUploadView
from api.views.webhook import paystack_webhook

app_name = 'api'

urlpatterns = [
    # Custom login view (returns user data)
    path('auth/login/', LoginView.as_view(), name='login'),
    
    # Other dj-rest-auth endpoints (logout, user, password change)
    path('auth/', include('dj_rest_auth.urls')),
    
    # Dashboard
    path('dashboard/stats/', admin_dashboard_stats, name='admin-dashboard-stats'),
    path('dashboard/student-growth/', student_growth_chart, name='student-growth-chart'),
    path('dashboard/payment-growth/', payment_growth_chart, name='payment-growth-chart'),
    # Staff dashboard
    path('staff-dashboard/stats/', staff_dashboard_stats, name='staff-dashboard-stats'),
    path('staff-dashboard/recent-assignments/', staff_recent_assignments, name='staff-recent-assignments'),
    # Student dashboard
    path('student-dashboard/stats/', student_dashboard_stats, name='student-dashboard-stats'),
    
    # Configs (centralized config data for caching)
    path('configs/', school_configs, name='school-configs'),
    
    # Academic endpoints (schools, sessions, classes, subjects, etc.)
    path('academic/', include('api.urls.academic')),
    
    # Student endpoints (students, biodata, guardians, documents, etc.)
    path('', include('api.urls.student')),
    
    # Staff endpoints (staff, education, salary, loans, etc.)
    path('', include('api.urls.staff')),
    
    # Fee endpoints (fee types, payments, etc.)
    path('', include('api.urls.fee')),
    
    # CBT endpoints (passcodes, exam access, etc.)
    path('cbt/', include('api.urls.cbt')),
    
    # Admission endpoints (applicant portal)
    path('admission/', include('api.urls.admission')),
    
    # Scheduling endpoints (Timetable, Attendance)
    path('scheduling/', include('api.urls.scheduling')),
    
    # Staff portal (self-service)
    path('staff-portal/me/', staff_me, name='staff-me'),
    path('staff-portal/wallet/', staff_wallet, name='staff-wallet'),
    path('staff-portal/transactions/', staff_wallet_transactions, name='staff-wallet-transactions'),
    path('staff-portal/students/', staff_students, name='staff-students'),
    path('staff-portal/students/<str:student_id>/', staff_student_detail_update, name='staff-student-detail'),
    # Student portal (self-service)
    path('student-portal/me/', student_me, name='student-me'),
    # Reports
    path('reports/convert-pdf/', convert_html_to_pdf, name='convert-html-to-pdf'),
    path('reports/convert-image/', convert_html_to_image, name='convert-html-to-image'),
    path('reports/convert-multi-pdf/', convert_multiple_html_to_pdf, name='convert-multiple-html-to-pdf'),
    path('reports/convert-multi-images-zip/', convert_multiple_html_to_images_zip, name='convert-multiple-html-to-images-zip'),
    path('reports/convert-multi-images-zip/', convert_multiple_html_to_images_zip, name='convert-multiple-html-to-images-zip'),

    # General File Upload
    path('common/upload/', FileUploadView.as_view(), name='file-upload'),
    
    # Centralized Payment Webhook
    path('payment/webhook/', paystack_webhook, name='central-paystack-webhook'),
]

