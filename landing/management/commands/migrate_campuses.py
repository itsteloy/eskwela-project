from django.core.management.base import BaseCommand
from landing.models import (
    Campus,
    StudentProfile,
    Teacher,
    Schedule,
    LearningModule,
    Announcement,
    Assignment,
)


class Command(BaseCommand):
    help = "Migrate existing campus choices to dynamic Campus model"

    def handle(self, *args, **options):
        # Existing campus choices from your models
        CAMPUS_CHOICES = [
            ("Panabo Park", "Panabo Park"),
            ("BJMP-Salvacion", "BJMP-Salvacion"),
            ("St. Joseph-Pagasa", "St. Joseph-Pagasa"),
            ("St. Therese Crisis Center", "St. Therese Crisis Center"),
            ("E Learning Center", "E Learning Center"),
            ("BFAR Cagangohan", "BFAR Cagangohan"),
            ("Southern Davao", "Southern Davao"),
        ]

        # Create campuses from existing choices
        campus_map = {}
        for code, name in CAMPUS_CHOICES:
            campus, created = Campus.objects.get_or_create(
                name=name, defaults={"code": code.upper().replace(" ", "_")}
            )
            campus_map[name] = campus
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created campus: {name}"))

        # Migrate StudentProfile campuses
        for student in StudentProfile.objects.all():
            if student.campus and student.campus in campus_map:
                student.campus_new = campus_map[student.campus]
                student.save()

        self.stdout.write(self.style.SUCCESS("Successfully migrated campuses"))
