"""
Create / reset a test applicant account for end-to-end testing of the
admission flow (biodata + documents + payment).

Idempotent — running it twice resets the same applicant rather than
creating duplicates. Prints credentials at the end.

Usage:
    poetry run python manage.py seed_test_applicant
"""
from datetime import date

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import BioData, Class, Document, School, Student, User


EMAIL = 'applicant.test@shinninglight.local'
PASSWORD = 'applicant123'


class Command(BaseCommand):
    help = 'Create or reset a test applicant with biodata and two uploaded documents.'

    @transaction.atomic
    def handle(self, *args, **options):
        school = School.objects.first()
        if not school:
            self.stderr.write(self.style.ERROR('No School found. Seed schools first.'))
            return

        class_obj = Class.objects.filter(class_code='JSS1').first() or Class.objects.first()
        if not class_obj:
            self.stderr.write(self.style.ERROR('No Class found. Seed classes first.'))
            return

        user, created = User.objects.get_or_create(
            email=EMAIL,
            defaults={'user_type': 'applicant', 'is_active': True},
        )
        user.set_password(PASSWORD)
        user.user_type = 'applicant'
        user.is_active = True
        user.save()

        student, _ = Student.objects.get_or_create(
            user=user,
            defaults={
                'id': 'STU-TESTAPP',
                'school': school,
                'class_model': class_obj,
                'status': 'applicant',
                'source': 'online_application',
                'wants_mock_exam': False,
            },
        )
        # Re-assert key fields if the row already existed
        student.school = school
        student.class_model = class_obj
        student.status = 'applicant'
        student.wants_mock_exam = False
        student.save()

        BioData.objects.update_or_create(
            student=student,
            defaults={
                'surname': 'Test',
                'first_name': 'Applicant',
                'other_names': 'Demo',
                'gender': 'male',
                'date_of_birth': date(2010, 6, 15),
                'nationality': 'Nigerian',
                'state_of_origin': 'Lagos',
                'permanent_address': '12 Test Street, Lagos',
            },
        )

        # Make sure at least two docs exist so the Replace button is testable
        for doc_type, body in [
            ('birth_certificate', b'Dummy birth certificate PDF content'),
            ('passport', b'Dummy passport photo content'),
        ]:
            existing = Document.objects.filter(student=student, document_type=doc_type).first()
            if existing:
                continue
            doc = Document(student=student, document_type=doc_type)
            doc.document_file.save(f'{doc_type}_test.pdf', ContentFile(body), save=True)

        self.stdout.write(self.style.SUCCESS('\nTest applicant ready.\n'))
        self.stdout.write(f'  Email:           {EMAIL}')
        self.stdout.write(f'  Password:        {PASSWORD}')
        self.stdout.write(f'  Application No:  {student.application_number}')
        self.stdout.write(f'  Status:          {student.status}')
        self.stdout.write(f'  Documents:       {student.documents.count()} uploaded\n')
