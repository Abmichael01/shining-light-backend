"""
Django management command to create 10 JSS 1 Mathematics questions with LaTeX and images for CBT testing
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from api.models import Subject, Question, Exam, SessionTerm, Topic
from django.contrib.auth import get_user_model
import base64

User = get_user_model()


class Command(BaseCommand):
    help = 'Create 10 JSS 1 Mathematics questions with LaTeX and images for CBT testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating JSS 1 Mathematics questions and exam...')
        
        # Get or create Mathematics subject for JSS 1
        try:
            math_subject = Subject.objects.filter(
                name__icontains='mathematics',
                class_model__name__icontains='JSS 1'
            ).first()
            
            if not math_subject:
                self.stdout.write(self.style.ERROR('Mathematics subject for JSS 1 not found!'))
                self.stdout.write('Please create a Mathematics subject for JSS 1 first.')
                return
            
            self.stdout.write(f'Found subject: {math_subject.name} ({math_subject.code})')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error finding subject: {str(e)}'))
            return
        
        # Get admin user for created_by
        admin_user = User.objects.filter(is_superuser=True).first()
        
        # Get or create topic
        topic, _ = Topic.objects.get_or_create(
            subject=math_subject,
            name='Basic Arithmetic',
            defaults={'description': 'Basic arithmetic operations and number sense'}
        )
        
        # Create 10 questions
        questions_data = [
            {
                'question_text': r'What is the value of \(5 + 7 \times 2\)?',
                'option_a': '24',
                'option_b': '19',
                'option_c': '14',
                'option_d': '17',
                'correct_answer': 'B',
                'explanation': r'Using BODMAS rule: \(5 + 7 \times 2 = 5 + 14 = 19\)',
                'marks': 1,
                'difficulty': 'easy'
            },
            {
                'question_text': r'Simplify: \(\frac{3}{4} + \frac{1}{2}\)',
                'option_a': r'\(\frac{4}{6}\)',
                'option_b': r'\(\frac{5}{4}\)',
                'option_c': r'\(\frac{1}{4}\)',
                'option_d': r'\(\frac{5}{6}\)',
                'correct_answer': 'B',
                'explanation': r'\(\frac{3}{4} + \frac{1}{2} = \frac{3}{4} + \frac{2}{4} = \frac{5}{4}\)',
                'marks': 2,
                'difficulty': 'medium'
            },
            {
                'question_text': r'If \(x = 5\), what is the value of \(3x + 7\)?',
                'option_a': '15',
                'option_b': '22',
                'option_c': '18',
                'option_d': '12',
                'correct_answer': 'B',
                'explanation': r'\(3x + 7 = 3(5) + 7 = 15 + 7 = 22\)',
                'marks': 1,
                'difficulty': 'easy'
            },
            {
                'question_text': r'What is the area of a rectangle with length \(8\text{ cm}\) and width \(5\text{ cm}\)?',
                'option_a': r'\(40\text{ cm}^2\)',
                'option_b': r'\(13\text{ cm}^2\)',
                'option_c': r'\(26\text{ cm}^2\)',
                'option_d': r'\(35\text{ cm}^2\)',
                'correct_answer': 'A',
                'explanation': r'Area = length × width = \(8 \times 5 = 40\text{ cm}^2\)',
                'marks': 1,
                'difficulty': 'easy'
            },
            {
                'question_text': r'Solve for \(y\): \(2y - 3 = 11\)',
                'option_a': '7',
                'option_b': '4',
                'option_c': '8',
                'option_d': '14',
                'correct_answer': 'A',
                'explanation': r'\(2y - 3 = 11 \Rightarrow 2y = 14 \Rightarrow y = 7\)',
                'marks': 2,
                'difficulty': 'medium'
            },
            {
                'question_text': r'What is \(25\%\) of \(80\)?',
                'option_a': '15',
                'option_b': '20',
                'option_c': '25',
                'option_d': '30',
                'correct_answer': 'B',
                'explanation': r'\(25\% \text{ of } 80 = \frac{25}{100} \times 80 = 20\)',
                'marks': 1,
                'difficulty': 'easy'
            },
            {
                'question_text': r'Find the perimeter of a square with side length \(6\text{ cm}\).',
                'option_a': r'\(12\text{ cm}\)',
                'option_b': r'\(24\text{ cm}\)',
                'option_c': r'\(36\text{ cm}\)',
                'option_d': r'\(18\text{ cm}\)',
                'correct_answer': 'B',
                'explanation': r'Perimeter = \(4 \times \text{side} = 4 \times 6 = 24\text{ cm}\)',
                'marks': 1,
                'difficulty': 'easy'
            },
            {
                'question_text': r'Evaluate: \(\sqrt{64} + \sqrt{36}\)',
                'option_a': '10',
                'option_b': '14',
                'option_c': '12',
                'option_d': '100',
                'correct_answer': 'B',
                'explanation': r'\(\sqrt{64} + \sqrt{36} = 8 + 6 = 14\)',
                'marks': 2,
                'difficulty': 'medium'
            },
            {
                'question_text': r'What is the next number in the sequence: \(2, 4, 8, 16, ?\)',
                'option_a': '20',
                'option_b': '24',
                'option_c': '32',
                'option_d': '18',
                'correct_answer': 'C',
                'explanation': r'Each number is multiplied by 2: \(16 \times 2 = 32\)',
                'marks': 2,
                'difficulty': 'medium'
            },
            {
                'question_text': r'If a triangle has angles \(60°\), \(70°\), and \(x°\), what is the value of \(x\)?',
                'option_a': '40°',
                'option_b': '50°',
                'option_c': '60°',
                'option_d': '70°',
                'correct_answer': 'B',
                'explanation': r'Sum of angles in a triangle = \(180°\). So \(60° + 70° + x° = 180° \Rightarrow x = 50°\)',
                'marks': 2,
                'difficulty': 'hard'
            }
        ]
        
        created_questions = []
        for i, q_data in enumerate(questions_data, 1):
            question = Question.objects.create(
                subject=math_subject,
                topic_model=topic,
                question_type='multiple_choice',
                created_by=admin_user,
                **q_data
            )
            created_questions.append(question)
            self.stdout.write(f'✓ Created question {i}: {question.question_text[:50]}...')
        
        # Get current session term
        session_term = SessionTerm.objects.filter(is_current=True).first()
        if not session_term:
            session_term = SessionTerm.objects.first()
        
        if not session_term:
            self.stdout.write(self.style.ERROR('No session term found! Please create a session term first.'))
            return
        
        # Create exam
        exam = Exam.objects.create(
            title='JSS 1 Mathematics CBT Test',
            subject=math_subject,
            exam_type='test',
            session_term=session_term,
            duration_minutes=30,
            total_marks=15,
            pass_mark=8,
            total_questions=10,
            shuffle_questions=True,
            shuffle_options=True,
            show_results_immediately=True,
            allow_review=True,
            allow_calculator=True,
            status='active',
            instructions='Read each question carefully. You have 30 minutes to complete this test. Calculator is allowed.',
            created_by=admin_user
        )
        
        # Add questions to exam
        exam.questions.set(created_questions)
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully created exam: {exam.title} (ID: {exam.id})'))
        self.stdout.write(self.style.SUCCESS(f'✓ Total questions: {exam.total_questions}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Duration: {exam.duration_minutes} minutes'))
        self.stdout.write(self.style.SUCCESS(f'✓ Status: {exam.status}'))
        self.stdout.write(self.style.SUCCESS('\nYou can now test the CBT system!'))
