from django.core.management.base import BaseCommand
from api.models import StudentExam, Student, Exam

class Command(BaseCommand):
    help = 'Debug StudentExam records'

    def handle(self, *args, **options):
        self.stdout.write("=== StudentExam Records ===")
        
        # Get all StudentExam records
        student_exams = StudentExam.objects.all().select_related('student', 'exam')
        
        if not student_exams.exists():
            self.stdout.write("No StudentExam records found.")
            return
        
        for se in student_exams:
            self.stdout.write(f"Student: {se.student.admission_number} | Exam: {se.exam.id} | Status: {se.status} | Score: {se.score}")
        
        self.stdout.write(f"\nTotal StudentExam records: {student_exams.count()}")
        
        # Check for specific student if provided
        if len(args) > 0:
            admission_number = args[0]
            try:
                student = Student.objects.get(admission_number=admission_number)
                student_exams = StudentExam.objects.filter(student=student)
                self.stdout.write(f"\n=== Exams taken by {admission_number} ===")
                for se in student_exams:
                    self.stdout.write(f"Exam: {se.exam.id} | Status: {se.status} | Score: {se.score}")
            except Student.DoesNotExist:
                self.stdout.write(f"Student with admission number {admission_number} not found.")

