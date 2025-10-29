from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models.academic import Class, Subject, SessionTerm, Exam, Question, Topic
from api.models.user import User


class Command(BaseCommand):
    help = 'Create active exams for all classes with questions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--questions-per-exam',
            type=int,
            default=10,
            help='Number of questions per exam (default: 10)'
        )
        parser.add_argument(
            '--duration',
            type=int,
            default=60,
            help='Exam duration in minutes (default: 60)'
        )
        parser.add_argument(
            '--total-marks',
            type=int,
            default=100,
            help='Total marks per exam (default: 100)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting exam creation for all classes...'))

        # Get or create admin user
        user, _ = User.objects.get_or_create(
            email='admin@shininglightschools.com',
            defaults={'is_staff': True, 'is_superuser': True}
        )

        # Get current session term
        current_session_term = SessionTerm.objects.filter(
            session__is_current=True,
            is_current=True
        ).first()

        if not current_session_term:
            self.stdout.write(self.style.ERROR('No current session term found. Please run seed_data first.'))
            return

        # Get all classes
        classes = Class.objects.all().order_by('order')
        if not classes.exists():
            self.stdout.write(self.style.ERROR('No classes found. Please run seed_data first.'))
            return

        questions_per_exam = options['questions_per_exam']
        duration = options['duration']
        total_marks = options['total_marks']
        pass_mark = int(total_marks * 0.4)  # 40% pass mark

        exams_created = 0
        questions_created = 0

        for class_obj in classes:
            self.stdout.write(f'\nProcessing {class_obj.name}...')
            
            # Get subjects for this class
            subjects = Subject.objects.filter(class_model=class_obj)
            
            if not subjects.exists():
                self.stdout.write(self.style.WARNING(f'  No subjects found for {class_obj.name}'))
                continue

            for subject in subjects:
                # Check if exam already exists for this subject
                existing_exam = Exam.objects.filter(
                    subject=subject,
                    session_term=current_session_term,
                    status='active'
                ).first()

                if existing_exam:
                    self.stdout.write(self.style.WARNING(f'  Exam already exists for {subject.name}'))
                    continue

                # Get questions for this subject
                available_questions = Question.objects.filter(
                    subject=subject,
                    is_verified=True
                )

                if available_questions.count() < questions_per_exam:
                    # Create additional questions if needed
                    questions_created += self._create_questions_for_subject(
                        subject, questions_per_exam, user
                    )

                # Select questions for the exam
                selected_questions = list(available_questions[:questions_per_exam])
                
                if len(selected_questions) < questions_per_exam:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Only {len(selected_questions)} questions available for {subject.name}, '
                            f'requested {questions_per_exam}'
                        )
                    )

                # Create exam
                exam = Exam.objects.create(
                    title=f"{subject.name} Test - {class_obj.name}",
                    subject=subject,
                    exam_type='test',
                    session_term=current_session_term,
                    duration_minutes=duration,
                    total_marks=total_marks,
                    pass_mark=pass_mark,
                    total_questions=len(selected_questions),
                    shuffle_questions=True,
                    shuffle_options=True,
                    show_results_immediately=True,
                    allow_review=True,
                    status='active',
                    instructions=f"Answer all questions. You have {duration} minutes to complete this test.",
                    created_by=user
                )

                # Add questions to exam
                exam.questions.set(selected_questions)

                exams_created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Created exam for {subject.name} with {len(selected_questions)} questions'
                    )
                )

        self.stdout.write(self.style.SUCCESS(f'\n✅ Exam creation completed!'))
        self.stdout.write(self.style.SUCCESS(f'  • Exams created: {exams_created}'))
        self.stdout.write(self.style.SUCCESS(f'  • Additional questions created: {questions_created}'))

    def _create_questions_for_subject(self, subject, target_count, user):
        """Create additional questions for a subject if needed"""
        current_count = Question.objects.filter(subject=subject).count()
        needed = target_count - current_count
        
        if needed <= 0:
            return 0

        # Get or create a default topic
        topic, _ = Topic.objects.get_or_create(
            subject=subject,
            name='General',
            defaults={
                'description': f'General questions for {subject.name}',
                'is_active': True
            }
        )

        # Create sample questions based on subject
        questions_data = self._get_sample_questions(subject.name, needed)
        created = 0

        for q_data in questions_data:
            Question.objects.create(
                subject=subject,
                topic_model=topic,
                question_text=q_data['question_text'],
                question_type='multiple_choice',
                difficulty=q_data['difficulty'],
                option_a=q_data['option_a'],
                option_b=q_data['option_b'],
                option_c=q_data['option_c'],
                option_d=q_data['option_d'],
                correct_answer=q_data['correct_answer'],
                explanation=q_data['explanation'],
                marks=q_data['marks'],
                created_by=user,
                is_verified=True
            )
            created += 1

        return created

    def _get_sample_questions(self, subject_name, count):
        """Generate sample questions based on subject name"""
        questions = []
        
        # Base question templates
        base_questions = [
            {
                'question_text': f'What is the main focus of {subject_name}?',
                'option_a': 'Theory only',
                'option_b': 'Practical application',
                'option_c': 'Memorization',
                'option_d': 'All of the above',
                'correct_answer': 'D',
                'explanation': f'{subject_name} involves theory, practical application, and understanding.',
                'difficulty': 'easy',
                'marks': 2
            },
            {
                'question_text': f'Which of the following is most important in {subject_name}?',
                'option_a': 'Speed',
                'option_b': 'Accuracy',
                'option_c': 'Both speed and accuracy',
                'option_d': 'Neither',
                'correct_answer': 'C',
                'explanation': 'Both speed and accuracy are important in academic subjects.',
                'difficulty': 'medium',
                'marks': 2
            },
            {
                'question_text': f'In {subject_name}, what should you do first when solving a problem?',
                'option_a': 'Guess the answer',
                'option_b': 'Read the question carefully',
                'option_c': 'Ask for help',
                'option_d': 'Skip the question',
                'correct_answer': 'B',
                'explanation': 'Always read the question carefully to understand what is being asked.',
                'difficulty': 'easy',
                'marks': 1
            },
            {
                'question_text': f'What is the best way to study {subject_name}?',
                'option_a': 'Cramming the night before',
                'option_b': 'Regular practice and review',
                'option_c': 'Reading only',
                'option_d': 'Avoiding practice',
                'correct_answer': 'B',
                'explanation': 'Regular practice and review is the most effective study method.',
                'difficulty': 'easy',
                'marks': 2
            },
            {
                'question_text': f'Which skill is most developed through {subject_name}?',
                'option_a': 'Physical strength',
                'option_b': 'Critical thinking',
                'option_c': 'Musical ability',
                'option_d': 'Artistic skill',
                'correct_answer': 'B',
                'explanation': 'Academic subjects primarily develop critical thinking skills.',
                'difficulty': 'medium',
                'marks': 2
            }
        ]

        # Generate questions by cycling through base questions
        for i in range(count):
            base_q = base_questions[i % len(base_questions)]
            questions.append(base_q)

        return questions

