from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0099_sessionterm_rankings_calculated_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("passport", "Passport Photograph"),
                            ("nin", "NIN / National ID"),
                            ("certificate", "Educational Certificate"),
                            ("trcn", "TRCN / Teaching License"),
                            ("school_result", "School Result"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("document_file", models.FileField(upload_to="staff/documents/%Y/%m/%d/")),
                (
                    "label",
                    models.CharField(
                        blank=True,
                        help_text='Optional free-text label, e.g. "B.Ed Education" or "NYSC Certificate".',
                        max_length=120,
                    ),
                ),
                ("verified", models.BooleanField(default=False)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "staff",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="staff_documents",
                        to="api.staff",
                    ),
                ),
                (
                    "verified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="staff_documents_verified",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "staff_documents",
                "ordering": ["-uploaded_at"],
            },
        ),
        migrations.CreateModel(
            name="StaffChangeRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "change_type",
                    models.CharField(
                        choices=[
                            ("profile_field", "Profile Field"),
                            ("document_upload", "Document Uploaded"),
                            ("document_replace", "Document Replaced"),
                            ("document_delete", "Document Deleted"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "field_name",
                    models.CharField(
                        blank=True,
                        help_text="Profile field name, or document type for document changes.",
                        max_length=80,
                    ),
                ),
                ("old_value", models.TextField(blank=True)),
                ("new_value", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending_review", "Pending Review"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending_review",
                        max_length=20,
                    ),
                ),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True)),
                (
                    "staff",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="change_requests",
                        to="api.staff",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="change_requests",
                        to="api.staffdocument",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="staff_changes_reviewed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "staff_change_requests",
                "ordering": ["-submitted_at"],
                "indexes": [
                    models.Index(fields=["status", "-submitted_at"], name="staff_chang_status_b46612_idx"),
                    models.Index(fields=["staff", "-submitted_at"], name="staff_chang_staff_i_801d93_idx"),
                ],
            },
        ),
    ]
