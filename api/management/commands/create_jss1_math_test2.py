"""
Django management command to create another set of 10 JSS 1 Mathematics questions for CBT testing
"""
from django.core.management.base import BaseCommand
from api.models import Subject, Question, Exam, SessionTerm, Topic
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create another set of 10 JSS 1 Mathematics questions for CBT testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating JSS 1 Mathematics Test 2 questions and exam...')
        
        # Get Mathematics subject for JSS 1
        try:
            math_subject = Subject.objects.filter(
                name__icontains='mathematics',
                class_model__name__icontains='JSS 1'
            ).first()
            
            if not math_subject:
                self.stdout.write(self.style.ERROR('Mathematics subject for JSS 1 not found!'))
                return
            
            self.stdout.write(f'Found subject: {math_subject.name} ({math_subject.code})')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error finding subject: {str(e)}'))
            return
        
        # Get admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        
        # Get or create topic
        topic, _ = Topic.objects.get_or_create(
            subject=math_subject,
            name='Numbers and Numeration',
            defaults={'description': 'Working with numbers, place values, and basic operations'}
        )
        
        # Create 10 new questions
        questions_data = [
            {
                'question_text': r'What is \(12 \times 8\)?',
                'option_a': '84',
                'option_b': '96',
                'option_c': '104',
                'option_d': '88',
                'correct_answer': 'B',
                'explanation': r'\(12 \times 8 = 96\)',
                'marks': 1,
                'difficulty': 'easy'
            },
            {
                'question_text': r'Express \(\frac{3}{5}\) as a decimal.',
                'option_a': '0.3',
                'option_b': '0.5',
                'option_c': '0.6',
                'option_d': '0.35',
                'correct_answer': 'C',
                'explanation': r'\(\frac{3}{5} = 3 \div 5 = 0.6\)',
                'marks': 2,
                'difficulty': 'medium'
            },
            {
                'question_text': r'What is the value of \(15 - 3 \times 4\)?',
                'option_a': '48',
                'option_b': '3',
                'option_c': '12',
                'option_d': '27',
                'correct_answer': 'B',
                'explanation': r'Using BODMAS: \(15 - 3 \times 4 = 15 - 12 = 3\)',
                'marks': 1,
                'difficulty': 'medium'
            },
            {
                'question_text': r'Find the LCM of 4 and 6.',
                'option_a': '12',
                'option_b': '24',
                'option_c': '8',
                'option_d': '6',
                'correct_answer': 'A',
                'explanation': r'Multiples of 4: 4, 8, 12, 16... Multiples of 6: 6, 12, 18... LCM = 12',
                'marks': 2,
                'difficulty': 'medium'
            },
            {
                'question_text': r'What is \(20\%\) of \(150\)?',
                'option_a': '20',
                'option_b': '25',
                'option_c': '30',
                'option_d': '35',
                'correct_answer': 'C',
                'explanation': r'\(20\% \text{ of } 150 = \frac{20}{100} \times 150 = 30\)',
                'marks': 1,
                'difficulty': 'easy'
            },
            {
                'question_text': r'Simplify: \(2^3 + 3^2\)',
                'option_a': '13',
                'option_b': '17',
                'option_c': '15',
                'option_d': '19',
                'correct_answer': 'B',
                'explanation': r'\(2^3 + 3^2 = 8 + 9 = 17\)',
                'marks': 2,
                'difficulty': 'medium'
            },
            {
                'question_text': r'What is the HCF of 12 and 18?',
                'option_a': '2',
                'option_b': '3',
                'option_c': '6',
                'option_d': '9',
                'correct_answer': 'C',
                'explanation': r'Factors of 12: 1, 2, 3, 4, 6, 12. Factors of 18: 1, 2, 3, 6, 9, 18. HCF = 6',
                'marks': 2,
                'difficulty': 'medium'
            },
            {
                'question_text': r'Convert \(0.75\) to a fraction in its simplest form.',
                'option_a': r'\(\frac{3}{4}\)',
                'option_b': r'\(\frac{7}{10}\)',
                'option_c': r'\(\frac{75}{100}\)',
                'option_d': r'\(\frac{1}{4}\)',
                'correct_answer': 'A',
                'explanation': r'\(0.75 = \frac{75}{100} = \frac{3}{4}\)',
                'marks': 2,
                'difficulty': 'hard'
            },
            {
                'question_text': r'If \(3x = 15\), what is \(x\)?',
                'option_a': '3',
                'option_b': '4',
                'option_c': '5',
                'option_d': '6',
                'correct_answer': 'C',
                'explanation': r'\(3x = 15 \Rightarrow x = 15 \div 3 = 5\)',
                'marks': 1,
                'difficulty': 'easy'
            },
            {
                'question_text': r'What is the sum of the first 5 odd numbers?',
                'option_a': '15',
                'option_b': '20',
                'option_c': '25',
                'option_d': '30',
                'correct_answer': 'C',
                'explanation': r'First 5 odd numbers: 1, 3, 5, 7, 9. Sum = \(1 + 3 + 5 + 7 + 9 = 25\)',
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
            self.stdout.write(self.style.ERROR('No session term found!'))
            return
        
        # Create exam
        exam = Exam.objects.create(
            title='JSS 1 Mathematics Test 2',
            subject=math_subject,
            exam_type='test',
            session_term=session_term,
            duration_minutes=25,
            total_marks=16,
            pass_mark=9,
            total_questions=10,
            shuffle_questions=True,
            shuffle_options=True,
            show_results_immediately=False,
            allow_review=True,
            allow_calculator=True,
            status='active',
            instructions='Answer all questions carefully. Show your working where necessary. You have 25 minutes.',
            created_by=admin_user
        )
        
        # Add questions to exam
        exam.questions.set(created_questions)
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully created exam: {exam.title} (ID: {exam.id})'))
        self.stdout.write(self.style.SUCCESS(f'✓ Total questions: {exam.total_questions}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Duration: {exam.duration_minutes} minutes'))
        self.stdout.write(self.style.SUCCESS(f'✓ Status: {exam.status}'))
        self.stdout.write(self.style.SUCCESS('\nReady for testing!'))
