from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from api.models import (
    BioData,
    Class,
    ResultScoreSubmission,
    School,
    Session,
    SessionTerm,
    Staff,
    Student,
    StudentSubject,
    Subject,
    SystemSetting,
)


@pytest.fixture
def score_sheet_school():
    return School.objects.create(
        name="Score Sheet School",
        school_type="Secondary",
        ca_max_score=40,
        exam_max_score=60,
    )


@pytest.fixture
def score_sheet_session():
    return Session.objects.create(
        name="2028/2029",
        start_date="2028-09-01",
        end_date="2029-07-31",
        is_current=True,
    )


@pytest.fixture
def score_sheet_term(score_sheet_session):
    term, _ = SessionTerm.objects.get_or_create(
        session=score_sheet_session,
        term_name="1st Term",
        defaults={
            "start_date": "2028-09-01",
            "end_date": "2028-12-20",
            "is_current": True,
        },
    )
    term.is_current = True
    term.save()
    return term


@pytest.fixture
def score_sheet_student(score_sheet_school):
    class_model = Class.objects.create(
        name="SS 1A",
        class_code="SS1A",
        school=score_sheet_school,
        order=1,
    )
    student = Student.objects.create(
        id="STU-SHEET-001",
        application_number="APP-SHEET-001",
        school=score_sheet_school,
        class_model=class_model,
        admission_number="ADM-SHEET-001",
        status="enrolled",
        source="admin_registration",
    )
    BioData.objects.create(
        student=student,
        surname="Sheet",
        first_name="Student",
        gender="female",
        date_of_birth="2012-01-01",
        state_of_origin="Lagos",
        permanent_address="1 Sheet Street",
    )
    return student


@pytest.fixture
def score_sheet_subject(score_sheet_student):
    return Subject.objects.create(
        name="Chemistry",
        school=score_sheet_student.school,
        class_model=score_sheet_student.class_model,
        order=1,
    )


@pytest.fixture
def assigned_staff(staff_user, score_sheet_school, score_sheet_subject):
    staff = Staff.objects.create(
        user=staff_user,
        title="mr",
        surname="Assigned",
        first_name="Teacher",
        state_of_origin="Lagos",
        date_of_birth="1990-01-01",
        permanent_address="1 Staff Street",
        phone_number="08030000000",
        marital_status="single",
        religion="christian",
        school=score_sheet_school,
        zone="ransowa",
        staff_type="teaching",
    )
    score_sheet_subject.assigned_teachers.add(staff)
    return staff


@pytest.fixture
def score_sheet_registration(score_sheet_student, score_sheet_subject, score_sheet_session, score_sheet_term):
    return StudentSubject.objects.create(
        student=score_sheet_student,
        subject=score_sheet_subject,
        session=score_sheet_session,
        session_term=score_sheet_term,
    )


@pytest.mark.django_db
def test_subject_score_sheet_list_returns_registered_student_fields(
    api_client,
    admin_user,
    score_sheet_registration,
    score_sheet_subject,
    score_sheet_session,
    score_sheet_term,
):
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(
        reverse("api:studentsubject-list"),
        {
            "subject": score_sheet_subject.id,
            "session": score_sheet_session.id,
            "session_term": score_sheet_term.id,
        },
    )

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["id"] == score_sheet_registration.id
    assert response.data[0]["student_admission_number"] == "ADM-SHEET-001"
    assert response.data[0]["student_full_name"] == "Sheet Student"


@pytest.mark.django_db
def test_bulk_update_scores_saves_split_scores(
    api_client,
    admin_user,
    score_sheet_registration,
    score_sheet_subject,
    score_sheet_session,
    score_sheet_term,
):
    api_client.force_authenticate(user=admin_user)

    response = api_client.post(
        reverse("api:studentsubject-bulk-update-scores"),
        {
            "subject": score_sheet_subject.id,
            "session": score_sheet_session.id,
            "session_term": score_sheet_term.id,
            "updates": [
                {
                    "id": score_sheet_registration.id,
                    "ca_score": "32.00",
                    "objective_score": "18.00",
                    "theory_score": "24.00",
                    "teacher_comment": "Good progress",
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 200
    score_sheet_registration.refresh_from_db()
    assert score_sheet_registration.ca_score == Decimal("32.00")
    assert score_sheet_registration.objective_score == Decimal("18.00")
    assert score_sheet_registration.theory_score == Decimal("24.00")
    assert score_sheet_registration.exam_score == Decimal("42.00")
    assert score_sheet_registration.total_score == Decimal("74.00")
    assert score_sheet_registration.teacher_comment == "Good progress"


@pytest.mark.django_db
def test_bulk_update_scores_rejects_ca_when_ca_editing_is_locked(
    api_client,
    admin_user,
    score_sheet_registration,
    score_sheet_subject,
    score_sheet_session,
    score_sheet_term,
):
    score_sheet_registration.ca_score = Decimal("10.00")
    score_sheet_registration.objective_score = Decimal("10.00")
    score_sheet_registration.theory_score = Decimal("10.00")
    score_sheet_registration.save()

    settings = SystemSetting.load()
    settings.allow_ca_score_editing = False
    settings.save()
    api_client.force_authenticate(user=admin_user)

    response = api_client.post(
        reverse("api:studentsubject-bulk-update-scores"),
        {
            "subject": score_sheet_subject.id,
            "session": score_sheet_session.id,
            "session_term": score_sheet_term.id,
            "updates": [
                {
                    "id": score_sheet_registration.id,
                    "ca_score": "12.00",
                    "objective_score": "20.00",
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 400
    score_sheet_registration.refresh_from_db()
    assert score_sheet_registration.ca_score == Decimal("10.00")
    assert score_sheet_registration.objective_score == Decimal("10.00")


@pytest.mark.django_db
def test_csv_upload_accepts_ca_objective_and_theory_columns(
    api_client,
    admin_user,
    score_sheet_registration,
    score_sheet_subject,
    score_sheet_session,
    score_sheet_term,
):
    api_client.force_authenticate(user=admin_user)
    csv_content = "\n".join([
        "SUBJECT: Chemistry",
        "CLASS: SS 1A",
        "",
        "S/N,Admission Number,Student Name,CA Score,Objective Score,Theory Score,Remark",
        '1,ADM-SHEET-001,Sheet Student,30,17,20,"Solid work"',
    ])
    upload = SimpleUploadedFile(
        "score-sheet.csv",
        csv_content.encode("utf-8"),
        content_type="text/csv",
    )

    response = api_client.post(
        reverse("api:studentsubject-upload-results-csv"),
        {
            "subject": score_sheet_subject.id,
            "session": score_sheet_session.id,
            "session_term": score_sheet_term.id,
            "file": upload,
        },
        format="multipart",
    )

    assert response.status_code == 200
    score_sheet_registration.refresh_from_db()
    assert score_sheet_registration.ca_score == Decimal("30.00")
    assert score_sheet_registration.objective_score == Decimal("17.00")
    assert score_sheet_registration.theory_score == Decimal("20.00")
    assert score_sheet_registration.exam_score == Decimal("37.00")
    assert score_sheet_registration.total_score == Decimal("67.00")
    assert score_sheet_registration.teacher_comment == "Solid work"


@pytest.mark.django_db
def test_teacher_score_entry_waits_for_admin_approval_when_required(
    api_client,
    staff_user,
    admin_user,
    assigned_staff,
    score_sheet_registration,
    score_sheet_subject,
    score_sheet_session,
    score_sheet_term,
):
    settings = SystemSetting.load()
    settings.require_result_entry_approval = True
    settings.save()

    api_client.force_authenticate(user=staff_user)
    response = api_client.post(
        reverse("api:studentsubject-bulk-update-scores"),
        {
            "subject": score_sheet_subject.id,
            "session": score_sheet_session.id,
            "session_term": score_sheet_term.id,
            "updates": [
                {
                    "id": score_sheet_registration.id,
                    "ca_score": "35.00",
                    "objective_score": "12.00",
                    "theory_score": "30.00",
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 200
    score_sheet_registration.refresh_from_db()
    assert score_sheet_registration.total_score is None

    submission = ResultScoreSubmission.objects.get(student_subject=score_sheet_registration)
    assert submission.status == "pending"
    assert submission.proposed_scores["ca_score"] == "35.00"

    api_client.force_authenticate(user=admin_user)
    approve_response = api_client.post(
        reverse("api:result-score-submission-approve", args=[submission.id])
    )

    assert approve_response.status_code == 200
    score_sheet_registration.refresh_from_db()
    submission.refresh_from_db()
    assert submission.status == "approved"
    assert score_sheet_registration.ca_score == Decimal("35.00")
    assert score_sheet_registration.exam_score == Decimal("42.00")
    assert score_sheet_registration.total_score == Decimal("77.00")
