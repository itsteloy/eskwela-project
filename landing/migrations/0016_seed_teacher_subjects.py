# Generated manually — seed existing teachers with the full subject catalog

from django.db import migrations


def seed_teacher_subjects(apps, schema_editor):
    Teacher = apps.get_model("landing", "Teacher")
    TeacherSubject = apps.get_model("landing", "TeacherSubject")
    subjects = [
        "Communication Skills",
        "Critical Thinking",
        "Mathematics",
        "Science",
        "Social Studies",
        "Life Skills",
        "Filipino",
        "English",
    ]
    for teacher in Teacher.objects.all():
        for subject in subjects:
            TeacherSubject.objects.get_or_create(
                teacher=teacher,
                subject=subject,
                defaults={"grade_level": "All Levels"},
            )


def unseed_teacher_subjects(apps, schema_editor):
    TeacherSubject = apps.get_model("landing", "TeacherSubject")
    TeacherSubject.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0015_teachersubject"),
    ]

    operations = [
        migrations.RunPython(seed_teacher_subjects, unseed_teacher_subjects),
    ]
