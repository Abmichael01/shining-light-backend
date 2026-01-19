from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import TimetableEntry, AttendanceRecord, SessionTerm, Session
from datetime import date

class Command(BaseCommand):
    help = 'Generates attendance records for the day'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Date in YYYY-MM-DD format')

    def handle(self, *args, **kwargs):
        if kwargs['date']:
            today = date.fromisoformat(kwargs['date'])
        else:
            today = timezone.localdate()
            
        day_index = today.weekday() # 0=Mon, 6=Sun
        
        self.stdout.write(f"Generating attendance for {today} (Day {day_index})")

        # 1. Get Current Term
        current_term = SessionTerm.objects.filter(is_current=True).first()
        if not current_term:
            # Fallback: Current session's current term
            current_session = Session.objects.filter(is_current=True).first()
            if current_session:
                current_term = current_session.session_terms.filter(is_current=True).first()
        
        if not current_term:
            self.stdout.write(self.style.ERROR("No current term found."))
            return

        # 2. Get Timetable Entries for Today
        entries = TimetableEntry.objects.filter(
            session_term=current_term,
            day_of_week=day_index
        ).select_related('class_model', 'period', 'subject')

        count = 0
        existing = 0
        
        for entry in entries:
            # Create Attendance Header
            record, created = AttendanceRecord.objects.get_or_create(
                class_model=entry.class_model,
                date=today,
                timetable_entry=entry,
                defaults={
                    'session_term': current_term
                }
            )
            
            if created:
                count += 1
                self.stdout.write(f"Created: {entry.class_model.name} - {entry.period.name} ({entry.subject.name if entry.subject else 'No Subject'})")
            else:
                existing += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Created {count} records. Skipped {existing} existing."))
