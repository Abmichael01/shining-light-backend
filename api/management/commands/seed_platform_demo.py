from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import (
    AdmissionSettings,
    Assignment,
    CBTExamCode,
    Class,
    Exam,
    ExamHall,
    FeePayment,
    FeeType,
    Guardian,
    LoanTenure,
    PaymentPurpose,
    Period,
    Question,
    ResultPin,
    SalaryGrade,
    Schedule,
    ScheduleEntry,
    School,
    Session,
    SessionTerm,
    Staff,
    StaffEducation,
    StaffSalary,
    StaffWallet,
    Student,
    StudentAttendance,
    StudentSubject,
    Subject,
    SystemSetting,
    TermReport,
    TimetableEntry,
    Topic,
    User,
    BioData,
    AttendanceRecord,
)


class Command(BaseCommand):
    help = "Seed a complete demo dataset for local platform testing."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Seeding complete demo platform data..."))

        self.stdout.write("Running core academic seed...")
        call_command("seed_data", verbosity=0)

        admin = self.seed_shortcut_admins()
        session, term = self.get_current_academic_period()
        self.seed_system_settings()
        self.seed_admission_settings(admin)
        self.seed_topics()
        self.attach_missing_question_topics()

        teachers = self.seed_staff(admin)
        students = self.seed_students(admin, session, term)
        self.seed_subject_registrations(students, admin, session, term)
        self.seed_finance(admin, students, term)
        self.seed_staff_finance(admin, teachers)
        self.seed_exams(term)
        self.seed_timetable_and_attendance(teachers, term)
        self.seed_assignments(teachers)
        self.seed_result_pin(admin, students, session, term)

        self.print_summary()

    def seed_shortcut_admins(self):
        shortcut_admins = [
            ("admin@gmail.com", "mtn*556#"),
            ("admin@shininglightschools.com", "admin123"),
        ]
        primary_admin = None
        for email, password in shortcut_admins:
            user, _ = User.objects.get_or_create(email=email)
            user.user_type = "admin"
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()
            if email == "admin@gmail.com":
                primary_admin = user
            self.stdout.write(self.style.SUCCESS(f"  admin ready: {email}"))
        return primary_admin or User.objects.filter(is_superuser=True).first()

    def get_current_academic_period(self):
        session = Session.objects.filter(is_current=True).first()
        if not session:
            session = Session.objects.order_by("-start_date").first()
            if session:
                session.is_current = True
                session.save()

        term = None
        if session:
            term = session.session_terms.filter(is_current=True).first()
            if not term:
                term = session.session_terms.order_by("term_name").first()
                if term:
                    term.is_current = True
                    term.save()

        if term:
            term.is_subject_registration_open = True
            term.registration_deadline = timezone.localdate() + timedelta(days=30)
            term.save()

        return session, term

    def seed_system_settings(self):
        settings = SystemSetting.load()
        settings.show_announcement = True
        settings.announcement_title = "Welcome"
        settings.announcement_message = "Shinning Light demo portal is ready for testing."
        settings.is_maintenance_mode = False
        settings.disable_staff_login = False
        settings.disable_student_login = False
        settings.result_pin_price = Decimal("1500.00")
        settings.late_subject_registration_fee = Decimal("500.00")
        settings.save()
        self.stdout.write(self.style.SUCCESS("  system settings ready"))

    def seed_admission_settings(self, admin):
        now = timezone.now()
        for school in School.objects.all():
            settings, _ = AdmissionSettings.objects.get_or_create(
                school=school,
                defaults={"created_by": admin},
            )
            settings.is_admission_open = True
            settings.admission_start_datetime = now - timedelta(days=7)
            settings.admission_end_datetime = now + timedelta(days=90)
            settings.application_fee_amount = Decimal("5000.00")
            settings.created_by = settings.created_by or admin
            settings.save()
        self.stdout.write(self.style.SUCCESS("  admission settings ready"))

    def seed_topics(self):
        standard_topics = [
            ("Introduction", "Basic introduction to the subject concepts."),
            ("Fundamentals", "Core principles and foundational knowledge."),
            ("Practical Applications", "Applied exercises and real-world usage."),
            ("Revision", "Term revision and exam preparation."),
        ]
        created = 0
        for subject in Subject.objects.all():
            for name, description in standard_topics:
                _, was_created = Topic.objects.get_or_create(
                    subject=subject,
                    name=name,
                    defaults={"description": description, "is_active": True},
                )
                if was_created:
                    created += 1
        self.stdout.write(self.style.SUCCESS(f"  topics ready ({created} new)"))

    def attach_missing_question_topics(self):
        updated = 0
        for subject in Subject.objects.all():
            topic, _ = Topic.objects.get_or_create(
                subject=subject,
                name="General",
                defaults={
                    "description": f"General questions for {subject.name}.",
                    "is_active": True,
                },
            )
            updated += Question.objects.filter(
                subject=subject,
                topic_model__isnull=True,
            ).update(topic_model=topic)
        self.stdout.write(self.style.SUCCESS(f"  question topics linked ({updated} updated)"))

    def seed_staff(self, admin):
        schools = list(School.objects.all())
        if not schools:
            return []

        staff_data = [
            ("oluwaseun.adebayo@shininglightschools.com", "Adebayo", "Oluwaseun", "mr"),
            ("fatima.ibrahim@shininglightschools.com", "Ibrahim", "Fatima", "mrs"),
            ("chioma.okafor@shininglightschools.com", "Okafor", "Chioma", "miss"),
            ("david.williams@shininglightschools.com", "Williams", "David", "mr"),
            ("maryam.yusuf@shininglightschools.com", "Yusuf", "Maryam", "mrs"),
        ]

        staff_members = []
        for idx, (email, surname, first_name, title) in enumerate(staff_data):
            user, _ = User.objects.get_or_create(email=email)
            user.user_type = "staff"
            user.is_staff = True
            user.is_active = True
            user.set_password("password123")
            user.save()

            staff, _ = Staff.objects.get_or_create(
                user=user,
                defaults={
                    "title": title,
                    "surname": surname,
                    "first_name": first_name,
                    "state_of_origin": "Lagos",
                    "date_of_birth": date(1990, 1, 1),
                    "permanent_address": "123 School Road",
                    "phone_number": f"080000000{idx}",
                    "marital_status": "single",
                    "religion": "christian",
                    "staff_type": "teaching",
                    "school": schools[idx % len(schools)],
                    "zone": "ransowa",
                    "status": "active",
                    "created_by": admin,
                },
            )
            staff.title = title
            staff.surname = surname
            staff.first_name = first_name
            staff.staff_type = "teaching"
            staff.status = "active"
            staff.created_by = staff.created_by or admin
            staff.school = staff.school or schools[idx % len(schools)]
            staff.save()

            StaffEducation.objects.get_or_create(
                staff=staff,
                level="tertiary",
                institution_name="University of Lagos",
                defaults={"year_of_graduation": 2015, "degree": "bed"},
            )
            StaffWallet.objects.get_or_create(staff=staff)
            staff_members.append(staff)

        for index, class_obj in enumerate(Class.objects.order_by("order")):
            teacher = staff_members[index % len(staff_members)]
            class_obj.assigned_teachers.add(teacher)
            if not class_obj.class_staff:
                class_obj.class_staff = teacher.user
                class_obj.save()

        for subject in Subject.objects.all():
            subject.assigned_teachers.add(*staff_members)

        self.stdout.write(self.style.SUCCESS(f"  staff ready ({len(staff_members)} teachers)"))
        return staff_members

    def seed_students(self, admin, session, term):
        students = []
        classes = list(Class.objects.order_by("order"))
        for idx, class_obj in enumerate(classes, start=1):
            email = f"student{idx}@test.com"
            user, _ = User.objects.get_or_create(email=email)
            user.user_type = "student"
            user.is_staff = False
            user.is_superuser = False
            user.is_active = True
            user.set_password("password123")
            user.save()

            student = getattr(user, "student_profile", None)
            if student is None:
                student = Student.objects.create(
                    user=user,
                    school=class_obj.school,
                    class_model=class_obj,
                    source="admin_registration",
                    status="applicant",
                    created_by=admin,
                )
            else:
                student.school = class_obj.school
                student.class_model = class_obj
                student.source = student.source or "admin_registration"
                student.created_by = student.created_by or admin
                if student.status not in ["accepted", "enrolled"]:
                    student.status = "applicant"
                student.save()

            BioData.objects.update_or_create(
                student=student,
                defaults={
                    "surname": "Test",
                    "first_name": f"Student{idx}",
                    "gender": "male" if idx % 2 else "female",
                    "date_of_birth": date(2010, 1, 1) + timedelta(days=idx),
                    "state_of_origin": "Lagos",
                    "permanent_address": "123 Test Street",
                    "nationality": "Nigerian",
                },
            )

            Guardian.objects.update_or_create(
                student=student,
                guardian_type="father",
                defaults={
                    "surname": "Parent",
                    "first_name": f"Guardian{idx}",
                    "state_of_origin": "Lagos",
                    "phone_number": f"08012345{idx:03d}",
                    "email": f"guardian{idx}@test.com",
                    "occupation": "Trader",
                    "place_of_employment": "Self Employed",
                    "is_primary_contact": True,
                },
            )

            if student.status != "enrolled":
                student.status = "enrolled"
                student.save()
            students.append(student)

        self.stdout.write(self.style.SUCCESS(f"  students ready ({len(students)} demo students)"))
        return students

    def seed_subject_registrations(self, students, admin, session, term):
        if not session or not term:
            return

        registrations = 0
        for student in students:
            subjects = Subject.objects.filter(
                school=student.school,
                class_model=student.class_model,
            ).order_by("name")
            for idx, subject in enumerate(subjects, start=1):
                ca_score = Decimal(24 + (idx % 12))
                exam_score = Decimal(38 + (idx % 18))
                registration, _ = StudentSubject.objects.update_or_create(
                    student=student,
                    subject=subject,
                    session=session,
                    session_term=term,
                    defaults={
                        "is_active": True,
                        "cleared": True,
                        "openday_cleared": True,
                        "ca_score": ca_score,
                        "exam_score": exam_score,
                        "teacher_comment": "Good progress. Keep improving.",
                        "result_entered_by": admin,
                        "result_entered_at": timezone.now(),
                    },
                )
                registration.save()
                registrations += 1

            total_score = sum(
                (row.total_score or Decimal("0.00"))
                for row in StudentSubject.objects.filter(
                    student=student,
                    session=session,
                    session_term=term,
                )
            )
            subject_count = StudentSubject.objects.filter(
                student=student,
                session=session,
                session_term=term,
            ).count()
            average = (total_score / subject_count) if subject_count else Decimal("0.00")
            TermReport.objects.update_or_create(
                student=student,
                session=session,
                session_term=term,
                defaults={
                    "punctuality": 4,
                    "mental_alertness": 4,
                    "behavior": 5,
                    "reliability": 4,
                    "attentiveness": 4,
                    "respect": 5,
                    "neatness": 4,
                    "politeness": 5,
                    "honesty": 5,
                    "relationship_staff": 4,
                    "relationship_students": 4,
                    "attitude_school": 5,
                    "self_control": 4,
                    "handwriting": 4,
                    "reading": 4,
                    "verbal_fluency": 4,
                    "musical_skills": 3,
                    "creative_arts": 4,
                    "physical_education": 4,
                    "general_reasoning": 4,
                    "class_teacher_report": "A disciplined learner with steady academic growth.",
                    "ict_report": "Uses digital learning tools responsibly.",
                    "principal_report": "A pleasing performance. Keep shining.",
                    "days_present": 58,
                    "days_absent": 2,
                    "total_days": 60,
                    "total_score": total_score,
                    "average_score": average,
                    "class_position": 1,
                    "grade_position": 1,
                    "total_students": max(student.class_model.students.count(), 1),
                    "total_students_grade": max(student.class_model.students.count(), 1),
                },
            )

        self.stdout.write(self.style.SUCCESS(f"  subject registrations ready ({registrations})"))

    def seed_finance(self, admin, students, term):
        purposes = [
            ("Tuition", "tuition"),
            ("Admission Form", "admission_form"),
            ("Examination", "examination"),
            ("Result PIN", "result_pin"),
            ("PTA Levy", "pta_levy"),
        ]
        for name, code in purposes:
            PaymentPurpose.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": f"{name} payments"},
            )

        tuition_amounts = {
            "Nursery": Decimal("40000.00"),
            "Primary": Decimal("50000.00"),
            "Junior Secondary": Decimal("60000.00"),
            "Senior Secondary": Decimal("70000.00"),
        }

        for school in School.objects.all():
            tuition, _ = FeeType.objects.get_or_create(
                school=school,
                name=f"{school.school_type} Tuition",
                defaults={
                    "amount": tuition_amounts.get(school.school_type, Decimal("50000.00")),
                    "description": f"Tuition for {school.school_type} classes",
                    "is_mandatory": True,
                    "is_recurring_per_term": True,
                    "max_installments": 3,
                    "created_by": admin,
                },
            )
            tuition.applicable_classes.set(Class.objects.filter(school=school))
            if term:
                tuition.active_terms.add(term)

            for fee_name, amount, mandatory in [
                ("PTA Fee", Decimal("5000.00"), True),
                ("Exam Fee", Decimal("2000.00"), True),
                ("Result PIN", Decimal("1500.00"), False),
            ]:
                fee, _ = FeeType.objects.get_or_create(
                    school=school,
                    name=fee_name,
                    defaults={
                        "amount": amount,
                        "description": f"{fee_name} for {school.name}",
                        "is_mandatory": mandatory,
                        "is_recurring_per_term": True,
                        "created_by": admin,
                    },
                )
                if term:
                    fee.active_terms.add(term)

            if school.school_type == "Senior Secondary":
                lab_fee, _ = FeeType.objects.get_or_create(
                    school=school,
                    name="Lab Fee",
                    defaults={
                        "amount": Decimal("10000.00"),
                        "description": "Science laboratory practicals",
                        "is_mandatory": True,
                        "is_recurring_per_term": True,
                        "created_by": admin,
                    },
                )
                lab_fee.applicable_classes.set(Class.objects.filter(school=school))
                if term:
                    lab_fee.active_terms.add(term)

        purpose = PaymentPurpose.objects.get(code="tuition")
        for student in students[-3:]:
            fee = FeeType.objects.filter(
                school=student.school,
                name=f"{student.school.school_type} Tuition",
            ).first()
            if not fee:
                continue
            reference = f"DEMO-TUITION-{student.id}"
            if FeePayment.objects.filter(reference_number=reference).exists():
                continue
            FeePayment.objects.create(
                student=student,
                fee_type=fee,
                amount=min(Decimal("10000.00"), fee.amount),
                payment_purpose=purpose,
                session_term=term,
                payment_method="online",
                reference_number=reference,
                notes="Demo seed payment",
                processed_by=admin,
            )

        self.stdout.write(self.style.SUCCESS("  fees and demo payments ready"))

    def seed_staff_finance(self, admin, teachers):
        for grade_number, amount in [(1, 50000), (2, 65000), (3, 80000), (4, 100000)]:
            grade, _ = SalaryGrade.objects.get_or_create(
                grade_number=grade_number,
                defaults={
                    "monthly_amount": Decimal(amount),
                    "description": f"Demo salary grade {grade_number}",
                    "created_by": admin,
                },
            )
            grade.monthly_amount = Decimal(amount)
            grade.save()

        default_grade = SalaryGrade.objects.filter(grade_number=2).first()
        for teacher in teachers:
            if default_grade:
                StaffSalary.objects.get_or_create(
                    staff=teacher,
                    defaults={"salary_grade": default_grade, "assigned_by": admin},
                )

        for name, months, rate in [
            ("3 Months Plan", 3, Decimal("3.00")),
            ("6 Months Plan", 6, Decimal("5.00")),
            ("12 Months Plan", 12, Decimal("8.00")),
        ]:
            LoanTenure.objects.get_or_create(
                name=name,
                defaults={
                    "duration_months": months,
                    "interest_rate": rate,
                    "is_active": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("  staff finance ready"))

    def seed_exams(self, term):
        if not term:
            return
        call_command(
            "create_exams_for_all_classes",
            questions_per_exam=5,
            duration=30,
            total_marks=50,
            verbosity=0,
        )
        self.stdout.write(self.style.SUCCESS("  CBT exams ready"))

    def seed_timetable_and_attendance(self, teachers, term):
        if not term:
            return

        period_specs = [
            ("Assembly", time(7, 45), time(8, 0), "assembly"),
            ("Period 1", time(8, 0), time(8, 40), "lesson"),
            ("Period 2", time(8, 40), time(9, 20), "lesson"),
            ("Break", time(9, 20), time(9, 40), "break"),
            ("Period 3", time(9, 40), time(10, 20), "lesson"),
        ]
        for school in School.objects.all():
            for order, (name, start, end, kind) in enumerate(period_specs, start=1):
                Period.objects.update_or_create(
                    school=school,
                    name=name,
                    defaults={
                        "start_time": start,
                        "end_time": end,
                        "period_type": kind,
                        "order": order,
                    },
                )

        for class_obj in Class.objects.all():
            subjects = list(Subject.objects.filter(class_model=class_obj).order_by("name"))
            lesson_periods = list(
                Period.objects.filter(school=class_obj.school, period_type="lesson").order_by("order")
            )
            if not subjects or not lesson_periods:
                continue
            for day_index in range(5):
                for idx, period in enumerate(lesson_periods):
                    subject = subjects[(day_index + idx) % len(subjects)]
                    teacher = (
                        subject.assigned_teachers.first()
                        or class_obj.assigned_teachers.first()
                        or (teachers[(day_index + idx) % len(teachers)] if teachers else None)
                    )
                    TimetableEntry.objects.update_or_create(
                        session_term=term,
                        class_model=class_obj,
                        day_of_week=day_index,
                        period=period,
                        defaults={"subject": subject, "teacher": teacher},
                    )

        today = timezone.localdate()
        for entry in TimetableEntry.objects.filter(session_term=term, day_of_week=today.weekday()):
            record, _ = AttendanceRecord.objects.get_or_create(
                session_term=term,
                class_model=entry.class_model,
                date=today,
                timetable_entry=entry,
            )
            for student in entry.class_model.students.filter(status="enrolled"):
                StudentAttendance.objects.get_or_create(
                    attendance_record=record,
                    student=student,
                    defaults={"status": "present"},
                )

        schedule, _ = Schedule.objects.get_or_create(
            schedule_type="exam",
            start_date=today,
            end_date=today + timedelta(days=4),
            defaults={"is_active": True},
        )
        for class_obj in Class.objects.all()[:6]:
            subject = Subject.objects.filter(class_model=class_obj).first()
            if not subject:
                continue
            entry = ScheduleEntry.objects.filter(
                schedule=schedule,
                date=today + timedelta(days=1),
                start_time=time(9, 0),
                title=f"{subject.name} Exam",
            ).first()
            if entry is None:
                entry = ScheduleEntry.objects.create(
                    schedule=schedule,
                    date=today + timedelta(days=1),
                    start_time=time(9, 0),
                    end_time=time(11, 0),
                    title=f"{subject.name} Exam",
                    linked_subject=subject,
                )
            entry.target_classes.add(class_obj)

        self.stdout.write(self.style.SUCCESS("  timetable, attendance, and schedule ready"))

    def seed_assignments(self, teachers):
        teacher = teachers[0] if teachers else Staff.objects.first()
        if not teacher:
            return

        subject = Subject.objects.filter(assigned_teachers=teacher).first() or Subject.objects.first()
        if not subject:
            return

        assignment, _ = Assignment.objects.get_or_create(
            title=f"{subject.name} Demo Assignment",
            subject=subject,
            class_model=subject.class_model,
            defaults={
                "staff": teacher,
                "description": "Answer the attached practice questions.",
                "due_date": timezone.now() + timedelta(days=7),
                "is_published": True,
            },
        )
        questions = Question.objects.filter(subject=subject, is_verified=True)[:5]
        if questions:
            assignment.questions.set(questions)
        self.stdout.write(self.style.SUCCESS("  assignment ready"))

    def seed_result_pin(self, admin, students, session, term):
        student = next((s for s in students if s.user and s.user.email == "student14@test.com"), None)
        if not student:
            return

        fee = FeeType.objects.filter(school=student.school, name="Result PIN").first()
        purpose = PaymentPurpose.objects.filter(code="result_pin").first()
        if not fee:
            return

        payment, _ = FeePayment.objects.get_or_create(
            reference_number=f"DEMO-RESULTPIN-{student.id}",
            defaults={
                "student": student,
                "fee_type": fee,
                "amount": fee.amount,
                "payment_purpose": purpose,
                "session": session,
                "session_term": term,
                "payment_method": "online",
                "notes": "Demo result PIN payment",
                "processed_by": admin,
            },
        )
        ResultPin.objects.update_or_create(
            payment=payment,
            defaults={
                "pin": "DEMORESULT14",
                "serial_number": "0000000014",
                "student": student,
                "session": session,
                "session_term": term,
                "is_used": False,
            },
        )

        subject = Subject.objects.filter(class_model=student.class_model).first()
        exam = subject.exams.filter(status="active").first() if subject else None
        if exam:
            hall = ExamHall.objects.filter(is_active=True).first()
            code, _ = CBTExamCode.objects.get_or_create(
                code="DEMO14",
                defaults={
                    "student": student,
                    "exam": exam,
                    "exam_hall": hall,
                    "seat_number": 14,
                    "expires_at": timezone.now() + timedelta(days=30),
                    "access_start_datetime": timezone.now() - timedelta(days=1),
                    "access_end_datetime": timezone.now() + timedelta(days=30),
                    "created_by": admin,
                },
            )
            code.student = student
            code.exam = exam
            code.expires_at = timezone.now() + timedelta(days=30)
            code.access_start_datetime = timezone.now() - timedelta(days=1)
            code.access_end_datetime = timezone.now() + timedelta(days=30)
            code.created_by = code.created_by or admin
            code.save()

        self.stdout.write(self.style.SUCCESS("  result PIN and CBT code ready"))

    def print_summary(self):
        summary = {
            "users": User.objects.count(),
            "staff": Staff.objects.count(),
            "students": Student.objects.count(),
            "schools": School.objects.count(),
            "classes": Class.objects.count(),
            "subjects": Subject.objects.count(),
            "topics": Topic.objects.count(),
            "questions": Question.objects.count(),
            "exams": Exam.objects.count(),
            "fees": FeeType.objects.count(),
            "payments": FeePayment.objects.count(),
            "timetable_entries": TimetableEntry.objects.count(),
        }
        self.stdout.write(self.style.SUCCESS("Demo seed complete."))
        for key, value in summary.items():
            self.stdout.write(f"  {key}: {value}")
        self.stdout.write("Shortcut logins:")
        self.stdout.write("  Admin: admin@gmail.com / mtn*556#")
        self.stdout.write("  Teacher: oluwaseun.adebayo@shininglightschools.com / password123")
        self.stdout.write("  Student: student14@test.com / password123")
        self.stdout.write("  Result PIN: DEMORESULT14")
        self.stdout.write("  CBT code: DEMO14")
