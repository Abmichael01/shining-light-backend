from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse

from api.models import BioData, Class, FeePayment, FeeType, School, Session, SessionTerm, Student


@pytest.fixture
def school():
    return School.objects.create(name="Receipt Test School", school_type="Primary")


@pytest.fixture
def session():
    return Session.objects.create(
        name="2026/2027",
        start_date="2026-09-01",
        end_date="2027-07-31",
        is_current=True,
    )


@pytest.fixture
def term(session):
    term, _ = SessionTerm.objects.get_or_create(
        session=session,
        term_name="1st Term",
        defaults={
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "is_current": True,
        },
    )
    term.is_current = True
    term.save()
    return term


@pytest.fixture
def student_profile(test_user, school):
    class_model = Class.objects.create(
        name="Primary 4A",
        class_code="PRY4A",
        school=school,
        order=1,
    )
    student = Student.objects.create(
        id="STU-RCP-001",
        application_number="APP-RCP-001",
        user=test_user,
        school=school,
        class_model=class_model,
        admission_number="20260001",
        status="enrolled",
        source="admin_registration",
    )
    BioData.objects.create(
        student=student,
        surname="Receipt",
        first_name="Student",
        gender="male",
        date_of_birth="2012-01-01",
        state_of_origin="Lagos",
        permanent_address="1 Receipt Street",
    )
    return student


@pytest.fixture
def fee_type(student_profile):
    fee = FeeType.objects.create(
        name="Tuition Receipt Fee",
        school=student_profile.school,
        amount=Decimal("6000.00"),
        is_active=True,
        is_mandatory=True,
    )
    fee.applicable_classes.add(student_profile.class_model)
    return fee


@pytest.fixture
def fee_payment(student_profile, fee_type, session, term):
    return FeePayment.objects.create(
        student=student_profile,
        fee_type=fee_type,
        amount=Decimal("6000.00"),
        session=session,
        session_term=term,
        payment_method="online",
        reference_number="TREF-RECEIPT-001",
        notes="Paystack Ref: TREF-RECEIPT-001",
    )


def find_fee(response_data, fee_type):
    return next(
        item for item in response_data
        if item["fee_type_id"] == fee_type.id
    )


@pytest.mark.django_db
def test_student_fees_returns_nested_receipts_for_logged_in_student(
    authenticated_client,
    fee_type,
    fee_payment,
):
    response = authenticated_client.get(reverse("api:fee-payment-student-fees"))

    assert response.status_code == 200
    fee_status = find_fee(response.data, fee_type)
    assert fee_status["status"] == "paid"
    assert fee_status["amount_paid"] == "6000.00"
    assert len(fee_status["payments"]) == 1
    assert fee_status["payments"][0]["id"] == fee_payment.id
    assert fee_status["payments"][0]["receipt_number"] == fee_payment.receipt_number
    assert fee_status["payments"][0]["reference_number"] == "TREF-RECEIPT-001"


@pytest.mark.django_db
def test_admin_can_fetch_selected_student_receipts_with_session_aliases(
    api_client,
    admin_user,
    student_profile,
    fee_type,
    fee_payment,
    session,
    term,
):
    api_client.force_authenticate(user=admin_user)
    response = api_client.get(
        reverse("api:fee-payment-student-fees"),
        {
            "student": student_profile.id,
            "session": session.id,
            "session_term": term.id,
        },
    )

    assert response.status_code == 200
    fee_status = find_fee(response.data, fee_type)
    assert len(fee_status["payments"]) == 1
    assert fee_status["payments"][0]["receipt_number"] == fee_payment.receipt_number


@pytest.mark.django_db
def test_payment_list_and_student_fees_expose_same_payment(
    api_client,
    admin_user,
    student_profile,
    fee_type,
    fee_payment,
    session,
    term,
):
    api_client.force_authenticate(user=admin_user)

    list_response = api_client.get(
        reverse("api:fee-payment-list"),
        {"student": student_profile.id, "page_size": 1000},
    )
    student_fees_response = api_client.get(
        reverse("api:fee-payment-student-fees"),
        {
            "student": student_profile.id,
            "session_id": session.id,
            "term_id": term.id,
        },
    )

    assert list_response.status_code == 200
    assert student_fees_response.status_code == 200

    list_payment_ids = {payment["id"] for payment in list_response.data["results"]}
    fee_status = find_fee(student_fees_response.data, fee_type)
    student_fee_payment_ids = {payment["id"] for payment in fee_status["payments"]}

    assert fee_payment.id in list_payment_ids
    assert fee_payment.id in student_fee_payment_ids


@pytest.mark.django_db
@patch("api.views.fee.paystack.Paystack.initialize_transaction")
def test_initialize_payment_sends_selected_session_and_term_to_paystack(
    mock_initialize_transaction,
    authenticated_client,
    fee_type,
    session,
    term,
):
    mock_initialize_transaction.return_value = {
        "authorization_url": "https://paystack.test/pay",
        "access_code": "access-code",
    }

    response = authenticated_client.post(
        reverse("api:fee-payment-initialize-payment"),
        {
            "fee_type_id": fee_type.id,
            "amount": "6000.00",
            "session_id": session.id,
            "term_id": term.id,
        },
        format="json",
    )

    assert response.status_code == 200
    metadata = mock_initialize_transaction.call_args.kwargs["metadata"]
    assert metadata["session_id"] == session.id
    assert metadata["term_id"] == term.id


@pytest.mark.django_db
@patch("api.views.fee.paystack.Paystack.verify_transaction")
def test_verify_payment_records_selected_session_and_term_from_paystack_metadata(
    mock_verify_transaction,
    authenticated_client,
    student_profile,
    fee_type,
    session,
    term,
):
    reference = "TREF-SELECTED-001"
    mock_verify_transaction.return_value = {
        "status": "success",
        "amount": 600000,
        "metadata": {
            "fee_type_id": fee_type.id,
            "student_id": student_profile.id,
            "session_id": session.id,
            "term_id": term.id,
        },
    }

    response = authenticated_client.post(
        reverse("api:fee-payment-verify-payment"),
        {"reference": reference},
        format="json",
    )

    assert response.status_code == 200
    payment = FeePayment.objects.get(reference_number=reference)
    assert payment.session_id == session.id
    assert payment.session_term_id == term.id
