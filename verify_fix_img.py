
import os
import django
import sys

print("Starting verification script...")

# Setup Django environment FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
try:
    django.setup()
    print("Django setup successful.")
except Exception as e:
    print(f"Django setup failed: {e}")
    sys.exit(1)

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from api.models import Student
from api.serializers.student import CBTStudentProfileSerializer
from api.views.dashboard import student_dashboard_stats

def verify_cbt_profile():
    print("\n--- Verifying CBT Student Profile Serializer ---")
    student = Student.objects.filter(biodata__passport_photo__isnull=False).exclude(biodata__passport_photo='').first()
    if not student:
        print("No student with passport photo found for testing.")
        return

    print(f"Found student: {student.admission_number}")
    print(f"Bio passport_photo field: {student.biodata.passport_photo}")
    print(f"Bio passport_photo URL: {student.biodata.passport_photo.url}")

    factory = APIRequestFactory()
    request = factory.get('/')
    request = Request(request) # Wrap in DRF Request

    serializer = CBTStudentProfileSerializer(student, context={'request': request})
    data = serializer.data
    photo_url = data.get('passport_photo')
    
    print(f"Serializer Output Passport Photo URL: {photo_url}")
    if photo_url and photo_url.startswith('http'):
        print("✅ CBT Profile: Absolute URL generated correctly.")
    else:
        print("❌ CBT Profile: Absolute URL NOT generated.")

def verify_dashboard_stats():
    print("\n--- Verifying Student Dashboard Stats View ---")
    student = Student.objects.filter(user__isnull=False, biodata__passport_photo__isnull=False).exclude(biodata__passport_photo='').first()
    if not student:
        print("No student with user and passport photo found for testing.")
        return

    print(f"Found student: {student.admission_number} with user: {student.user.email}")

    factory = APIRequestFactory()
    request = factory.get('/api/student-dashboard/stats/')
    request.user = student.user
    
    # We call the view function directly
    response = student_dashboard_stats(request)
    data = response.data
    photo_url = data.get('passport_photo')
    
    print(f"View Response Passport Photo URL: {photo_url}")
    if photo_url and photo_url.startswith('http'):
        print("✅ Dashboard Stats: Absolute URL included correctly.")
    else:
        print("❌ Dashboard Stats: Absolute URL NOT included.")

if __name__ == "__main__":
    try:
        if Student.objects.filter(admission_number='TEST-001').exists():
            print("Test student TEST-001 exists.")
        else:
            print("Test student TEST-001 MISSING.")
            
        verify_cbt_profile()
        verify_dashboard_stats()
    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()
