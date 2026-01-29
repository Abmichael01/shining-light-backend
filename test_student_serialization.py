import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models import Student, Staff
from api.serializers.student import StudentListSerializer
from rest_framework.test import APIRequestFactory

# Get a student that is a staff child
staff_with_children = Staff.objects.filter(children__isnull=False).first()

if not staff_with_children:
    print("No staff with children found!")
    exit(0)

student = staff_with_children.children.first()
print(f"Testing serialization of student: {student.get_full_name()}")
print(f"Student is child of: {staff_with_children.get_full_name()}")

# Try to serialize the student
factory = APIRequestFactory()
request = factory.get('/api/students/')

try:
    serializer = StudentListSerializer(student, context={'request': request})
    data = serializer.data
    print("✅ Serialization successful!")
    print(f"Student data keys: {list(data.keys())}")
except Exception as e:
    print(f"❌ Serialization failed!")
    print(f"Error: {e}")
    traceback.print_exc()
