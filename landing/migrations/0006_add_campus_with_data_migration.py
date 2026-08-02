from django.db import migrations, models
import django.db.models.deletion


def create_campuses_from_existing_data(apps, schema_editor):
    """Create Campus records from existing string values in all tables"""
    # These will be available after CreateModel operation
    Campus = apps.get_model("landing", "Campus")
    StudentProfile = apps.get_model("landing", "StudentProfile")
    Teacher = apps.get_model("landing", "Teacher")
    Schedule = apps.get_model("landing", "Schedule")
    LearningModule = apps.get_model("landing", "LearningModule")
    Announcement = apps.get_model("landing", "Announcement")
    Assignment = apps.get_model("landing", "Assignment")

    # Collect all unique campus names from all tables
    campus_names = set()

    # Get from StudentProfile
    for student in StudentProfile.objects.exclude(campus__isnull=True).exclude(
        campus=""
    ):
        if student.campus:
            campus_names.add(student.campus)

    # Get from Teacher
    for teacher in Teacher.objects.exclude(campus__isnull=True).exclude(campus=""):
        if teacher.campus:
            campus_names.add(teacher.campus)

    # Get from Schedule
    for schedule in Schedule.objects.exclude(campus__isnull=True).exclude(campus=""):
        if schedule.campus:
            campus_names.add(schedule.campus)

    # Get from LearningModule
    for module in LearningModule.objects.exclude(campus__isnull=True).exclude(
        campus=""
    ):
        if module.campus:
            campus_names.add(module.campus)

    # Get from Announcement
    for announcement in Announcement.objects.exclude(campus__isnull=True).exclude(
        campus=""
    ):
        if announcement.campus:
            campus_names.add(announcement.campus)

    # Get from Assignment
    for assignment in Assignment.objects.exclude(campus__isnull=True).exclude(
        campus=""
    ):
        if assignment.campus:
            campus_names.add(assignment.campus)

    # Create Campus objects for each unique name
    campus_map = {}
    print("Creating campuses from existing data...")
    for name in campus_names:
        if name and name.strip():  # Skip empty strings
            # Generate code from name
            code = name.upper().replace(" ", "_").replace("-", "_").replace(".", "")
            campus, created = Campus.objects.get_or_create(
                name=name.strip(), defaults={"code": code, "is_active": True}
            )
            campus_map[name] = campus.id
            if created:
                print(f"  Created campus: {name} -> ID: {campus.id}")
            else:
                print(f"  Found existing campus: {name} -> ID: {campus.id}")

    return campus_map


def update_foreign_keys(apps, schema_editor):
    """Update all foreign keys to point to the correct Campus IDs"""
    Campus = apps.get_model("landing", "Campus")
    StudentProfile = apps.get_model("landing", "StudentProfile")
    Teacher = apps.get_model("landing", "Teacher")
    Schedule = apps.get_model("landing", "Schedule")
    LearningModule = apps.get_model("landing", "LearningModule")
    Announcement = apps.get_model("landing", "Announcement")
    Assignment = apps.get_model("landing", "Assignment")

    # Create a mapping of campus names to IDs
    campus_map = {campus.name: campus.id for campus in Campus.objects.all()}
    print(f"\nUpdating foreign keys using campus map: {campus_map}")

    # Update StudentProfile
    updated_count = 0
    for student in StudentProfile.objects.all():
        old_campus = student.campus
        if old_campus and old_campus in campus_map:
            student.campus_id = campus_map[old_campus]
            student.save()
            updated_count += 1
    print(f"  Updated {updated_count} StudentProfile records")

    # Update Teacher
    updated_count = 0
    for teacher in Teacher.objects.all():
        old_campus = teacher.campus
        if old_campus and old_campus in campus_map:
            teacher.campus_id = campus_map[old_campus]
            teacher.save()
            updated_count += 1
    print(f"  Updated {updated_count} Teacher records")

    # Update Schedule
    updated_count = 0
    for schedule in Schedule.objects.all():
        old_campus = schedule.campus
        if old_campus and old_campus in campus_map:
            schedule.campus_id = campus_map[old_campus]
            schedule.save()
            updated_count += 1
    print(f"  Updated {updated_count} Schedule records")

    # Update LearningModule
    updated_count = 0
    for module in LearningModule.objects.all():
        old_campus = module.campus
        if old_campus and old_campus in campus_map:
            module.campus_id = campus_map[old_campus]
            module.save()
            updated_count += 1
    print(f"  Updated {updated_count} LearningModule records")

    # Update Announcement
    updated_count = 0
    for announcement in Announcement.objects.all():
        old_campus = announcement.campus
        if old_campus and old_campus in campus_map:
            announcement.campus_id = campus_map[old_campus]
            announcement.save()
            updated_count += 1
    print(f"  Updated {updated_count} Announcement records")

    # Update Assignment
    updated_count = 0
    for assignment in Assignment.objects.all():
        old_campus = assignment.campus
        if old_campus and old_campus in campus_map:
            assignment.campus_id = campus_map[old_campus]
            assignment.save()
            updated_count += 1
    print(f"  Updated {updated_count} Assignment records")


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0005_announcement_assignment_assignmentsubmission"),
    ]

    operations = [
        # 1. FIRST: Create Campus model
        migrations.CreateModel(
            name="Campus",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=100, unique=True, verbose_name="Campus Name"
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        null=True,
                        unique=True,
                        verbose_name="Campus Code",
                    ),
                ),
                (
                    "address",
                    models.TextField(
                        blank=True, null=True, verbose_name="Campus Address"
                    ),
                ),
                (
                    "contact_number",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        null=True,
                        verbose_name="Contact Number",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Active")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Campus",
                "verbose_name_plural": "Campuses",
                "ordering": ["name"],
            },
        ),
        # 2. THEN: Create campuses from existing data
        migrations.RunPython(create_campuses_from_existing_data),
        # 3. NOW: Add temporary columns for the new foreign keys
        migrations.AddField(
            model_name="studentprofile",
            name="campus_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="students_temp",
                to="landing.campus",
                verbose_name="Campus",
            ),
        ),
        migrations.AddField(
            model_name="teacher",
            name="campus_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="teachers_temp",
                to="landing.campus",
                verbose_name="Campus",
            ),
        ),
        migrations.AddField(
            model_name="schedule",
            name="campus_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="schedules_temp",
                to="landing.campus",
                verbose_name="Campus",
            ),
        ),
        migrations.AddField(
            model_name="learningmodule",
            name="campus_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="learning_modules_temp",
                to="landing.campus",
                verbose_name="Campus",
            ),
        ),
        migrations.AddField(
            model_name="announcement",
            name="campus_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="announcements_temp",
                to="landing.campus",
                verbose_name="Campus",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="campus_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assignments_temp",
                to="landing.campus",
                verbose_name="Campus",
            ),
        ),
        # 4. Copy data to new columns
        migrations.RunPython(update_foreign_keys),
        # 5. Remove old campus fields
        migrations.RemoveField(
            model_name="studentprofile",
            name="campus",
        ),
        migrations.RemoveField(
            model_name="teacher",
            name="campus",
        ),
        migrations.RemoveField(
            model_name="schedule",
            name="campus",
        ),
        migrations.RemoveField(
            model_name="learningmodule",
            name="campus",
        ),
        migrations.RemoveField(
            model_name="announcement",
            name="campus",
        ),
        migrations.RemoveField(
            model_name="assignment",
            name="campus",
        ),
        # 6. Rename new columns to original names
        migrations.RenameField(
            model_name="studentprofile",
            old_name="campus_new",
            new_name="campus",
        ),
        migrations.RenameField(
            model_name="teacher",
            old_name="campus_new",
            new_name="campus",
        ),
        migrations.RenameField(
            model_name="schedule",
            old_name="campus_new",
            new_name="campus",
        ),
        migrations.RenameField(
            model_name="learningmodule",
            old_name="campus_new",
            new_name="campus",
        ),
        migrations.RenameField(
            model_name="announcement",
            old_name="campus_new",
            new_name="campus",
        ),
        migrations.RenameField(
            model_name="assignment",
            old_name="campus_new",
            new_name="campus",
        ),
    ]
