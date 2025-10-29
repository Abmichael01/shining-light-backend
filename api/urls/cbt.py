from django.urls import path
from api.views.cbt import (
    generate_passcode,
    login_with_passcode,
    revoke_passcode,
    get_active_passcode,
    get_passcode_stats,
    get_all_active_passcodes,
    validate_cbt_session,
    refresh_cbt_session,
    logout_cbt_session,
    get_cbt_session_stats,
    get_cbt_exams,
    get_cbt_exam,
    submit_cbt_exam,
    get_practice_subjects,
    create_practice_exam,
    submit_practice_exam
)

urlpatterns = [
    # Generate passcode (admin only)
    path('generate/', generate_passcode, name='generate-passcode'),
    
    # Student login with passcode (public)
    path('login/', login_with_passcode, name='login-with-passcode'),
    
    # Revoke passcode (admin only)
    path('revoke/', revoke_passcode, name='revoke-passcode'),
    
    # Get active passcode for student (admin only)
    path('active/', get_active_passcode, name='get-active-passcode'),
    
    # Get passcode statistics (admin only)
    path('stats/', get_passcode_stats, name='get-passcode-stats'),
    
    # Get all active passcodes (admin only)
    path('active-all/', get_all_active_passcodes, name='get-all-active-passcodes'),
    
    # CBT Session Management
    path('session/validate/', validate_cbt_session, name='validate-cbt-session'),
    path('session/refresh/', refresh_cbt_session, name='refresh-cbt-session'),
    path('session/logout/', logout_cbt_session, name='logout-cbt-session'),
    path('session/stats/', get_cbt_session_stats, name='get-cbt-session-stats'),
    
    # CBT Exam Management
    path('exams/', get_cbt_exams, name='get-cbt-exams'),
    path('exams/<str:exam_id>/', get_cbt_exam, name='get-cbt-exam'),
    path('exams/<str:exam_id>/submit/', submit_cbt_exam, name='submit-cbt-exam'),
    
    # Practice CBT
    path('practice/subjects/', get_practice_subjects, name='get-practice-subjects'),
    path('practice/create/', create_practice_exam, name='create-practice-exam'),
    path('practice/submit/', submit_practice_exam, name='submit-practice-exam'),
]
