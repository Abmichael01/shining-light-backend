
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

admission_no = "2016080901"
try:
    student = Student.objects.get(admission_number=admission_no)
    serializer = StudentSerializer(student, context={'request': request})
    data = serializer.data
    
    print("Biometric Data in JSON:")
    if 'biometric' in data and data['biometric']:
        bio_data = data['biometric']
        print(json.dumps(bio_data, indent=2))
        
        # Explicit check for keys
        keys = ['left_thumb', 'left_index', 'right_thumb', 'right_index']
        for k in keys:
            print(f"  {k}: {bio_data.get(k, 'MISSING')}")
    else:
        print("No biometric data in student JSON.")
except Exception as e:
    print(f"Error: {e}")

