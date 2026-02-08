
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models import Student, Biometric

admission_no = "2016080901"
try:
    student = Student.objects.get(admission_number=admission_no)
    print(f"Student: {student.get_full_name()} (ID: {student.id})")
    
    try:
        bio = Biometric.objects.get(student=student)
        print(f"Biometric Record Found (ID: {bio.id})")
        print(f"  Right Thumb: {bio.right_thumb.url if bio.right_thumb else 'None'}")
        print(f"  Right Index: {bio.right_index.url if bio.right_index else 'None'}")
        print(f"  Left Thumb: {bio.left_thumb.url if bio.left_thumb else 'None'}")
        print(f"  Left Index: {bio.left_index.url if bio.left_index else 'None'}")
        
        print("\nTemplates:")
        print(f"  Right Thumb Tmpl: {'Present' if bio.right_thumb_template else 'None'}")
        print(f"  Right Index Tmpl: {'Present' if bio.right_index_template else 'None'}")
        print(f"  Left Thumb Tmpl: {'Present' if bio.left_thumb_template else 'None'}")
        print(f"  Left Index Tmpl: {'Present' if bio.left_index_template else 'None'}")
    except Biometric.DoesNotExist:
        print("No Biometric record found for this student.")
except Student.DoesNotExist:
    print(f"Student with admission number {admission_no} not found.")

