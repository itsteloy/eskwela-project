# landing/context_processors.py
from .models import Campus, StudentProfile, AssignmentSubmission, Announcement
from django.db.models import Q


def campuses(request):
    """Add campuses to all templates"""
    return {"all_campuses": Campus.objects.filter(is_active=True).order_by("name")}


def student_notifications(request):
    """Add student notification counts to all templates"""
    context = {
        "pending_assignments_count": 0,
        "graded_submissions_count": 0,
        "pending_announcements_count": 0,
    }

    # Only process if user is authenticated and is a student
    if request.user.is_authenticated and not request.user.is_staff:
        try:
            student_profile = request.user.student_profile

            # Get pending assignments count
            if student_profile.enrolled_in and student_profile.campus:
                from .models import Assignment, AssignmentSubmission

                # Get assignments for this student's grade and campus
                assignments = Assignment.objects.filter(
                    campus=student_profile.campus,
                    grade_level=student_profile.enrolled_in,
                    is_active=True,
                )

                # Get submitted assignment IDs
                submitted_ids = AssignmentSubmission.objects.filter(
                    student=student_profile
                ).values_list("assignment_id", flat=True)

                # Pending = total assignments not yet submitted
                context["pending_assignments_count"] = assignments.exclude(
                    id__in=submitted_ids
                ).count()

                # Get graded submissions count
                context["graded_submissions_count"] = (
                    AssignmentSubmission.objects.filter(
                        student=student_profile, status="graded"
                    ).count()
                )

                # Get pending announcements for this student
                grade_mapping = {
                    "Grade 1": "grade_1",
                    "Grade 2": "grade_2",
                    "Grade 3": "grade_3",
                    "Grade 4": "grade_4",
                    "Grade 5": "grade_5",
                    "Grade 6": "grade_6",
                    "Grade 7": "grade_7",
                    "Grade 8": "grade_8",
                    "Grade 9": "grade_9",
                    "Grade 10": "grade_10",
                    "Grade 11": "grade_11",
                    "Grade 12": "grade_12",
                }
                grade_audience = grade_mapping.get(student_profile.enrolled_in, "")

                recent_announcements = (
                    Announcement.objects.filter(
                        campus=student_profile.campus,
                        is_active=True,
                    )
                    .filter(Q(audience="all") | Q(audience=grade_audience))
                    .order_by("-created_at")
                )

                # Could add logic here to count "new" announcements if you track that
                # For now, we'll just count urgent + high priority ones
                context["pending_announcements_count"] = recent_announcements.filter(
                    Q(priority="urgent") | Q(priority="high")
                ).count()

        except StudentProfile.DoesNotExist:
            pass

    return context
