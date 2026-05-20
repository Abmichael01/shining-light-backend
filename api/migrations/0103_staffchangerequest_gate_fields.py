# Hand-written migration: adds is_gated + applied_at columns and the
# (staff, status, is_gated) index to support the hybrid approval-gate model
# for staff profile edits. Existing rows are treated as audit-only
# (is_gated=False) which matches their previous behaviour.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0102_staffchangerequest_education_staffeducation_verified_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffchangerequest",
            name="is_gated",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "True means the Staff record was NOT updated yet — admin "
                    "approval is required to apply new_value. False means the "
                    "change was applied immediately and this row is audit-only."
                ),
            ),
        ),
        migrations.AddField(
            model_name="staffchangerequest",
            name="applied_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When new_value was actually written to the Staff record.",
            ),
        ),
        migrations.AddIndex(
            model_name="staffchangerequest",
            index=models.Index(
                fields=["staff", "status", "is_gated"],
                name="staff_chang_staff_i_gated_idx",
            ),
        ),
    ]
