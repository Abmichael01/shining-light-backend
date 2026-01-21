from django.core.management.base import BaseCommand
from api.models import Subject, Topic, Question
from django.db import transaction

class Command(BaseCommand):
    help = 'Seeds database with default topics for all subjects and clears existing questions'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting database seeding...')

        with transaction.atomic():
            # 1. Delete all existing questions
            question_count = Question.objects.count()
            Question.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {question_count} existing questions.'))

            # 2. Define standard topics
            standard_topics = [
                {
                    'name': 'Introduction',
                    'description': 'Basic introduction to the subject concepts.'
                },
                {
                    'name': 'Fundamentals',
                    'description': 'Core fundamental principles.'
                },
                {
                    'name': 'Advanced Concepts',
                    'description': 'More complex and advanced topics.'
                },
                {
                    'name': 'Practical Applications',
                    'description': 'Real-world applications and practical exercises.'
                }
            ]

            # 3. Create topics for each subject
            subjects = Subject.objects.all()
            if not subjects.exists():
                self.stdout.write(self.style.WARNING('No subjects found! Please create subjects first.'))
                return

            topics_created = 0
            for subject in subjects:
                for topic_data in standard_topics:
                    topic, created = Topic.objects.get_or_create(
                        subject=subject,
                        name=topic_data['name'],
                        defaults={
                            'description': topic_data['description'],
                            'is_active': True
                        }
                    )
                    if created:
                        topics_created += 1

            self.stdout.write(self.style.SUCCESS(f'Successfully seeded {topics_created} new topics across {subjects.count()} subjects.'))
