
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models import Student
from api.serializers.student import StudentSerializer
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()
request = factory.get('/')

# This is the string ID that fetch_student uses for search
target_id = "STU-XE6YNC" 
print(f"Testing search for ID: {target_id}")

try:
    # Manual query to verify filter
    from django.db.models import Q
    students = Student.objects.filter(status='enrolled')
    students = students.filter(
        Q(id__icontains=target_id) |
        Q(biodata__first_name__icontains=target_id) |
        Q(biodata__surname__icontains=target_id) |
        Q(admission_number__icontains=target_id)
    )
    
    if students.exists():
        print(f"✅ Student found in DB: {students[0].get_full_name()}")
    else:
        print("❌ Student NOT found in DB search.")
except Exception as e:
    print(f"Error: {e}")

