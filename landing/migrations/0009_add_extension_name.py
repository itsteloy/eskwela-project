"""Add extension_name field to StudentProfile.

Manual migration adding `extension_name` as nullable CharField to avoid
OperationalError on existing SQLite DB.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0008_add_registration_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="extension_name",
            field=models.CharField(
                blank=True,
                max_length=50,
                null=True,
                verbose_name="Extension Name (Jr., III, etc.)",
            ),
        ),
    ]
