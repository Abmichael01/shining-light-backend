import pytest
from unittest.mock import patch
from django.urls import reverse
from api.models import (
    School, Student, Session, SessionTerm, 
    SystemSetting, ResultPin, FeePayment, FeeType,
    BioData, TermReport, Class
)
from decimal import Decimal

@pytest.fixture
def school():
    return School.objects.create(name="Test School", code="TS")

@pytest.fixture
def session():
    return Session.objects.create(name="2023/2024", start_date="2023-09-01", end_date="2024-07-31", is_current=True)

@pytest.fixture
def term(session):
    # Session.objects.create already creates '1st Term' via signal/save.
    # We just need to ensure it has the right dates if we were to create it manually,
    # but here we'll just fetch or update it.
    term, created = SessionTerm.objects.get_or_create(
        session=session, 
        term_name="1st Term",
        defaults={
            'start_date': "2023-09-01",
            'end_date': "2023-12-20",
            'is_current': True
        }
    )
    if not created:
        term.is_current = True
        term.save()
    return term

@pytest.fixture
def student_profile(test_user, school, session, term):
    # Student has a required class_model field, find/create one.
    klass = Class.objects.create(name="JS 1A", school=school, order=1)
    
    student = Student.objects.create(
        id="STU-001",
        application_number="APP-001",
        user=test_user,
        school=school,
        class_model=klass,
        admission_number="20240001",
        status='enrolled',
        source='admin_registration'
    )
    biodata = BioData.objects.create(
        student=student,
        surname="Student",
        first_name="Test",
        gender="male",
        date_of_birth="2010-01-01",
        state_of_origin="Lagos",
        permanent_address="123 Test St"
    )
    return student

@pytest.fixture
def pin_price_setting():
    setting = SystemSetting.load()
    setting.result_pin_price = Decimal("1000.00")
    setting.save()
    return setting

@pytest.mark.django_db
class TestResultPinSystem:
    
    @patch('api.utils.paystack.Paystack.initialize_transaction')
    def test_initialize_pin_purchase(self, mock_init, authenticated_client, student_profile, pin_price_setting):
        mock_init.return_value = {
            'authorization_url': 'http://test.com',
            'access_code': 'test_code'
        }
        url = reverse('api:fee-payment-initialize-pin-purchase')
        response = authenticated_client.post(url)
        
        assert response.status_code == 200
        assert 'authorization_url' in response.data
        assert 'reference' in response.data
        assert float(response.data['amount']) == 1000.0

    @patch('api.utils.paystack.Paystack.verify_transaction')
    def test_verify_pin_purchase_creates_pin(self, mock_verify, authenticated_client, student_profile, pin_price_setting):
        reference = "TEST_REF"
        mock_verify.return_value = {
            'status': 'success',
            'amount': 100000, # Paystack sends in kobo
            'metadata': {
                'is_pin_purchase': True,
                'student_id': student_profile.id,
            }
        }
        
        url = reverse('api:fee-payment-verify-payment')
        response = authenticated_client.post(url, {'reference': reference})
        
        assert response.status_code == 200
        assert response.data['status'] == 'success'
        assert 'pin' in response.data
        
        # Verify database
        assert ResultPin.objects.filter(student=student_profile).exists()
        assert FeePayment.objects.filter(reference_number=reference).exists()

    def test_validate_pin_success(self, authenticated_client, student_profile, session, term):
        # Setup a report and a PIN
        report = TermReport.objects.create(
            student=student_profile,
            session=session,
            session_term=term,
            total_score=85.5
        )
        
        # Create a dummy payment and PIN manually for the test
        fee_type = FeeType.objects.create(name="Manual PIN Fee", school=student_profile.school, amount=1000)
        payment = FeePayment.objects.create(
            student=student_profile,
            fee_type=fee_type,
            amount=1000,
            reference_number="MANUAL_REF",
            payment_method="manual",
            session=session,
            session_term=term
        )
        pin_record = ResultPin.objects.create(payment=payment, student=student_profile)
        
        url = reverse('api:result-pin-validate')
        data = {
            'pin': pin_record.pin,
            'student_id': student_profile.id,
            'session_id': session.id,
            'term_id': term.id
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == 200
        assert response.data['message'] == 'PIN validated successfully.'
        assert 'report' in response.data
        
        # Check PIN is marked as used
        pin_record.refresh_from_db()
        assert pin_record.is_used is True
        assert pin_record.session == session
        assert pin_record.session_term == term

    def test_validate_pin_one_time_use(self, authenticated_client, student_profile, session, term):
        # Create a PIN and mark it as used
        fee_type = FeeType.objects.create(name="Used PIN Fee", school=student_profile.school, amount=1000)
        payment = FeePayment.objects.create(student=student_profile, fee_type=fee_type, amount=1000, reference_number="REF1", payment_method="manual")
        pin_record = ResultPin.objects.create(payment=payment, student=student_profile, is_used=True)
        
        url = reverse('api:result-pin-validate')
        data = {
            'pin': pin_record.pin,
            'student_id': student_profile.id,
            'session_id': session.id,
            'term_id': term.id
        }
        
        response = authenticated_client.post(url, data)
        assert response.status_code == 400
        assert "already used" in response.data['error'].lower()

    def test_validate_pin_wrong_student(self, authenticated_client, student_profile, session, term, create_user, school):
        # Create another student
        klass = Class.objects.first() # Reuse existing class
        other_user = create_user(email="other@example.com")
        other_student = Student.objects.create(
            id="STU-002",
            application_number="APP-002",
            user=other_user, 
            school=school, 
            class_model=klass,
            admission_number="20240002",
            status='enrolled',
            source='admin_registration'
        )
        BioData.objects.create(
            student=other_student, 
            surname="Other", 
            first_name="Student", 
            gender="female", 
            date_of_birth="2010-01-01",
            state_of_origin="Lagos",
            permanent_address="456 Test St"
        )
        
        # Authenticated student tries to use a PIN belonging to 'other_student'
        fee_type = FeeType.objects.create(name="Other PIN Fee", school=school, amount=1000)
        payment = FeePayment.objects.create(student=other_student, fee_type=fee_type, amount=1000, reference_number="REF2", payment_method="manual")
        pin_record = ResultPin.objects.create(payment=payment, student=other_student)
        
        url = reverse('api:result-pin-validate')
        data = {
            'pin': pin_record.pin,
            'student_id': student_profile.id, # Logged in student ID
            'session_id': session.id,
            'term_id': term.id
        }
        
        response = authenticated_client.post(url, data)
        assert response.status_code == 403
        assert "not purchased for this student" in response.data['error'].lower()
