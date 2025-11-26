from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0030_cbtexamcode'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='allow_calculator',
            field=models.BooleanField(
                default=False,
                help_text='Allow students to open the calculator tool during the exam',
                verbose_name='allow calculator',
            ),
        ),
    ]

