"""End-to-end tests for the hybrid staff profile approval gate.

What we're protecting:
  * High-risk fields (bank, identity, phone) MUST NOT touch the Staff record
    until an admin approves.
  * Low-risk fields apply immediately and produce an audit row.
  * Admin doc endpoints are direct (no review queue, docs land verified).

If any of these break, payroll could pay the wrong account or admins could
silently lose review control. So these are integration tests, not unit
tests — they go through the real serializer + view + url stack.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from api.models import Staff, StaffChangeRequest, StaffDocument

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def staff_owner_user(create_user):
    """The User the Staff record belongs to (the one editing their profile)."""
    return create_user(
        email='owner@example.com',
        password='ownerpass123',
        user_type='staff',
        is_staff=True,
    )


@pytest.fixture
def school_admin_user(create_user):
    """An admin who reviews the change requests."""
    return create_user(
        email='reviewer@example.com',
        password='reviewerpass123',
        user_type='admin',
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def staff_record(staff_owner_user):
    """A baseline Staff record with sensible defaults so we can mutate it."""
    return Staff.objects.create(
        user=staff_owner_user,
        title='mr',
        surname='Original',
        first_name='Adebayo',
        other_names='',
        nationality='Nigerian',
        state_of_origin='Lagos',
        date_of_birth='1990-01-15',
        permanent_address='1 Test Street',
        phone_number='08011111111',
        marital_status='single',
        religion='christian',
        zone='ransowa',
        staff_type='teaching',
        account_name='Old Name',
        account_number='0000000000',
        bank_name='Old Bank',
    )


@pytest.fixture
def staff_client(staff_owner_user):
    # Build a fresh APIClient per role so authenticating one doesn't override
    # the other — important for tests that need both staff and admin acting
    # in the same scenario.
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=staff_owner_user)
    return client


@pytest.fixture
def admin_client(school_admin_user):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=school_admin_user)
    return client


# ---------------------------------------------------------------------------
# 1. The core invariant — high-risk PATCH is gated, low-risk is not
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGateBehavior:
    """Verifies the hybrid model — high-risk does NOT mutate Staff at PATCH;
    low-risk does."""

    def test_bank_account_change_does_not_apply_immediately(self, staff_client, staff_record):
        """If this regresses, payroll could pay the wrong account."""
        original_account = staff_record.account_number

        response = staff_client.patch(
            '/api/staff-portal/me/',
            {'account_number': '9999999999'},
            format='json',
        )

        assert response.status_code == 200
        staff_record.refresh_from_db()
        assert staff_record.account_number == original_account, (
            'High-risk field was applied immediately — gate is broken!'
        )

        # A gated change request should exist
        cr = StaffChangeRequest.objects.get(
            staff=staff_record,
            field_name='account_number',
            status='pending_review',
        )
        assert cr.is_gated is True
        assert cr.applied_at is None
        assert cr.old_value == original_account
        assert cr.new_value == '9999999999'

    def test_address_change_applies_immediately(self, staff_client, staff_record):
        """Low-risk field — should land on the record at PATCH time."""
        response = staff_client.patch(
            '/api/staff-portal/me/',
            {'permanent_address': '42 New Avenue'},
            format='json',
        )

        assert response.status_code == 200
        staff_record.refresh_from_db()
        assert staff_record.permanent_address == '42 New Avenue'

        cr = StaffChangeRequest.objects.get(
            staff=staff_record,
            field_name='permanent_address',
        )
        assert cr.is_gated is False
        assert cr.applied_at is not None

    def test_mixed_edit_splits_correctly(self, staff_client, staff_record):
        """A single PATCH containing both tiers should apply low-risk and
        gate high-risk in one round-trip."""
        original_phone = staff_record.phone_number

        response = staff_client.patch(
            '/api/staff-portal/me/',
            {
                'permanent_address': '42 New Avenue',  # low-risk
                'phone_number': '08099999999',          # high-risk
            },
            format='json',
        )

        assert response.status_code == 200
        staff_record.refresh_from_db()
        assert staff_record.permanent_address == '42 New Avenue'
        assert staff_record.phone_number == original_phone, 'Phone should NOT be applied'

        gated = StaffChangeRequest.objects.get(
            staff=staff_record, field_name='phone_number'
        )
        assert gated.is_gated is True
        assert gated.applied_at is None

        applied = StaffChangeRequest.objects.get(
            staff=staff_record, field_name='permanent_address'
        )
        assert applied.is_gated is False
        assert applied.applied_at is not None

    def test_unchanged_value_creates_no_row(self, staff_client, staff_record):
        """PATCH with the same value should be a no-op (no audit, no gate)."""
        before_count = StaffChangeRequest.objects.filter(staff=staff_record).count()

        response = staff_client.patch(
            '/api/staff-portal/me/',
            {'phone_number': staff_record.phone_number},
            format='json',
        )

        assert response.status_code == 200
        after_count = StaffChangeRequest.objects.filter(staff=staff_record).count()
        assert after_count == before_count


# ---------------------------------------------------------------------------
# 2. Conflict policy — second edit to same field overwrites pending
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConflictPolicy:
    """We picked latest-wins as the conflict policy — the second edit
    overwrites the pending value, but old_value stays anchored to the
    original (so admin sees original → latest, not stale → latest)."""

    def test_second_edit_overwrites_pending(self, staff_client, staff_record):
        original_account = staff_record.account_number

        staff_client.patch(
            '/api/staff-portal/me/', {'account_number': '1111111111'}, format='json',
        )
        staff_client.patch(
            '/api/staff-portal/me/', {'account_number': '2222222222'}, format='json',
        )

        pending = StaffChangeRequest.objects.filter(
            staff=staff_record,
            field_name='account_number',
            status='pending_review',
        )
        assert pending.count() == 1, 'Second edit should overwrite, not append'

        cr = pending.first()
        assert cr.old_value == original_account, 'old_value must remain the real original'
        assert cr.new_value == '2222222222'

        staff_record.refresh_from_db()
        assert staff_record.account_number == original_account


# ---------------------------------------------------------------------------
# 3. Approve actually mutates the Staff record now
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApproveApplies:
    """Approving a gated change must finally write to Staff. This was the
    main bug in the previous design."""

    def test_approve_writes_value_to_staff(self, staff_client, admin_client, staff_record):
        staff_client.patch(
            '/api/staff-portal/me/', {'phone_number': '08099999999'}, format='json',
        )

        cr = StaffChangeRequest.objects.get(
            staff=staff_record, field_name='phone_number', status='pending_review',
        )
        response = admin_client.post(f'/api/staff-changes/{cr.pk}/approve/', {}, format='json')

        assert response.status_code == 200
        cr.refresh_from_db()
        staff_record.refresh_from_db()
        assert cr.status == 'approved'
        assert cr.applied_at is not None
        assert cr.reviewed_by_id is not None
        assert staff_record.phone_number == '08099999999'

    def test_reject_does_not_touch_staff(self, staff_client, admin_client, staff_record):
        original_account = staff_record.account_number
        staff_client.patch(
            '/api/staff-portal/me/', {'account_number': '9999999999'}, format='json',
        )

        cr = StaffChangeRequest.objects.get(
            staff=staff_record, field_name='account_number', status='pending_review',
        )
        response = admin_client.post(
            f'/api/staff-changes/{cr.pk}/reject/',
            {'notes': 'Wrong bank, please re-submit'},
            format='json',
        )

        assert response.status_code == 200
        cr.refresh_from_db()
        staff_record.refresh_from_db()
        assert cr.status == 'rejected'
        assert cr.review_notes == 'Wrong bank, please re-submit'
        # The whole point of the gate: rejection leaves the record clean.
        assert staff_record.account_number == original_account


# ---------------------------------------------------------------------------
# 4. Pending changes exposed on the profile API for the frontend badge
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPendingChangesExposed:
    def test_pending_changes_appears_on_me_endpoint(self, staff_client, staff_record):
        staff_client.patch(
            '/api/staff-portal/me/', {'phone_number': '08099999999'}, format='json',
        )

        response = staff_client.get('/api/staff-portal/me/')
        assert response.status_code == 200
        pending = response.data.get('pending_changes', {})
        assert 'phone_number' in pending
        assert pending['phone_number']['new_value'] == '08099999999'
        assert pending['phone_number']['submitted_at'] is not None

    def test_pending_changes_clears_after_approve(self, staff_client, admin_client, staff_record):
        staff_client.patch(
            '/api/staff-portal/me/', {'phone_number': '08099999999'}, format='json',
        )
        cr = StaffChangeRequest.objects.get(
            staff=staff_record, field_name='phone_number', status='pending_review',
        )
        admin_client.post(f'/api/staff-changes/{cr.pk}/approve/', {}, format='json')

        response = staff_client.get('/api/staff-portal/me/')
        assert 'phone_number' not in response.data.get('pending_changes', {})


# ---------------------------------------------------------------------------
# 5. Admin docs endpoint — bypasses gate, lands verified
# ---------------------------------------------------------------------------

def _fake_file(name='nin.pdf', content=b'%PDF-1.4 dummy'):
    return SimpleUploadedFile(name, content, content_type='application/pdf')


@pytest.mark.django_db
class TestAdminDocsEndpoint:
    def test_admin_upload_lands_verified_no_change_request(self, admin_client, staff_record, school_admin_user):
        before_changes = StaffChangeRequest.objects.filter(staff=staff_record).count()

        response = admin_client.post(
            f'/api/staff/{staff_record.pk}/documents/',
            {
                'document_type': 'nin',
                'label': 'NIN Slip',
                'document_file': _fake_file(),
            },
            format='multipart',
        )

        assert response.status_code == 201, response.content
        doc_id = response.data['id']
        doc = StaffDocument.objects.get(pk=doc_id)
        assert doc.verified is True
        assert doc.verified_by_id == school_admin_user.id
        assert doc.verified_at is not None

        after_changes = StaffChangeRequest.objects.filter(staff=staff_record).count()
        assert after_changes == before_changes, (
            'Admin uploads must NOT create change requests — admin is the authority.'
        )

    def test_admin_delete_skips_change_request(self, admin_client, staff_record):
        # seed a doc directly
        doc = StaffDocument.objects.create(
            staff=staff_record,
            document_type='nin',
            document_file=_fake_file(),
            verified=True,
        )
        before = StaffChangeRequest.objects.filter(staff=staff_record).count()

        response = admin_client.delete(f'/api/staff/{staff_record.pk}/documents/{doc.pk}/')
        assert response.status_code == 204
        assert not StaffDocument.objects.filter(pk=doc.pk).exists()

        after = StaffChangeRequest.objects.filter(staff=staff_record).count()
        assert after == before

    def test_staff_cannot_hit_admin_docs_endpoint(self, staff_client, staff_record):
        """The admin endpoint should be off-limits to a non-admin staff user."""
        response = staff_client.get(f'/api/staff/{staff_record.pk}/documents/')
        assert response.status_code in (401, 403), (
            f'Staff user must not access admin docs endpoint, got {response.status_code}'
        )


# ---------------------------------------------------------------------------
# 6. Reject after approve is rejected (state machine integrity)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStateMachine:
    def test_cannot_approve_twice(self, staff_client, admin_client, staff_record):
        staff_client.patch(
            '/api/staff-portal/me/', {'phone_number': '08099999999'}, format='json',
        )
        cr = StaffChangeRequest.objects.get(
            staff=staff_record, field_name='phone_number', status='pending_review',
        )
        first = admin_client.post(f'/api/staff-changes/{cr.pk}/approve/', {}, format='json')
        assert first.status_code == 200
        second = admin_client.post(f'/api/staff-changes/{cr.pk}/approve/', {}, format='json')
        assert second.status_code == 400
