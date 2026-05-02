from decimal import Decimal

import pytest

from api.models import (
    BioData,
    Class,
    Grade,
    School,
    Session,
    SessionTerm,
    Student,
    StudentSubject,
    Subject,
    TermReport,
)


@pytest.fixture
def result_school():
    return School.objects.create(
        name="Result Percentage School",
        school_type="Primary",
        ca_max_score=10,
        exam_max_score=40,
    )


@pytest.fixture
def result_session():
    return Session.objects.create(
        name="2027/2028",
        start_date="2027-09-01",
        end_date="2028-07-31",
        is_current=True,
    )


@pytest.fixture
def result_term(result_session):
    term, _ = SessionTerm.objects.get_or_create(
        session=result_session,
        term_name="1st Term",
        defaults={
            "start_date": "2027-09-01",
            "end_date": "2027-12-20",
            "is_current": True,
        },
    )
    return term


@pytest.fixture
def result_student(test_user, result_school):
    class_model = Class.objects.create(
        name="Primary 5A",
        class_code="PRY5A",
        school=result_school,
        order=1,
    )
    student = Student.objects.create(
        id="STU-PCT-001",
        application_number="APP-PCT-001",
        user=test_user,
        school=result_school,
        class_model=class_model,
        admission_number="PCT001",
        status="enrolled",
        source="admin_registration",
    )
    BioData.objects.create(
        student=student,
        surname="Percent",
        first_name="Student",
        gender="male",
        date_of_birth="2012-01-01",
        state_of_origin="Lagos",
        permanent_address="1 Percent Street",
    )
    return student


@pytest.fixture
def result_subject(result_student):
    return Subject.objects.create(
        name="Mathematics",
        school=result_student.school,
        class_model=result_student.class_model,
        order=1,
    )


@pytest.mark.django_db
def test_term_report_average_uses_percentage_not_raw_total(
    result_student,
    result_subject,
    result_session,
    result_term,
):
    StudentSubject.objects.create(
        student=result_student,
        subject=result_subject,
        session=result_session,
        session_term=result_term,
        ca_score=Decimal("5.00"),
        objective_score=Decimal("10.00"),
        theory_score=Decimal("10.00"),
    )

    report = TermReport.objects.get(
        student=result_student,
        session=result_session,
        session_term=result_term,
    )

    assert report.total_score == Decimal("25.00")
    assert report.average_score == Decimal("50.00")


@pytest.mark.django_db
def test_subject_grade_uses_normalized_percentage(
    result_student,
    result_subject,
    result_session,
    result_term,
):
    grade = Grade.objects.create(
        grade_letter="A",
        grade_name="A",
        grade_description="Excellent",
        min_score=Decimal("50.00"),
        max_score=Decimal("100.00"),
    )

    subject_registration = StudentSubject.objects.create(
        student=result_student,
        subject=result_subject,
        session=result_session,
        session_term=result_term,
        ca_score=Decimal("5.00"),
        objective_score=Decimal("10.00"),
        theory_score=Decimal("10.00"),
    )

    assert subject_registration.total_score == Decimal("25.00")
    assert subject_registration.grade == grade
