from django.core.management.base import BaseCommand
from api.models.scheduling import Schedule


class Command(BaseCommand):
    help = 'Delete all exam-type schedules and their entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting',
        )

    def handle(self, *args, **options):
        # Get all exam schedules
        exam_schedules = Schedule.objects.filter(schedule_type='exam')
        
        if not exam_schedules.exists():
            self.stdout.write(self.style.WARNING('No exam schedules found.'))
            return

        # Display schedules to be deleted
        self.stdout.write(self.style.WARNING(f'\nFound {exam_schedules.count()} exam schedule(s):'))
        for schedule in exam_schedules:
            entry_count = schedule.entries.count()
            self.stdout.write(f'  - {schedule.name} (ID: {schedule.id}) - {entry_count} entries')

        # Confirm deletion
        if not options['confirm']:
            confirm = input('\nAre you sure you want to delete these schedules? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Deletion cancelled.'))
                return

        # Delete schedules (entries will be deleted via CASCADE)
        deleted_count = exam_schedules.count()
        exam_schedules.delete()

        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully deleted {deleted_count} exam schedule(s) and all their entries.'))
