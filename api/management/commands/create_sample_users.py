from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models.student import Student, StudentSubject
from api.models.academic import Class, Subject, Session, SessionTerm

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample students'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample students...')
        
        classes = Class.objects.all()
        if not classes.exists():
            self.stdout.write(self.style.ERROR('No classes found. Please run seed_data first.'))
            return
            
        session = Session.objects.filter(is_current=True).first()
        term = SessionTerm.objects.filter(is_current=True).first()
        
        if not session or not term:
            self.stdout.write(self.style.ERROR('No active session/term found.'))
            return
            
        from api.models.student import BioData
        from datetime import date
        
        for idx, cls in enumerate(classes):
            user, created = User.objects.get_or_create(
                email=f'student{idx+1}@test.com',
                defaults={
                    'user_type': 'student',
                    'is_active': True
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                
                # Create student profile
                student = Student.objects.create(
                    user=user,
                    school=cls.school,
                    status='applicant',
                    source='admin_registration',
                    class_model=cls,
                )
                
                # Create BioData to generate admission number
                BioData.objects.create(
                    student=student,
                    surname='Test',
                    first_name=f'Student{idx+1}',
                    gender='male',
                    date_of_birth=date(2010, 1, 1),
                    state_of_origin='Lagos',
                    permanent_address='123 Test Street'
                )
                
                # Now set to enrolled and save to trigger admission number generation
                student.status = 'enrolled'
                student.save()
                
                # Assign to all subjects for this class
                subjects = Subject.objects.filter(class_model=cls)
                for subject in subjects:
                    StudentSubject.objects.create(
                        student=student,
                        subject=subject,
                        session=session,
                        session_term=term,
                        is_active=True
                    )
                    
                self.stdout.write(self.style.SUCCESS(f'Created student: {user.email} in {cls.name} with {subjects.count()} subjects'))
                
        self.stdout.write(self.style.SUCCESS('Done! Password for all students is "password123"'))
