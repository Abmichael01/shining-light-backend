from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from api.models.academic import School, Session, SessionTerm, Class, Department, SubjectGroup, Subject, Topic, Grade, Question, ExamHall
from api.models.user import User


class Command(BaseCommand):
    help = 'Populate database with schools, classes, subjects, and question bank'

    def _get_or_create_topic(self, subject, topic_name):
        """Helper method to get or create a Topic for a given subject"""
        topic, _ = Topic.objects.get_or_create(
            subject=subject,
            name=topic_name,
            defaults={
                'description': f'{topic_name} topic for {subject.name}',
                'is_active': True
            }
        )
        return topic

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database population...'))

        # Create or get superuser for created_by
        user, _ = User.objects.get_or_create(
            email='admin@shininglightschools.com',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        if _:
            user.set_password('admin123')
            user.save()
            self.stdout.write(self.style.SUCCESS('✓ Created admin user'))

        # 1. Create Schools
        self.stdout.write('Creating schools...')
        schools_data = [
            {'name': 'Nursery Section', 'school_type': 'Nursery'},
            {'name': 'Primary Section', 'school_type': 'Primary'},
            {'name': 'Junior Secondary Section', 'school_type': 'Junior Secondary'},
            {'name': 'Senior Secondary Section', 'school_type': 'Senior Secondary'},
        ]
        
        schools = {}
        for school_data in schools_data:
            school, created = School.objects.get_or_create(
                school_type=school_data['school_type'],
                defaults={'name': school_data['name']}
            )
            schools[school_data['school_type']] = school
            self.stdout.write(self.style.SUCCESS(f'  ✓ {school}'))

        # 2. Create Session
        self.stdout.write('Creating academic session...')
        session, _ = Session.objects.get_or_create(
            name='2024/2025',
            defaults={
                'start_date': date(2024, 9, 1),
                'end_date': date(2025, 7, 31),
                'is_current': True
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {session}'))

        # 3. Create Classes
        self.stdout.write('Creating classes...')
        classes_data = [
            # Nursery
            {'name': 'Nursery 1', 'code': 'NUR1', 'school': 'Nursery', 'order': 1},
            {'name': 'Nursery 2', 'code': 'NUR2', 'school': 'Nursery', 'order': 2},
            # Primary
            {'name': 'Primary 1', 'code': 'PRI1', 'school': 'Primary', 'order': 3},
            {'name': 'Primary 2', 'code': 'PRI2', 'school': 'Primary', 'order': 4},
            {'name': 'Primary 3', 'code': 'PRI3', 'school': 'Primary', 'order': 5},
            {'name': 'Primary 4', 'code': 'PRI4', 'school': 'Primary', 'order': 6},
            {'name': 'Primary 5', 'code': 'PRI5', 'school': 'Primary', 'order': 7},
            {'name': 'Primary 6', 'code': 'PRI6', 'school': 'Primary', 'order': 8},
            # JSS
            {'name': 'JSS 1', 'code': 'JSS1', 'school': 'Junior Secondary', 'order': 9},
            {'name': 'JSS 2', 'code': 'JSS2', 'school': 'Junior Secondary', 'order': 10},
            {'name': 'JSS 3', 'code': 'JSS3', 'school': 'Junior Secondary', 'order': 11},
            # SSS
            {'name': 'SSS 1', 'code': 'SS1', 'school': 'Senior Secondary', 'order': 12},
            {'name': 'SSS 2', 'code': 'SS2', 'school': 'Senior Secondary', 'order': 13},
            {'name': 'SSS 3', 'code': 'SS3', 'school': 'Senior Secondary', 'order': 14},
        ]

        classes = {}
        for class_data in classes_data:
            school_obj = schools[class_data['school']]
            
            # Try to get existing class by school and name
            class_obj = Class.objects.filter(
                school=school_obj,
                name=class_data['name']
            ).first()
            
            if class_obj:
                classes[class_data['code']] = class_obj
                self.stdout.write(self.style.WARNING(f'  • Exists: {class_obj}'))
            else:
                # Create new class
                class_obj = Class(
                    name=class_data['name'],
                    class_code=class_data['code'],
                    school=school_obj,
                    order=class_data['order']
                )
                class_obj.save()
                classes[class_data['code']] = class_obj
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {class_obj}'))

        # 4. Create Departments (for SSS only)
        self.stdout.write('Creating departments...')
        sss_school = schools['Senior Secondary']
        departments_data = [
            {'name': 'Science', 'code': 'SCI'},
            {'name': 'Arts', 'code': 'ART'},
            {'name': 'Commercial', 'code': 'COM'},
        ]

        departments = {}
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                school=sss_school,
                code=dept_data['code'],
                defaults={'name': dept_data['name']}
            )
            departments[dept_data['code']] = dept
            self.stdout.write(self.style.SUCCESS(f'  ✓ {dept}'))

        # 5. Create Subject Groups
        self.stdout.write('Creating subject groups...')
        subject_groups_data = [
            {'name': 'Core Subjects', 'selection_type': 'multiple'},
            {'name': 'Science Subjects', 'selection_type': 'multiple'},
            {'name': 'Arts Subjects', 'selection_type': 'multiple'},
            {'name': 'Commercial Subjects', 'selection_type': 'multiple'},
            {'name': 'Trade Subjects', 'selection_type': 'single'},
        ]

        subject_groups = {}
        for sg_data in subject_groups_data:
            sg, created = SubjectGroup.objects.get_or_create(
                name=sg_data['name'],
                defaults={'selection_type': sg_data['selection_type']}
            )
            subject_groups[sg_data['name']] = sg
            self.stdout.write(self.style.SUCCESS(f'  ✓ {sg}'))

        # 6. Create Subjects
        self.stdout.write('Creating subjects...')
        subjects_data = [
            # Core subjects for all classes
            {'name': 'Mathematics', 'classes': ['PRI1', 'PRI2', 'PRI3', 'PRI4', 'PRI5', 'PRI6', 'JSS1', 'JSS2', 'JSS3', 'SS1', 'SS2', 'SS3'], 'group': 'Core Subjects'},
            {'name': 'English Language', 'classes': ['PRI1', 'PRI2', 'PRI3', 'PRI4', 'PRI5', 'PRI6', 'JSS1', 'JSS2', 'JSS3', 'SS1', 'SS2', 'SS3'], 'group': 'Core Subjects'},
            
            # Science subjects
            {'name': 'Basic Science', 'classes': ['JSS1', 'JSS2', 'JSS3'], 'group': 'Science Subjects'},
            {'name': 'Physics', 'classes': ['SS1', 'SS2', 'SS3'], 'group': 'Science Subjects', 'dept': 'SCI'},
            {'name': 'Chemistry', 'classes': ['SS1', 'SS2', 'SS3'], 'group': 'Science Subjects', 'dept': 'SCI'},
            {'name': 'Biology', 'classes': ['SS1', 'SS2', 'SS3'], 'group': 'Science Subjects', 'dept': 'SCI'},
            
            # Arts subjects
            {'name': 'Literature in English', 'classes': ['SS1', 'SS2', 'SS3'], 'group': 'Arts Subjects', 'dept': 'ART'},
            {'name': 'Government', 'classes': ['SS1', 'SS2', 'SS3'], 'group': 'Arts Subjects', 'dept': 'ART'},
            {'name': 'Economics', 'classes': ['SS1', 'SS2', 'SS3'], 'group': 'Arts Subjects', 'dept': 'ART'},
            {'name': 'History', 'classes': ['JSS1', 'JSS2', 'JSS3', 'SS1', 'SS2', 'SS3'], 'group': 'Arts Subjects'},
            
            # Commercial subjects
            {'name': 'Commerce', 'classes': ['SS1', 'SS2', 'SS3'], 'group': 'Commercial Subjects', 'dept': 'COM'},
            {'name': 'Accounting', 'classes': ['SS1', 'SS2', 'SS3'], 'group': 'Commercial Subjects', 'dept': 'COM'},
            
            # Other subjects
            {'name': 'Computer Studies', 'classes': ['JSS1', 'JSS2', 'JSS3', 'SS1', 'SS2', 'SS3'], 'group': 'Core Subjects'},
            {'name': 'Civic Education', 'classes': ['JSS1', 'JSS2', 'JSS3'], 'group': 'Core Subjects'},
        ]

        created_subjects = {}
        for subj_data in subjects_data:
            for class_code in subj_data['classes']:
                class_obj = classes.get(class_code)
                if not class_obj:
                    continue
                
                # Generate subject code
                subj_code = f"{subj_data['name'][:3].upper()}-{class_code}"
                
                dept_obj = None
                if subj_data.get('dept'):
                    dept_obj = departments.get(subj_data['dept'])
                
                subj, created = Subject.objects.get_or_create(
                    code=subj_code,
                    defaults={
                        'name': subj_data['name'],
                        'school': class_obj.school,
                        'class_model': class_obj,
                        'department': dept_obj,
                        'subject_group': subject_groups.get(subj_data['group']),
                    }
                )
                created_subjects[subj_code] = subj
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {subj}'))

        # 7. Create Grades
        self.stdout.write('Creating grades...')
        grades_data = [
            {'grade_letter': 'A', 'grade_name': 'A', 'min_score': 70, 'max_score': 100, 'grade_description': 'Excellent'},
            {'grade_letter': 'B', 'grade_name': 'B', 'min_score': 60, 'max_score': 69, 'grade_description': 'Very Good'},
            {'grade_letter': 'C', 'grade_name': 'C', 'min_score': 50, 'max_score': 59, 'grade_description': 'Good'},
            {'grade_letter': 'D', 'grade_name': 'D', 'min_score': 45, 'max_score': 49, 'grade_description': 'Pass'},
            {'grade_letter': 'E', 'grade_name': 'E', 'min_score': 40, 'max_score': 44, 'grade_description': 'Pass'},
            {'grade_letter': 'F', 'grade_name': 'F', 'min_score': 0, 'max_score': 39, 'grade_description': 'Fail'},
        ]

        for grade_data in grades_data:
            grade, created = Grade.objects.get_or_create(
                grade_letter=grade_data['grade_letter'],
                defaults=grade_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Grade {grade.grade_name}'))

        # 8. Create Exam Halls
        self.stdout.write('Creating exam halls...')
        exam_halls_data = [
            {'name': 'Main Hall', 'number_of_seats': 150, 'is_active': True},
            {'name': 'Block A Hall', 'number_of_seats': 80, 'is_active': True},
            {'name': 'Library Hall', 'number_of_seats': 60, 'is_active': True},
        ]
        
        for hall_data in exam_halls_data:
            hall, created = ExamHall.objects.get_or_create(
                name=hall_data['name'],
                defaults={
                    'number_of_seats': hall_data['number_of_seats'],
                    'is_active': hall_data['is_active']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {hall}'))
            else:
                self.stdout.write(self.style.WARNING(f'  • Exists: {hall}'))

        # 9. Create Questions for Question Bank
        self.stdout.write('Creating questions in question bank...')
        
        # Mathematics questions for different classes
        math_questions = self._create_math_questions(created_subjects, user)
        physics_questions = self._create_physics_questions(created_subjects, user)
        chemistry_questions = self._create_chemistry_questions(created_subjects, user)
        english_questions = self._create_english_questions(created_subjects, user)
        
        total_questions = math_questions + physics_questions + chemistry_questions + english_questions
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Database populated successfully!'))
        self.stdout.write(self.style.SUCCESS(f'  • Schools: {len(schools)}'))
        self.stdout.write(self.style.SUCCESS(f'  • Classes: {len(classes)}'))
        self.stdout.write(self.style.SUCCESS(f'  • Subjects: {len(created_subjects)}'))
        self.stdout.write(self.style.SUCCESS(f'  • Exam Halls: {len(exam_halls_data)}'))
        self.stdout.write(self.style.SUCCESS(f'  • Questions: {total_questions}'))

    def _create_math_questions(self, subjects, user):
        """Create mathematics questions"""
        count = 0
        math_subjects = [s for code, s in subjects.items() if 'MAT' in code]
        
        questions_data = [
            {
                'topic': 'Algebra',
                'question_text': 'Solve for x: 2x + 5 = 15',
                'option_a': 'x = 3',
                'option_b': 'x = 5',
                'option_c': 'x = 7',
                'option_d': 'x = 10',
                'correct_answer': 'B',
                'explanation': '2x + 5 = 15\n2x = 15 - 5\n2x = 10\nx = 5',
                'difficulty': 'easy',
                'marks': 2
            },
            {
                'topic': 'Algebra',
                'question_text': 'Simplify: 3(x + 4) - 2(x - 1)',
                'option_a': 'x + 10',
                'option_b': 'x + 14',
                'option_c': 'x + 12',
                'option_d': 'x + 8',
                'correct_answer': 'B',
                'explanation': '3(x + 4) - 2(x - 1) = 3x + 12 - 2x + 2 = x + 14',
                'difficulty': 'medium',
                'marks': 3
            },
            {
                'topic': 'Geometry',
                'question_text': 'What is the area of a rectangle with length 8cm and width 5cm?',
                'option_a': '13 cm²',
                'option_b': '26 cm²',
                'option_c': '40 cm²',
                'option_d': '45 cm²',
                'correct_answer': 'C',
                'explanation': 'Area = length × width = 8 × 5 = 40 cm²',
                'difficulty': 'easy',
                'marks': 2
            },
            {
                'topic': 'Fractions',
                'question_text': 'What is 3/4 + 1/2?',
                'option_a': '1/4',
                'option_b': '5/4',
                'option_c': '4/6',
                'option_d': '7/8',
                'correct_answer': 'B',
                'explanation': '3/4 + 1/2 = 3/4 + 2/4 = 5/4 or 1¼',
                'difficulty': 'easy',
                'marks': 2
            },
            {
                'topic': 'Percentages',
                'question_text': 'What is 25% of 80?',
                'option_a': '15',
                'option_b': '20',
                'option_c': '25',
                'option_d': '30',
                'correct_answer': 'B',
                'explanation': '25% of 80 = (25/100) × 80 = 20',
                'difficulty': 'easy',
                'marks': 2
            },
            {
                'topic': 'Quadratic Equations',
                'question_text': 'Solve: x² - 5x + 6 = 0',
                'option_a': 'x = 1 or x = 6',
                'option_b': 'x = 2 or x = 3',
                'option_c': 'x = -2 or x = -3',
                'option_d': 'x = 0 or x = 5',
                'correct_answer': 'B',
                'explanation': 'x² - 5x + 6 = 0\n(x - 2)(x - 3) = 0\nx = 2 or x = 3',
                'difficulty': 'hard',
                'marks': 4
            },
            {
                'topic': 'Ratios',
                'question_text': 'Simplify the ratio 12:18',
                'option_a': '1:2',
                'option_b': '2:3',
                'option_c': '3:4',
                'option_d': '4:5',
                'correct_answer': 'B',
                'explanation': '12:18 = (12÷6):(18÷6) = 2:3',
                'difficulty': 'medium',
                'marks': 2
            },
            {
                'topic': 'Decimals',
                'question_text': 'Convert 0.75 to a fraction',
                'option_a': '1/4',
                'option_b': '1/2',
                'option_c': '3/4',
                'option_d': '2/3',
                'correct_answer': 'C',
                'explanation': '0.75 = 75/100 = 3/4',
                'difficulty': 'easy',
                'marks': 2
            },
        ]

        for subject in math_subjects[:3]:  # Create for first 3 math subjects
            for q_data in questions_data:
                # Get or create the topic (make a copy to avoid modifying original)
                topic_name = q_data['topic']
                topic = self._get_or_create_topic(subject, topic_name)
                
                # Create a copy without the 'topic' key
                q_data_copy = {k: v for k, v in q_data.items() if k != 'topic'}
                
                Question.objects.get_or_create(
                    subject=subject,
                    question_text=q_data_copy['question_text'],
                    defaults={
                        **q_data_copy,
                        'topic_model': topic,
                        'question_type': 'multiple_choice',
                        'created_by': user,
                        'is_verified': True
                    }
                )
                count += 1
        
        return count

    def _create_physics_questions(self, subjects, user):
        """Create physics questions"""
        count = 0
        physics_subjects = [s for code, s in subjects.items() if 'PHY' in code]
        
        questions_data = [
            {
                'topic': 'Mechanics',
                'question_text': 'What is the SI unit of force?',
                'option_a': 'Joule',
                'option_b': 'Newton',
                'option_c': 'Watt',
                'option_d': 'Pascal',
                'correct_answer': 'B',
                'explanation': 'The SI unit of force is Newton (N), named after Sir Isaac Newton',
                'difficulty': 'easy',
                'marks': 2
            },
            {
                'topic': 'Motion',
                'question_text': 'A car travels 100km in 2 hours. What is its average speed?',
                'option_a': '25 km/h',
                'option_b': '40 km/h',
                'option_c': '50 km/h',
                'option_d': '75 km/h',
                'correct_answer': 'C',
                'explanation': 'Speed = Distance/Time = 100km/2h = 50 km/h',
                'difficulty': 'easy',
                'marks': 2
            },
            {
                'topic': 'Energy',
                'question_text': 'Which of the following is a form of renewable energy?',
                'option_a': 'Coal',
                'option_b': 'Natural Gas',
                'option_c': 'Solar',
                'option_d': 'Petroleum',
                'correct_answer': 'C',
                'explanation': 'Solar energy is renewable as it comes from the sun and is constantly replenished',
                'difficulty': 'easy',
                'marks': 1
            },
            {
                'topic': 'Electricity',
                'question_text': 'What is the formula for Ohm\'s Law?',
                'option_a': 'V = I × R',
                'option_b': 'P = V × I',
                'option_c': 'E = mc²',
                'option_d': 'F = ma',
                'correct_answer': 'A',
                'explanation': 'Ohm\'s Law states that Voltage (V) = Current (I) × Resistance (R)',
                'difficulty': 'medium',
                'marks': 2
            },
            {
                'topic': 'Waves',
                'question_text': 'Sound cannot travel through:',
                'option_a': 'Solid',
                'option_b': 'Liquid',
                'option_c': 'Gas',
                'option_d': 'Vacuum',
                'correct_answer': 'D',
                'explanation': 'Sound requires a medium to travel. It cannot travel through vacuum (empty space)',
                'difficulty': 'easy',
                'marks': 2
            },
        ]

        for subject in physics_subjects:
            for q_data in questions_data:
                # Get or create the topic (make a copy to avoid modifying original)
                topic_name = q_data['topic']
                topic = self._get_or_create_topic(subject, topic_name)
                
                # Create a copy without the 'topic' key
                q_data_copy = {k: v for k, v in q_data.items() if k != 'topic'}
                
                Question.objects.get_or_create(
                    subject=subject,
                    question_text=q_data_copy['question_text'],
                    defaults={
                        **q_data_copy,
                        'topic_model': topic,
                        'question_type': 'multiple_choice',
                        'created_by': user,
                        'is_verified': True
                    }
                )
                count += 1
        
        return count

    def _create_chemistry_questions(self, subjects, user):
        """Create chemistry questions"""
        count = 0
        chem_subjects = [s for code, s in subjects.items() if 'CHE' in code]
        
        questions_data = [
            {
                'topic': 'Atomic Structure',
                'question_text': 'What is the atomic number of Carbon?',
                'option_a': '4',
                'option_b': '6',
                'option_c': '8',
                'option_d': '12',
                'correct_answer': 'B',
                'explanation': 'Carbon has 6 protons, so its atomic number is 6',
                'difficulty': 'easy',
                'marks': 1
            },
            {
                'topic': 'Chemical Bonding',
                'question_text': 'What type of bond is formed when electrons are shared?',
                'option_a': 'Ionic bond',
                'option_b': 'Metallic bond',
                'option_c': 'Covalent bond',
                'option_d': 'Hydrogen bond',
                'correct_answer': 'C',
                'explanation': 'Covalent bonds are formed when atoms share electrons',
                'difficulty': 'medium',
                'marks': 2
            },
            {
                'topic': 'Periodic Table',
                'question_text': 'Which element has the chemical symbol "O"?',
                'option_a': 'Gold',
                'option_b': 'Oxygen',
                'option_c': 'Osmium',
                'option_d': 'Oxide',
                'correct_answer': 'B',
                'explanation': 'O is the chemical symbol for Oxygen',
                'difficulty': 'easy',
                'marks': 1
            },
            {
                'topic': 'Acids and Bases',
                'question_text': 'What is the pH of a neutral solution?',
                'option_a': '0',
                'option_b': '7',
                'option_c': '14',
                'option_d': '10',
                'correct_answer': 'B',
                'explanation': 'A neutral solution has a pH of 7. Below 7 is acidic, above 7 is basic',
                'difficulty': 'easy',
                'marks': 2
            },
        ]

        for subject in chem_subjects:
            for q_data in questions_data:
                # Get or create the topic (make a copy to avoid modifying original)
                topic_name = q_data['topic']
                topic = self._get_or_create_topic(subject, topic_name)
                
                # Create a copy without the 'topic' key
                q_data_copy = {k: v for k, v in q_data.items() if k != 'topic'}
                
                Question.objects.get_or_create(
                    subject=subject,
                    question_text=q_data_copy['question_text'],
                    defaults={
                        **q_data_copy,
                        'topic_model': topic,
                        'question_type': 'multiple_choice',
                        'created_by': user,
                        'is_verified': True
                    }
                )
                count += 1
        
        return count

    def _create_english_questions(self, subjects, user):
        """Create English Language questions"""
        count = 0
        eng_subjects = [s for code, s in subjects.items() if 'ENG' in code]
        
        questions_data = [
            {
                'topic': 'Grammar',
                'question_text': 'Choose the correct form: She _____ to school every day.',
                'option_a': 'go',
                'option_b': 'goes',
                'option_c': 'going',
                'option_d': 'gone',
                'correct_answer': 'B',
                'explanation': 'The correct form is "goes" because the subject "she" is third person singular',
                'difficulty': 'easy',
                'marks': 1
            },
            {
                'topic': 'Vocabulary',
                'question_text': 'What is the synonym of "happy"?',
                'option_a': 'Sad',
                'option_b': 'Angry',
                'option_c': 'Joyful',
                'option_d': 'Tired',
                'correct_answer': 'C',
                'explanation': 'Joyful means the same as happy',
                'difficulty': 'easy',
                'marks': 1
            },
            {
                'topic': 'Parts of Speech',
                'question_text': 'Identify the noun in this sentence: "The cat runs quickly."',
                'option_a': 'The',
                'option_b': 'cat',
                'option_c': 'runs',
                'option_d': 'quickly',
                'correct_answer': 'B',
                'explanation': 'Cat is a noun (a thing/animal). "runs" is a verb, "quickly" is an adverb',
                'difficulty': 'easy',
                'marks': 2
            },
            {
                'topic': 'Tenses',
                'question_text': 'Which sentence is in the past tense?',
                'option_a': 'I am eating',
                'option_b': 'I will eat',
                'option_c': 'I ate',
                'option_d': 'I eat',
                'correct_answer': 'C',
                'explanation': '"Ate" is the past tense of "eat"',
                'difficulty': 'medium',
                'marks': 2
            },
            {
                'topic': 'Comprehension',
                'question_text': 'What is the antonym of "hot"?',
                'option_a': 'Warm',
                'option_b': 'Cold',
                'option_c': 'Cool',
                'option_d': 'Mild',
                'correct_answer': 'B',
                'explanation': 'Cold is the opposite of hot',
                'difficulty': 'easy',
                'marks': 1
            },
        ]

        for subject in eng_subjects[:4]:  # Create for first 4 English subjects
            for q_data in questions_data:
                # Get or create the topic (make a copy to avoid modifying original)
                topic_name = q_data['topic']
                topic = self._get_or_create_topic(subject, topic_name)
                
                # Create a copy without the 'topic' key
                q_data_copy = {k: v for k, v in q_data.items() if k != 'topic'}
                
                Question.objects.get_or_create(
                    subject=subject,
                    question_text=q_data_copy['question_text'],
                    defaults={
                        **q_data_copy,
                        'topic_model': topic,
                        'question_type': 'multiple_choice',
                        'created_by': user,
                        'is_verified': True
                    }
                )
                count += 1
        
        return count

