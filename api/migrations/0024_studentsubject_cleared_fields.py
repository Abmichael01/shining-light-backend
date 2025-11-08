from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0023_remove_staff_school"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentsubject",
            name="cleared",
            field=models.BooleanField(default=False, verbose_name="cleared"),
        ),
        migrations.AddField(
            model_name="studentsubject",
            name="cleared_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="cleared at"),
        ),
        migrations.AddField(
            model_name="studentsubject",
            name="cleared_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="student_subjects_cleared",
                to="api.user",
                verbose_name="cleared by",
            ),
        ),
    ]
