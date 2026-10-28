from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator


# Shared ALS subject catalog (used by modules, assignments, and enrollments)
SUBJECT_CHOICES = [
    ("Communication Skills", "Communication Skills"),
    ("Critical Thinking", "Critical Thinking"),
    ("Mathematics", "Mathematics"),
    ("Science", "Science"),
    ("Social Studies", "Social Studies"),
    ("Life Skills", "Life Skills"),
    ("Filipino", "Filipino"),
    ("English", "English"),
]


# DepEd primary subject catalog (Grade 1 - Grade 6)
PRIMARY_SUBJECT_CHOICES = [
    ("Mother Tongue", "Mother Tongue"),
    ("Filipino", "Filipino"),
    ("English", "English"),
    ("Mathematics", "Mathematics"),
    ("Science", "Science"),
    ("Araling Panlipunan", "Araling Panlipunan"),
    ("Edukasyon sa Pagpapakatao", "Edukasyon sa Pagpapakatao"),
    ("MAPEH", "MAPEH"),
    ("EPP", "EPP"),
]

# Combined catalog accepted at the DB level (grade-specific filtering happens in views)
ALL_SUBJECT_CHOICES = SUBJECT_CHOICES + [
    choice for choice in PRIMARY_SUBJECT_CHOICES if choice not in SUBJECT_CHOICES
]

PRIMARY_GRADES = ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6"]

SECONDARY_GRADES = [
    "Grade 7",
    "Grade 8",
    "Grade 9",
    "Grade 10",
    "Grade 11",
    "Grade 12",
]

ALL_GRADES = PRIMARY_GRADES + SECONDARY_GRADES


def is_primary_grade(grade):
    """Return True when a grade string belongs to Primary (Grade 1-6)."""
    return grade in PRIMARY_GRADES


def subjects_for_grade(grade):
    """Return the subject catalog applicable to a grade level."""
    if is_primary_grade(grade):
        return PRIMARY_SUBJECT_CHOICES
    return SUBJECT_CHOICES


def grade_audience_key(grade):
    """Map 'Grade 1' -> 'grade_1' for announcement targeting."""
    if not grade:
        return ""
    return grade.lower().replace(" ", "_")


class StudentProfile(models.Model):
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
        ("Prefer not to say", "Prefer not to say"),
    ]

    GRADE_CHOICES = [
        ("Grade 1", "Grade 1"),
        ("Grade 2", "Grade 2"),
        ("Grade 3", "Grade 3"),
        ("Grade 4", "Grade 4"),
        ("Grade 5", "Grade 5"),
        ("Grade 6", "Grade 6"),
        ("Grade 7", "Grade 7"),
        ("Grade 8", "Grade 8"),
        ("Grade 9", "Grade 9"),
        ("Grade 10", "Grade 10"),
        ("Grade 11", "Grade 11"),
        ("Grade 12", "Grade 12"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    CAMPUS_CHOICES = [
        ("Panabo Park", "Panabo Park"),
        ("BJMP-Salvacion", "BJMP-Salvacion"),
        ("St. Joseph-Pagasa", "St. Joseph-Pagasa"),
        ("St. Therese Crisis Center", "St. Therese Crisis Center"),
        ("E Learning Center", "E Learning Center"),
        ("BFAR Cagangohan", "BFAR Cagangohan"),
        ("Southern Davao", "Southern Davao"),
    ]

    # Basic User Relationship
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )

    # Registration Information
    registration_date = models.DateField(
        null=True, blank=True, verbose_name="Date of Registration"
    )

    # Personal Information
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    extension_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Extension Name (Jr., III, etc.)",
    )
    birthdate = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True, verbose_name="Age")
    gender = models.CharField(
        max_length=20, choices=GENDER_CHOICES, blank=True, null=True
    )
    place_of_birth = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Place of Birth"
    )
    civil_status = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Civil Status"
    )
    religion = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Religion"
    )
    mother_tongue = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Mother Tongue"
    )

    # Indigenous People Information
    is_indigenous_people = models.BooleanField(
        default=False, verbose_name="Indigenous People"
    )
    indigenous_specify = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="IP Community Name"
    )

    # 4Ps Information
    is_4ps_beneficiary = models.BooleanField(
        default=False, verbose_name="4Ps Beneficiary"
    )
    fourps_household_id = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="4Ps Household ID"
    )

    # Contact Information
    phone = models.CharField(max_length=20, blank=True, null=True)
    contact_numbers = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Additional Contact Numbers"
    )

    # Address Information
    street_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Street Name"
    )
    province = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Province"
    )
    municipality = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Municipality/City"
    )
    barangay = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Barangay"
    )
    zip_code = models.CharField(
        max_length=4, blank=True, null=True, verbose_name="Zip Code"
    )
    address = models.TextField(blank=True, null=True)  # Keep for compatibility

    # Permanent Address (if different)
    same_address = models.BooleanField(
        default=True, verbose_name="Same as Current Address"
    )
    permanent_street_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Permanent Street Name"
    )
    permanent_province = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Permanent Province"
    )
    permanent_municipality = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Permanent Municipality/City",
    )
    permanent_barangay = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Permanent Barangay"
    )
    permanent_zip_code = models.CharField(
        max_length=4, blank=True, null=True, verbose_name="Permanent Zip Code"
    )

    # Educational Information - PWD
    is_pwd = models.BooleanField(default=False, verbose_name="Person with Disability")
    has_pwd_id = models.BooleanField(default=False, verbose_name="Has PWD ID")
    disability_types = models.TextField(
        blank=True, null=True, verbose_name="Disability Types"
    )  # Store as comma-separated
    disability_subtypes = models.TextField(
        blank=True, null=True, verbose_name="Disability Subtypes"
    )  # Store as comma-separated

    # Last Grade Level Completed
    last_grade_levels = models.TextField(
        blank=True, null=True, verbose_name="Last Grade Levels Completed"
    )  # Store as comma-separated

    # ALS Attendance History
    attended_als_before = models.BooleanField(
        default=False, verbose_name="Attended ALS Before"
    )
    als_programs = models.TextField(
        blank=True, null=True, verbose_name="ALS Programs Attended"
    )  # Store as comma-separated
    als_completed = models.BooleanField(
        default=False, verbose_name="Completed ALS Program"
    )
    als_not_completed_reason = models.TextField(
        blank=True, null=True, verbose_name="Reason for Not Completing ALS"
    )

    # Reasons for Not Attending School
    reasons_not_schooling = models.TextField(
        blank=True, null=True, verbose_name="Reasons for Not Attending School"
    )  # Store as comma-separated
    reason_not_schooling_other = models.TextField(
        blank=True, null=True, verbose_name="Other Reason for Not Schooling"
    )

    # Learning Center Accessibility
    learning_center_distance = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Distance to Learning Center",
    )
    learning_center_transport = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Mode of Transportation"
    )
    learning_center_transport_other = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Other Transportation"
    )
    travel_time = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Travel Time"
    )

    # Weekly Availability
    availability_monday = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Monday Availability"
    )
    availability_tuesday = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Tuesday Availability"
    )
    availability_wednesday = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Wednesday Availability"
    )
    availability_thursday = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Thursday Availability"
    )
    availability_friday = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Friday Availability"
    )
    availability_saturday = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Saturday Availability"
    )
    availability_sunday = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Sunday Availability"
    )

    # Parent/Guardian Information
    father_first_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Father's First Name"
    )
    father_middle_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Father's Middle Name"
    )
    father_last_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Father's Last Name"
    )

    mother_first_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Mother's First Name"
    )
    mother_middle_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Mother's Middle Name"
    )
    mother_last_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Mother's Last Name"
    )

    guardian_first_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Guardian's First Name"
    )
    guardian_middle_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Guardian's Middle Name"
    )
    guardian_last_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Guardian's Last Name"
    )

    # Learning Modalities
    learning_modalities = models.TextField(
        blank=True, null=True, verbose_name="Preferred Learning Modalities"
    )  # Store as comma-separated
    criteria_plan = models.TextField(
        blank=True, null=True, verbose_name="Criteria to Apply For"
    )  # Store as comma-separated

    # Campus and Enrollment
    campus = models.ForeignKey(
        "Campus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
        verbose_name="Campus",
    )
    enrolled_in = models.CharField(
        max_length=20, choices=GRADE_CHOICES, blank=True, null=True
    )

    # Documents
    lrn = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        validators=[
            RegexValidator(regex=r"^\d{12}$", message="LRN must be exactly 12 digits.")
        ],
        verbose_name="Learner Reference Number (LRN)",
    )
    birth_certificate = models.FileField(
        upload_to="documents/birth_certificates/%Y/%m/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])],
        verbose_name="Scanned Birth Certificate",
    )
    valid_id = models.FileField(
        upload_to="documents/valid_ids/%Y/%m/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])],
        verbose_name="Scanned Valid ID",
    )
    documents_verified = models.BooleanField(
        default=False, verbose_name="Documents Verified"
    )
    documents_uploaded_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Documents Uploaded At"
    )

    REQUIREMENT_STATUS_CHOICES = [
        ("not_available", "Not Available"),
        ("completed", "Completed"),
    ]
    bc_status = models.CharField(
        max_length=20,
        choices=REQUIREMENT_STATUS_CHOICES,
        default="not_available",
        verbose_name="Birth Certificate Status",
    )
    vid_status = models.CharField(
        max_length=20,
        choices=REQUIREMENT_STATUS_CHOICES,
        default="not_available",
        verbose_name="Valid ID Status",
    )

    # Status and Timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.status}"

    def get_assigned_teacher(self):
        try:
            from .models import Teacher

            return Teacher.objects.get(campus=self.campus)
        except Teacher.DoesNotExist:
            return None
        except Exception:
            return None

    def has_uploaded_documents(self):
        return bool(self.birth_certificate or self.valid_id)

    def get_document_status(self):
        status = []
        if self.birth_certificate:
            status.append("✓ Birth Certificate")
        if self.valid_id:
            status.append("✓ Valid ID")
        if self.lrn:
            status.append("✓ LRN")
        return status if status else ["No documents uploaded"]

    def get_document_count(self):
        """Get the number of documents uploaded"""
        count = 0
        if self.lrn:
            count += 1
        if self.birth_certificate:
            count += 1
        if self.valid_id:
            count += 1
        return count

    def enrolled_subjects(self):
        """Return list of active subject names this student is enrolled in."""
        return list(
            self.subject_enrollments.filter(is_active=True).values_list(
                "subject", flat=True
            )
        )


class Teacher(models.Model):
    CAMPUS_CHOICES = [
        ("Panabo Park", "Panabo Park"),
        ("BJMP-Salvacion", "BJMP-Salvacion"),
        ("St. Joseph-Pagasa", "St. Joseph-Pagasa"),
        ("St. Therese Crisis Center", "St. Therese Crisis Center"),
        ("E Learning Center", "E Learning Center"),
        ("BFAR Cagangohan", "BFAR Cagangohan"),
        ("Southern Davao", "Southern Davao"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="teacher_profile"
    )
    campus = models.ForeignKey(
        "Campus",
        on_delete=models.CASCADE,
        related_name="teachers",
        verbose_name="Campus",
        limit_choices_to={"is_active": True},
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        campus_name = self.campus.name if self.campus else "No Campus"
        return f"{self.user.get_full_name()} - {campus_name}"


class Schedule(models.Model):
    """Schedule model for teacher-created class schedules"""

    DAYS_OF_WEEK = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    ]

    GRADE_LEVEL_CHOICES = [
        ("All Levels", "All Levels"),
        ("Grade 1", "Grade 1"),
        ("Grade 2", "Grade 2"),
        ("Grade 3", "Grade 3"),
        ("Grade 4", "Grade 4"),
        ("Grade 5", "Grade 5"),
        ("Grade 6", "Grade 6"),
        ("Grade 7", "Grade 7"),
        ("Grade 8", "Grade 8"),
        ("Grade 9", "Grade 9"),
        ("Grade 10", "Grade 10"),
        ("Grade 11", "Grade 11"),
        ("Grade 12", "Grade 12"),
    ]

    teacher = models.ForeignKey(
        "Teacher",
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name="Teacher",
    )
    campus = models.ForeignKey(
        "Campus",
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name="Campus",
        null=True,
        blank=True,
    )
    day_of_week = models.CharField(
        max_length=10, choices=DAYS_OF_WEEK, verbose_name="Day of Week"
    )
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    subject = models.CharField(max_length=100, verbose_name="Subject/Learning Area")
    grade_level = models.CharField(
        max_length=20,
        choices=GRADE_LEVEL_CHOICES,
        default="All Levels",
        verbose_name="Grade Level",
    )
    room = models.CharField(max_length=50, blank=True, verbose_name="Room/Location")
    notes = models.TextField(blank=True, verbose_name="Additional Notes")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        verbose_name = "Schedule"
        verbose_name_plural = "Schedules"
        unique_together = ["teacher", "day_of_week", "start_time", "room"]

    def __str__(self):
        return f"{self.teacher.user.get_full_name()} - {self.day_of_week} {self.start_time}"


class LearningModule(models.Model):
    """Model for storing learning modules uploaded by teachers"""

    GRADE_LEVEL_CHOICES = [
        ("All Levels", "All Levels"),
        ("Grade 1", "Grade 1"),
        ("Grade 2", "Grade 2"),
        ("Grade 3", "Grade 3"),
        ("Grade 4", "Grade 4"),
        ("Grade 5", "Grade 5"),
        ("Grade 6", "Grade 6"),
        ("Grade 7", "Grade 7"),
        ("Grade 8", "Grade 8"),
        ("Grade 9", "Grade 9"),
        ("Grade 10", "Grade 10"),
        ("Grade 11", "Grade 11"),
        ("Grade 12", "Grade 12"),
    ]

    SUBJECT_CHOICES = ALL_SUBJECT_CHOICES

    QUARTER_CHOICES = [
        ("Quarter 1", "Quarter 1"),
        ("Quarter 2", "Quarter 2"),
        ("Quarter 3", "Quarter 3"),
        ("Quarter 4", "Quarter 4"),
    ]

    teacher = models.ForeignKey(
        "Teacher", on_delete=models.CASCADE, related_name="modules"
    )
    campus = models.ForeignKey(
        "Campus",
        on_delete=models.CASCADE,
        related_name="modules",
        verbose_name="Campus",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200, verbose_name="Module Title")
    description = models.TextField(verbose_name="Description")
    subject = models.CharField(
        max_length=50, choices=ALL_SUBJECT_CHOICES, default="Other", verbose_name="Subject"
    )
    grade_level = models.CharField(
        max_length=20, choices=GRADE_LEVEL_CHOICES, default="All Levels"
    )
    quarter = models.CharField(
        max_length=20,
        choices=QUARTER_CHOICES,
        default="Quarter 1",
        verbose_name="Quarter",
        blank=True,
    )
    file = models.FileField(
        upload_to="modules/%Y/%m/",
        validators=[
            FileExtensionValidator(["pdf", "doc", "docx", "ppt", "pptx", "zip"])
        ],
        blank=True,
        null=True,
    )
    file_size = models.FloatField(default=0, verbose_name="File Size (KB)")
    thumbnail = models.ImageField(upload_to="module_thumbnails/", blank=True, null=True)
    download_count = models.IntegerField(default=0, verbose_name="Download Count")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Learning Module"
        verbose_name_plural = "Learning Modules"

    def __str__(self):
        return f"{self.title} - {self.grade_level}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size / 1024
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ["KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            if unit != "GB":
                self.file_size /= 1024.0
        return "0 B"

    def increment_download_count(self):
        """Increment download count when module is downloaded"""
        self.download_count += 1
        self.save(update_fields=["download_count"])


class ModuleAccess(models.Model):
    """Track which students have accessed which modules"""

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="accessed_modules"
    )
    module = models.ForeignKey(
        LearningModule, on_delete=models.CASCADE, related_name="accessed_by"
    )
    accessed_at = models.DateTimeField(auto_now_add=True)
    downloaded = models.BooleanField(default=False)

    class Meta:
        unique_together = ["student", "module"]
        verbose_name = "Module Access"
        verbose_name_plural = "Module Accesses"


class Announcement(models.Model):
    """Model for teacher announcements"""

    AUDIENCE_CHOICES = [
        ("all", "All Students"),
        ("grade_1", "Grade 1 Only"),
        ("grade_2", "Grade 2 Only"),
        ("grade_3", "Grade 3 Only"),
        ("grade_4", "Grade 4 Only"),
        ("grade_5", "Grade 5 Only"),
        ("grade_6", "Grade 6 Only"),
        ("grade_7", "Grade 7 Only"),
        ("grade_8", "Grade 8 Only"),
        ("grade_9", "Grade 9 Only"),
        ("grade_10", "Grade 10 Only"),
        ("grade_11", "Grade 11 Only"),
        ("grade_12", "Grade 12 Only"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    teacher = models.ForeignKey(
        "Teacher", on_delete=models.CASCADE, related_name="announcements"
    )
    campus = models.ForeignKey(
        "Campus",
        on_delete=models.CASCADE,
        related_name="announcements",
        verbose_name="Campus",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200, verbose_name="Title")
    content = models.TextField(verbose_name="Content")
    audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default="all",
        verbose_name="Target Audience",
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
        verbose_name="Priority",
    )
    attachment = models.FileField(
        upload_to="announcements/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Attachment",
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d')}"

    def get_audience_display(self):
        return dict(self.AUDIENCE_CHOICES).get(self.audience, "All Students")


class Assignment(models.Model):
    """Model for teacher assignments"""

    GRADE_LEVEL_CHOICES = [
        ("Grade 1", "Grade 1"),
        ("Grade 2", "Grade 2"),
        ("Grade 3", "Grade 3"),
        ("Grade 4", "Grade 4"),
        ("Grade 5", "Grade 5"),
        ("Grade 6", "Grade 6"),
        ("Grade 7", "Grade 7"),
        ("Grade 8", "Grade 8"),
        ("Grade 9", "Grade 9"),
        ("Grade 10", "Grade 10"),
        ("Grade 11", "Grade 11"),
        ("Grade 12", "Grade 12"),
    ]

    SUBJECT_CHOICES = ALL_SUBJECT_CHOICES

    teacher = models.ForeignKey(
        "Teacher", on_delete=models.CASCADE, related_name="assignments"
    )
    campus = models.ForeignKey(
        "Campus",
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="Campus",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200, verbose_name="Title")
    description = models.TextField(verbose_name="Description")
    subject = models.CharField(
        max_length=50, choices=ALL_SUBJECT_CHOICES, default="Other", verbose_name="Subject"
    )
    grade_level = models.CharField(
        max_length=20, choices=GRADE_LEVEL_CHOICES, verbose_name="Grade Level"
    )
    due_date = models.DateTimeField(verbose_name="Due Date")
    total_points = models.IntegerField(default=100, verbose_name="Total Points")
    attachment = models.FileField(
        upload_to="assignments/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Assignment File",
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"

    def __str__(self):
        return f"{self.title} - {self.grade_level}"

    @property
    def is_past_due(self):
        from django.utils import timezone

        return timezone.now() > self.due_date


class AssignmentSubmission(models.Model):
    """Model for student assignment submissions"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("submitted", "Submitted"),
        ("late", "Late"),
        ("graded", "Graded"),
    ]

    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="submissions"
    )
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="submissions"
    )
    submission_file = models.FileField(
        upload_to="submissions/%Y/%m/%d/", verbose_name="Submission File"
    )
    comments = models.TextField(blank=True, verbose_name="Student Comments")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="submitted"
    )
    grade = models.IntegerField(null=True, blank=True, verbose_name="Grade")
    feedback = models.TextField(blank=True, verbose_name="Teacher Feedback")
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        unique_together = ["assignment", "student"]

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.assignment.title}"

    def save(self, *args, **kwargs):
        if self.grade is not None and self.status != "graded":
            self.status = "graded"
            from django.utils import timezone

            self.graded_at = timezone.now()
        super().save(*args, **kwargs)


class SubjectEnrollment(models.Model):
    """Admin-managed enrollment of a student into a specific subject."""

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="subject_enrollments",
    )
    subject = models.CharField(
        max_length=50, choices=ALL_SUBJECT_CHOICES, verbose_name="Subject"
    )
    enrolled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subject_enrollments_made",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        unique_together = ["student", "subject"]
        ordering = ["subject"]
        verbose_name = "Subject Enrollment"
        verbose_name_plural = "Subject Enrollments"

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject}"


class TeacherSubject(models.Model):
    """Subjects a teacher has added to their teaching list."""

    GRADE_LEVEL_CHOICES = [
        ("All Levels", "All Levels"),
        ("Grade 1", "Grade 1"),
        ("Grade 2", "Grade 2"),
        ("Grade 3", "Grade 3"),
        ("Grade 4", "Grade 4"),
        ("Grade 5", "Grade 5"),
        ("Grade 6", "Grade 6"),
        ("Grade 7", "Grade 7"),
        ("Grade 8", "Grade 8"),
        ("Grade 9", "Grade 9"),
        ("Grade 10", "Grade 10"),
        ("Grade 11", "Grade 11"),
        ("Grade 12", "Grade 12"),
    ]

    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name="teacher_subjects"
    )
    subject = models.CharField(
        max_length=50, choices=ALL_SUBJECT_CHOICES, verbose_name="Subject"
    )
    grade_level = models.CharField(
        max_length=20,
        choices=GRADE_LEVEL_CHOICES,
        default="All Levels",
        verbose_name="Grade Level",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["teacher", "subject"]
        ordering = ["subject"]
        verbose_name = "Teacher Subject"
        verbose_name_plural = "Teacher Subjects"

    def __str__(self):
        return f"{self.teacher.user.get_full_name()} - {self.subject}"


class Campus(models.Model):
    """Model for managing campuses dynamically"""

    name = models.CharField(max_length=100, unique=True, verbose_name="Campus Name")
    code = models.CharField(
        max_length=20, unique=True, verbose_name="Campus Code", blank=True, null=True
    )
    address = models.TextField(blank=True, null=True, verbose_name="Campus Address")
    contact_number = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Contact Number"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Campus"
        verbose_name_plural = "Campuses"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name.upper().replace(" ", "_")
        super().save(*args, **kwargs)
