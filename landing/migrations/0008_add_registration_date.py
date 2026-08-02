"""Add registration_date field to StudentProfile.

This is a manual migration to add the nullable `registration_date` DateField
so the existing SQLite database gets the column without modifying other
pending model changes.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0007_studentprofile_birth_certificate_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="registration_date",
            field=models.DateField(
                blank=True, null=True, verbose_name="Date of Registration"
            ),
        ),
    ]
