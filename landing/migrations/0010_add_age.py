"""Add age field to StudentProfile.

Manual migration adding `age` as nullable IntegerField so existing
SQLite DB gains the column without altering data.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0009_add_extension_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="age",
            field=models.IntegerField(blank=True, null=True, verbose_name="Age"),
        ),
    ]
