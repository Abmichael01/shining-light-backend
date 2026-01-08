import os
import django
import sys

# Setup Django
sys.path.append('/home/urkelcodes/Desktop/MyProjects/Clients/shinninglight/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models import (
    Student, StudentSubject, Session, SessionTerm, TermReport, 
    Subject, Class, School
)
from decimal import Decimal

def verify_logic():
    print("Starting ranking and cumulative logic verification...")
    
    # Get current session and terms
    session = Session.objects.filter(is_current=True).first()
    if not session:
        print("Error: No current session found.")
        return
        
    # Ensure all terms exist
    term1, _ = SessionTerm.objects.get_or_create(session=session, term_name='1st Term', defaults={'start_date': session.start_date, 'end_date': session.start_date})
    term2, _ = SessionTerm.objects.get_or_create(session=session, term_name='2nd Term', defaults={'start_date': session.start_date, 'end_date': session.start_date})
    term3, _ = SessionTerm.objects.get_or_create(session=session, term_name='3rd Term', defaults={'start_date': session.start_date, 'end_date': session.start_date})
    
    print(f"Terms: {term1.term_name}, {term2.term_name}, {term3.term_name}")


    # Use a sample student
    student = Student.objects.filter(status='enrolled').first()
    if not student:
        print("Error: No enrolled student found for testing.")
        return
    
    # Use a sample subject
    subject = Subject.objects.filter(class_model=student.class_model).first()
    if not subject:
        print("Error: No subject found for student's class.")
        return

    print(f"Testing for Student: {student.id}, Subject: {subject.name}")

    # 1. Test Terminal Scores in Serializer (Simulation via queryset)
    # Create results for terms
    params = {
        'student': student,
        'subject': subject,
        'session': session,
    }
    
    # Cleanup previous test data
    StudentSubject.objects.filter(**params).delete()
    
    # Create 3 terms of results
    reg1 = StudentSubject.objects.create(session_term=term1, ca_score=20, exam_score=45, **params) # Total 65
    reg2 = StudentSubject.objects.create(session_term=term2, ca_score=25, exam_score=50, **params) # Total 75
    reg3 = StudentSubject.objects.create(session_term=term3, ca_score=30, exam_score=55, **params) # Total 85

    # 2. Test calculate_rankings view logic (Calling the logic directly)
    from rest_framework.test import APIRequestFactory
    from api.views.student import StudentSubjectViewSet
    
    factory = APIRequestFactory()
    view = StudentSubjectViewSet.as_view({'post': 'calculate_rankings'})
    
    # Mock user for permission
    from api.models import User
    import django.contrib.auth.models
    admin = User.objects.filter(user_type='admin').first()
    if not admin:
        print("Error: No admin user found for testing.")
        return
        
    django.contrib.auth.models.AnonymousUser = lambda: admin # Simple mock
    
    # Create TermReports (since calculation logic depends on them for previous terms)
    # We'll calculate rankings for each term to trigger TermReport creation
    for t in [term1, term2, term3]:
        print(f"Calculating rankings for {t.term_name}...")
        req = factory.post('/api/student-subjects/calculate_rankings/', {
            'session': session.id,
            'session_term': t.id
        }, format='json')
        req.user = admin
        view(req)

    # 3. Assertions
    # Check Metric caching
    reg3.refresh_from_db()
    print(f"Subject metrics - Max: {reg3.highest_score}, Min: {reg3.lowest_score}, Avg: {reg3.subject_average}")
    
    if reg3.highest_score == Decimal('85.00') and reg3.lowest_score == Decimal('85.00') and reg3.subject_average == Decimal('85.00'):
        print("✅ Subject metrics correctly cached.")
    else:
        print(f"❌ Subject metrics mismatch: Max={reg3.highest_score}, Min={reg3.lowest_score}, Avg={reg3.subject_average}")

    # Check Cumulative Report
    report3 = TermReport.objects.filter(student=student, session=session, session_term=term3).first()
    
    # Expected: (65+75+85)/3 = 75
    if report3 and report3.cumulative_average:
        print(f"Term 3 Cumulative Average: {report3.cumulative_average}")
        if abs(report3.cumulative_average - Decimal('75.00')) < 0.01:
            print("✅ Cumulative average calculation is CORRECT (75.00).")
        else:
            print(f"❌ Cumulative average calculation INCORRECT. Expected 75.00, got {report3.cumulative_average}")
    else:
        print("❌ Cumulative average missing for Term 3.")

    # Check Term 1 (Should be blank)
    report1_check = TermReport.objects.filter(student=student, session=session, session_term=term1).first()
    if report1_check and report1_check.cumulative_average is None:
        print("✅ Cumulative average is correctly NULL for Term 1.")
    else:
        print(f"❌ Cumulative average found for Term 1: {report1_check.cumulative_average if report1_check else 'N/A'}")


    print("\nVerification complete.")

if __name__ == "__main__":
    verify_logic()
