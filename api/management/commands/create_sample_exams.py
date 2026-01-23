from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from api.models.scheduling import Schedule, ScheduleEntry
from api.models.academic import Class, Subject, SessionTerm


class Command(BaseCommand):
    help = 'Create sample exam timetable with 5 days of exam data'

    def handle(self, *args, **options):
        # Get current session/term
        try:
            session_term = SessionTerm.objects.filter(is_current=True).first()
            if not session_term:
                self.stdout.write(self.style.ERROR('No current session/term found. Please set a current session/term first.'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching session/term: {e}'))
            return

        # Create exam schedule
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=4)  # 5 days total

        schedule = Schedule.objects.create(
            name=f'Mid-Term Exam',
            description='Sample exam timetable with 5 days of exams',
            schedule_type='exam',
            start_date=start_date,
            end_date=end_date,
            session_term=session_term,
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f'Created schedule: {schedule.name}'))

        # Get classes and subjects
        classes = Class.objects.all()[:6]  # Limit to 6 classes
        if not classes:
            self.stdout.write(self.style.ERROR('No classes found. Please create classes first.'))
            schedule.delete()
            return

        # Define exam slots
        morning_slots = [
            {'start': '08:00:00', 'end': '10:00:00'},
            {'start': '10:30:00', 'end': '12:30:00'},
        ]
        afternoon_slot = {'start': '14:00:00', 'end': '16:00:00'}

        entry_count = 0

        # Create exams for 5 days
        for day in range(5):
            exam_date = start_date + timedelta(days=day)
            
            self.stdout.write(f'\nCreating exams for {exam_date}...')

            for cls in classes:
                # Get subjects for this class
                class_subjects = Subject.objects.filter(class_model=cls)
                if not class_subjects.exists():
                    # Fall back to general subjects
                    class_subjects = Subject.objects.filter(class_model__isnull=True)
                
                if not class_subjects.exists():
                    self.stdout.write(self.style.WARNING(f'  No subjects found for {cls.name}, skipping...'))
                    continue

                # Assign 2-3 exams per day per class
                num_exams = min(3, class_subjects.count())
                subjects_to_use = list(class_subjects[:num_exams])

                for i, subject in enumerate(subjects_to_use):
                    # Use morning slots for first 2 exams, afternoon for 3rd
                    if i < 2:
                        slot = morning_slots[i]
                    else:
                        slot = afternoon_slot

                    entry = ScheduleEntry.objects.create(
                        schedule=schedule,
                        date=exam_date,
                        start_time=slot['start'],
                        end_time=slot['end'],
                        title=subject.name,
                        linked_subject=subject
                    )
                    entry.target_classes.set([cls])
                    entry_count += 1

                self.stdout.write(f'  ✓ {cls.name}: {num_exams} exams')

        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully created {entry_count} exam entries across 5 days'))
        self.stdout.write(self.style.SUCCESS(f'Schedule ID: {schedule.id}'))
