from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
import traceback
from .models import (
    StudentProfile,
    Teacher,
    Announcement,
    Assignment,
    AssignmentSubmission,
    LearningModule,
    SubjectEnrollment,
    TeacherSubject,
    SUBJECT_CHOICES,
)
import random
import string
from django.utils import timezone
from .models import Schedule, Campus
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from datetime import datetime
import json
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum
import os
from django.conf import settings
from django.core.paginator import Paginator
from .models import LearningModule, ModuleAccess
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.template.loader import render_to_string
from django.contrib.admin.views.decorators import staff_member_required
from .realtime_events import broadcast_event


def generate_username(first_name, last_name):
    """Generate a unique username from first and last name"""
    base = f"{first_name.lower()}.{last_name.lower()}".replace(" ", "")
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1
    return username


def generate_password(length=10):
    """Generate a random secure password"""
    characters = string.ascii_letters + string.digits + "!@#$%"
    password = "".join(random.choice(characters) for i in range(length))
    return password


def send_approval_email(student_profile, password):
    """Send email notification with login credentials when student is approved"""
    subject = "Your Account has been Approved - CALLED School of Performing Arts"

    print(f"\n📧 === EMAIL DEBUG START ===")
    print(f"   To: {student_profile.user.email}")
    print(f"   From: {settings.DEFAULT_FROM_EMAIL}")
    print(f"   SMTP Host: {settings.EMAIL_HOST}")
    print(f"   SMTP User: {settings.EMAIL_HOST_USER}")

    campus_name = (
        student_profile.campus.name if student_profile.campus else "Not Assigned"
    )

    context = {
        "student_name": student_profile.user.get_full_name(),
        "username": student_profile.user.username,
        "password": password,
        "email": student_profile.user.email,
        "campus": campus_name,
        "login_url": "http://127.0.0.1:8000/student_login/",
    }

    print(f"   Rendering email template...")
    try:
        html_message = render_to_string("landing/approval_email.html", context)
        plain_message = strip_tags(html_message)
        print(f"   Template rendered OK (length: {len(html_message)})")
    except Exception as e:
        print(f"   ❌ Template render failed: {str(e)}")
        print(f"   Error: {traceback.format_exc()}")
        return False

    print(
        f"   Attempting SMTP connection to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}..."
    )
    try:
        from django.core.mail import get_connection

        connection = get_connection(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
        )
        connection.open()
        print(f"   SMTP connection opened OK")
        connection.close()
    except Exception as e:
        print(f"   ❌ SMTP connection failed: {str(e)}")
        print(f"   Error: {traceback.format_exc()}")
        return False

    print(f"   Sending email via send_mail...")
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [student_profile.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"   ✅ Email sent successfully to {student_profile.user.email}")
        print(f"📧 === EMAIL DEBUG END ===\n")
        return True
    except Exception as e:
        print(f"   ❌ send_mail failed: {str(e)}")
        print(f"   Error: {traceback.format_exc()}")
        print(f"📧 === EMAIL DEBUG END ===\n")
        return False


def send_rejection_email(student_profile):
    """Send email notification when student is rejected"""
    subject = "❌ Your Registration Status - CALLED School of Performing Arts"

    context = {
        "student_name": student_profile.user.get_full_name(),
    }

    html_message = render_to_string("landing/rejection_email.html", context)
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [student_profile.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Rejection email sent to {student_profile.user.email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send rejection email: {str(e)}")
        print(f"   Error details: {traceback.format_exc()}")
        return False


# ============================================
# PUBLIC PAGES (No Login Required)
# ============================================


def index(request):
    """Landing page"""
    return render(request, "landing/landing_page.html")


def admin_login(request):
    """Admin login page"""
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_dashboard")

    storage = messages.get_messages(request)
    # Force the storage to be marked as used
    for message in storage:
        # Iterate through to mark all as used
        pass
    storage.used = True

    # Also try to directly clear from session if possible
    if hasattr(request, "session"):
        # remove any stored messages in session to avoid showing stale warnings
        request.session.pop("_messages", None)

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            messages.success(
                request, f"Welcome back, {user.first_name or user.username}!"
            )

            # Redirect to next parameter if exists
            next_url = request.GET.get("next", "admin_dashboard")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid admin credentials.")
            return redirect("admin_login")

    return render(request, "landing/admin_login.html")


def student_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        print(f"🔐 Login attempt - Username: {username}")

        # Check if user exists
        try:
            user_exists = User.objects.get(username=username)
            print(f"   User found: {user_exists.username}")
            print(f"   User is_staff: {user_exists.is_staff}")
            print(f"   User is_active: {user_exists.is_active}")
        except User.DoesNotExist:
            print(f"   ❌ User does not exist: {username}")
            messages.error(request, "Invalid username or password.")
            return redirect("student_login")

        user = authenticate(request, username=username, password=password)
        print(f"   Authenticate result: {user}")

        if user is not None:
            # Check if student is approved
            try:
                profile = user.student_profile
                print(f"   Profile status: {profile.status}")

                if profile.status != "approved":
                    messages.error(
                        request,
                        "Your account is still pending approval. Please wait for admin approval.",
                    )
                    return redirect("student_login")
            except StudentProfile.DoesNotExist:
                # Create profile if it doesn't exist
                profile = StudentProfile.objects.create(user=user, status="pending")
                messages.error(
                    request,
                    "Your account is pending approval. Please wait for admin approval.",
                )
                return redirect("student_login")

            login(request, user)
            messages.success(
                request, f"Welcome back, {user.first_name or user.username}!"
            )
            return redirect("student_dashboard")
        else:
            print(f"   ❌ Authentication failed for {username}")
            messages.error(request, "Invalid username or password.")
            return redirect("student_login")

    return render(request, "landing/student_login.html")


@login_required
def edit_teacher(request, teacher_id):
    """Edit teacher information"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher = User.objects.get(id=teacher_id, is_staff=True, is_superuser=False)
        teacher_profile = teacher.teacher_profile
    except User.DoesNotExist:
        messages.error(request, "Teacher not found.")
        return redirect("teacher_management")

    if request.method == "POST":
        # Update user fields
        teacher.first_name = request.POST.get("first_name", teacher.first_name)
        teacher.last_name = request.POST.get("last_name", teacher.last_name)
        teacher.email = request.POST.get("email", teacher.email)
        teacher.save()

        # Update profile fields
        teacher_profile.phone = request.POST.get("phone", "")
        teacher_profile.save()

        messages.success(
            request, f"Teacher {teacher.get_full_name()} updated successfully."
        )
        return redirect("teacher_management")

    context = {
        "teacher": teacher,
        "profile": teacher_profile,
        "active_page": "teachers",
    }
    return render(request, "administrator/edit_teacher.html", context)


def register(request):
    """Student registration page with comprehensive ALS enrollment form"""
    if request.method == "POST":
        try:
            # ============================================
            # 1. BASIC INFORMATION
            # ============================================
            registration_date = request.POST.get("registration_date", "")
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            middle_name = request.POST.get("middle_name", "").strip()
            extension_name = request.POST.get("extension_name", "").strip()
            birthdate = request.POST.get("birthdate", "")
            age = request.POST.get("age", "")
            sex = request.POST.get("sex", "")
            place_of_birth = request.POST.get("place_of_birth", "").strip()
            civil_status = request.POST.get("civil_status", "")
            religion = request.POST.get("religion", "").strip()
            mother_tongue = request.POST.get("mother_tongue", "").strip()

            # Indigenous People
            indigenous_people = request.POST.get("indigenous_people", "No")
            indigenous_specify = request.POST.get("indigenous_specify", "").strip()

            # 4Ps Information
            is_4ps_beneficiary = request.POST.get("is_4ps_beneficiary", "No")
            fourps_household_id = request.POST.get("4ps_household_id", "").strip()

            # ============================================
            # 2. CONTACT INFORMATION
            # ============================================
            email = request.POST.get("email", "").strip()
            contact_numbers = request.POST.get("contact_numbers", "").strip()
            phone = contact_numbers.split(",")[0].strip() if contact_numbers else ""

            # ============================================
            # 3. ADDRESS INFORMATION
            # ============================================
            street_name = request.POST.get("street_name", "").strip()
            province = request.POST.get("province", "").strip()
            municipality = request.POST.get("municipality", "").strip()
            barangay = request.POST.get("barangay", "").strip()
            zip_code = request.POST.get("zip_code", "").strip()

            # Permanent Address
            same_address = request.POST.get("same_address", "Yes") == "Yes"
            permanent_street_name = request.POST.get(
                "permanent_street_name", ""
            ).strip()
            permanent_province = request.POST.get("permanent_province", "").strip()
            permanent_municipality = request.POST.get(
                "permanent_municipality", ""
            ).strip()
            permanent_barangay = request.POST.get("permanent_barangay", "").strip()
            permanent_zip_code = request.POST.get("permanent_zip_code", "").strip()

            # ============================================
            # 4. EDUCATIONAL INFORMATION
            # ============================================
            is_pwd = request.POST.get("is_pwd", "No") == "Yes"
            has_pwd_id = request.POST.get("has_pwd_id", "No") == "Yes"

            # Get disability types (multiple checkboxes)
            disability_types = request.POST.getlist("disability_type")
            disability_subtypes = request.POST.getlist("disability_subtype")

            # Get grade levels (multiple checkboxes)
            grade_levels = request.POST.getlist("grade_level")

            # ============================================
            # 5A. ALS ATTENDANCE HISTORY
            # ============================================
            attended_als_before = request.POST.get("attended_als_before", "No") == "Yes"
            als_programs = request.POST.getlist("als_program")
            als_completed = request.POST.get("als_completed", "No") == "Yes"
            als_not_completed_reason = request.POST.get(
                "als_not_completed_reason", ""
            ).strip()

            # ============================================
            # 6. REASONS FOR NOT ATTENDING SCHOOL
            # ============================================
            reasons_not_schooling = request.POST.getlist("reason_not_schooling")
            reason_not_schooling_other = request.POST.get(
                "reason_not_schooling_other", ""
            ).strip()

            # ============================================
            # 7. LEARNING CENTER ACCESSIBILITY
            # ============================================
            learning_center_distance = request.POST.get("learning_center_distance", "")
            learning_center_transport = request.POST.get(
                "learning_center_transport", ""
            )
            learning_center_transport_other = request.POST.get(
                "learning_center_transport_other", ""
            ).strip()
            travel_time = request.POST.get("travel_time", "").strip()

            # Weekly Availability
            availability_monday = request.POST.get("availability_monday", "").strip()
            availability_tuesday = request.POST.get("availability_tuesday", "").strip()
            availability_wednesday = request.POST.get(
                "availability_wednesday", ""
            ).strip()
            availability_thursday = request.POST.get(
                "availability_thursday", ""
            ).strip()
            availability_friday = request.POST.get("availability_friday", "").strip()
            availability_saturday = request.POST.get(
                "availability_saturday", ""
            ).strip()
            availability_sunday = request.POST.get("availability_sunday", "").strip()

            # ============================================
            # 8. PARENT/GUARDIAN INFORMATION
            # ============================================
            father_first_name = request.POST.get("father_first_name", "").strip()
            father_middle_name = request.POST.get("father_middle_name", "").strip()
            father_last_name = request.POST.get("father_last_name", "").strip()

            mother_first_name = request.POST.get("mother_first_name", "").strip()
            mother_middle_name = request.POST.get("mother_middle_name", "").strip()
            mother_last_name = request.POST.get("mother_last_name", "").strip()

            guardian_first_name = request.POST.get("guardian_first_name", "").strip()
            guardian_middle_name = request.POST.get("guardian_middle_name", "").strip()
            guardian_last_name = request.POST.get("guardian_last_name", "").strip()

            # ============================================
            # 9. LEARNING MODALITIES
            # ============================================
            learning_modalities = request.POST.getlist("learning_modality")
            criteria_plan = request.POST.getlist("criteria_plan")

            # ============================================
            # 10. CAMPUS AND DOCUMENTS
            # ============================================
            campus_id = request.POST.get("campus", "")
            lrn = request.POST.get("lrn", "").strip()

            # Get uploaded files
            birth_certificate = request.FILES.get("birth_certificate")
            valid_id = request.FILES.get("valid_id")

            # ============================================
            # VALIDATION
            # ============================================

            # Check if email already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
                return redirect("register")

            # Validate LRN if provided
            if lrn:
                lrn = lrn.replace("-", "").replace(" ", "")
                if not lrn.isdigit() or len(lrn) != 12:
                    messages.error(request, "LRN must be exactly 12 digits.")
                    return redirect("register")
                if StudentProfile.objects.filter(lrn=lrn).exists():
                    messages.error(request, "This LRN is already registered.")
                    return redirect("register")

            # Validate file uploads
            if birth_certificate:
                if birth_certificate.size > 5 * 1024 * 1024:
                    messages.error(
                        request, "Birth certificate file size must be less than 5MB."
                    )
                    return redirect("register")
                ext = os.path.splitext(birth_certificate.name)[1].lower()
                if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
                    messages.error(
                        request, "Birth certificate must be PDF, JPG, or PNG format."
                    )
                    return redirect("register")

            if valid_id:
                if valid_id.size > 5 * 1024 * 1024:
                    messages.error(request, "Valid ID file size must be less than 5MB.")
                    return redirect("register")
                ext = os.path.splitext(valid_id.name)[1].lower()
                if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
                    messages.error(request, "Valid ID must be PDF, JPG, or PNG format.")
                    return redirect("register")

            # ============================================
            # CREATE USER AND PROFILE
            # ============================================

            # Generate username and password
            username = generate_username(first_name, last_name)
            password = generate_password()

            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            # Get campus object
            campus = None
            if campus_id:
                try:
                    campus = Campus.objects.get(id=campus_id, is_active=True)
                except (Campus.DoesNotExist, ValueError):
                    pass

            # Create full address string for compatibility
            address_parts = [street_name, barangay, municipality, province, zip_code]
            full_address = ", ".join([p for p in address_parts if p])

            # Create student profile
            student_profile = StudentProfile(
                user=user,
                # Registration
                registration_date=registration_date if registration_date else None,
                # Personal Information
                middle_name=middle_name,
                extension_name=extension_name,
                birthdate=birthdate if birthdate else None,
                age=int(age) if age and age.isdigit() else None,
                gender=sex,
                place_of_birth=place_of_birth,
                civil_status=civil_status,
                religion=religion,
                mother_tongue=mother_tongue,
                # Indigenous People
                is_indigenous_people=(indigenous_people == "Yes"),
                indigenous_specify=indigenous_specify,
                # 4Ps
                is_4ps_beneficiary=(is_4ps_beneficiary == "Yes"),
                fourps_household_id=fourps_household_id,
                # Contact
                phone=phone,
                contact_numbers=contact_numbers,
                # Address
                street_name=street_name,
                province=province,
                municipality=municipality,
                barangay=barangay,
                zip_code=zip_code,
                address=full_address,
                # Permanent Address
                same_address=same_address,
                permanent_street_name=permanent_street_name,
                permanent_province=permanent_province,
                permanent_municipality=permanent_municipality,
                permanent_barangay=permanent_barangay,
                permanent_zip_code=permanent_zip_code,
                # Educational - PWD
                is_pwd=is_pwd,
                has_pwd_id=has_pwd_id,
                disability_types=(
                    ",".join(disability_types) if disability_types else None
                ),
                disability_subtypes=(
                    ",".join(disability_subtypes) if disability_subtypes else None
                ),
                # Grade Levels
                last_grade_levels=",".join(grade_levels) if grade_levels else None,
                # ALS History
                attended_als_before=attended_als_before,
                als_programs=",".join(als_programs) if als_programs else None,
                als_completed=als_completed,
                als_not_completed_reason=als_not_completed_reason,
                # Reasons Not Schooling
                reasons_not_schooling=(
                    ",".join(reasons_not_schooling) if reasons_not_schooling else None
                ),
                reason_not_schooling_other=reason_not_schooling_other,
                # Learning Center
                learning_center_distance=learning_center_distance,
                learning_center_transport=learning_center_transport,
                learning_center_transport_other=learning_center_transport_other,
                travel_time=travel_time,
                # Weekly Availability
                availability_monday=availability_monday,
                availability_tuesday=availability_tuesday,
                availability_wednesday=availability_wednesday,
                availability_thursday=availability_thursday,
                availability_friday=availability_friday,
                availability_saturday=availability_saturday,
                availability_sunday=availability_sunday,
                # Parents/Guardians
                father_first_name=father_first_name,
                father_middle_name=father_middle_name,
                father_last_name=father_last_name,
                mother_first_name=mother_first_name,
                mother_middle_name=mother_middle_name,
                mother_last_name=mother_last_name,
                guardian_first_name=guardian_first_name,
                guardian_middle_name=guardian_middle_name,
                guardian_last_name=guardian_last_name,
                # Learning Modalities
                learning_modalities=(
                    ",".join(learning_modalities) if learning_modalities else None
                ),
                criteria_plan=",".join(criteria_plan) if criteria_plan else None,
                # Campus
                campus=campus,
                enrolled_in=None,
                # Documents
                lrn=lrn if lrn else None,
                documents_uploaded_at=(
                    timezone.now() if (birth_certificate or valid_id) else None
                ),
                # Status
                status="pending",
            )

            # Save files if they exist
            if birth_certificate:
                student_profile.birth_certificate = birth_certificate
            if valid_id:
                student_profile.valid_id = valid_id

            # Save the profile
            student_profile.save()

            # ── REAL-TIME: notify admin of new registration ──
            broadcast_event(
                "student_registered",
                {
                    "name": f"{first_name} {last_name}",
                },
            )

            messages.success(
                request,
                "Registration submitted successfully! Your account is pending approval. You will receive your login credentials via email once approved.",
            )
            return redirect("student_login")

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            print(f"Error in registration: {str(e)}")
            import traceback

            traceback.print_exc()
            return redirect("register")

    # For GET request, get active campuses
    campuses = Campus.objects.filter(is_active=True).order_by("name")
    return render(request, "landing/register.html", {"campuses": campuses})


@sensitive_post_parameters()
@csrf_protect
@never_cache
def logout_view(request):
    """Logout user and prevent back button navigation"""
    # Store the referer to determine where to redirect
    referer = request.META.get("HTTP_REFERER", "")

    # Clear messages
    storage = messages.get_messages(request)
    storage.used = True

    # Logout the user
    logout(request)

    # Clear session completely
    request.session.flush()

    # Determine redirect based on where the logout came from
    if "teacher" in referer:
        response = redirect("teacher_login")

    elif "admin" in referer:
        response = redirect("admin_login")

    else:
        response = redirect("home")

    # Add extensive cache-control headers
    response["Cache-Control"] = (
        "no-cache, no-store, must-revalidate, max-age=0, private"
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    # Add headers to prevent caching in all browsers
    response["X-Frame-Options"] = "DENY"
    response["X-Content-Type-Options"] = "nosniff"

    return response


@login_required
@never_cache
def admin_dashboard(request):
    """Admin dashboard - requires staff status"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("home")

    # Get all student profiles with user data
    all_students = (
        StudentProfile.objects.select_related("user").all().order_by("-created_at")
    )

    # Statistics
    total_students = StudentProfile.objects.filter(status="approved").count()

    # FIXED: Only count teachers (staff but NOT superuser)
    total_admins = User.objects.filter(is_staff=True, is_superuser=False).count()

    total_admissions = StudentProfile.objects.count()
    pending_count = StudentProfile.objects.filter(status="pending").count()

    # Recent users (students only, no admins)
    recent_users = User.objects.filter(is_staff=False).order_by("-date_joined")[:5]

    context = {
        "students": all_students,
        "total_students": total_students,
        "total_admins": total_admins,  # Now this will show ONLY teachers
        "total_admissions": total_admissions,
        "pending_count": pending_count,
        "recent_users": recent_users,
        "active_page": "dashboard",
    }
    return render(request, "administrator/admin_dashboard.html", context)


@login_required
@never_cache
def manage_students(request):
    """Manage Students page - full CRUD for approved students"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("home")

    students = (
        StudentProfile.objects.select_related("user", "campus")
        .filter(status="approved")
        .order_by("-created_at")
    )

    # Search
    search_query = request.GET.get("search", "").strip()
    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(lrn__icontains=search_query)
            | Q(campus__name__icontains=search_query)
        )

    # Campus filter
    campus_filter = request.GET.get("campus", "")
    if campus_filter:
        students = students.filter(campus__id=campus_filter)

    campuses = Campus.objects.filter(is_active=True).order_by("name")

    context = {
        "students": students,
        "campuses": campuses,
        "search_query": search_query,
        "campus_filter": campus_filter,
        "active_page": "manage_students",
    }
    return render(request, "administrator/manage_students.html", context)


@login_required
@never_cache
def subject_enrollment(request):
    """Admin page: list approved students for subject enrollment."""
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect("home")

    students = (
        StudentProfile.objects.select_related("user", "campus")
        .filter(status="approved")
        .order_by("-created_at")
    )

    search_query = request.GET.get("search", "").strip()
    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(lrn__icontains=search_query)
            | Q(campus__name__icontains=search_query)
        )

    campus_filter = request.GET.get("campus", "")
    if campus_filter:
        students = students.filter(campus__id=campus_filter)

    # Annotate active enrollment counts for the table
    student_rows = []
    for student in students:
        enrolled = student.enrolled_subjects()
        student_rows.append(
            {
                "student": student,
                "enrolled_count": len(enrolled),
                "enrolled_subjects": enrolled,
            }
        )

    campuses = Campus.objects.filter(is_active=True).order_by("name")

    context = {
        "student_rows": student_rows,
        "campuses": campuses,
        "search_query": search_query,
        "campus_filter": campus_filter,
        "active_page": "subject_enrollment",
    }
    return render(request, "administrator/subject_enrollment.html", context)


@login_required
@never_cache
def enroll_student_subjects(request, student_id):
    """Admin page: enroll/unenroll a student in subjects."""
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect("home")

    try:
        student = StudentProfile.objects.select_related("user", "campus").get(
            id=student_id, status="approved"
        )
    except StudentProfile.DoesNotExist:
        messages.error(request, "Approved student not found.")
        return redirect("subject_enrollment")

    valid_subjects = {value for value, _label in SUBJECT_CHOICES}

    if request.method == "POST":
        selected = set(request.POST.getlist("subjects"))
        invalid = selected - valid_subjects
        if invalid:
            messages.error(request, "One or more selected subjects are invalid.")
            return redirect("enroll_student_subjects", student_id=student.id)

        existing = {
            e.subject: e
            for e in SubjectEnrollment.objects.filter(student=student)
        }

        # Activate or create selected subjects
        for subject_name in selected:
            enrollment = existing.get(subject_name)
            if enrollment:
                if not enrollment.is_active:
                    enrollment.is_active = True
                    enrollment.enrolled_by = request.user
                    enrollment.save(
                        update_fields=["is_active", "enrolled_by"]
                    )
            else:
                SubjectEnrollment.objects.create(
                    student=student,
                    subject=subject_name,
                    enrolled_by=request.user,
                    is_active=True,
                )

        # Deactivate unchecked subjects (preserve history)
        for subject_name, enrollment in existing.items():
            if subject_name not in selected and enrollment.is_active:
                enrollment.is_active = False
                enrollment.save(update_fields=["is_active"])

        messages.success(
            request,
            f"Subject enrollment updated for {student.user.get_full_name()}.",
        )
        return redirect("enroll_student_subjects", student_id=student.id)

    current_enrolled = set(student.enrolled_subjects())
    subject_options = [
        {"value": value, "label": label, "checked": value in current_enrolled}
        for value, label in SUBJECT_CHOICES
    ]

    missing_grade = not student.enrolled_in
    missing_campus = not student.campus

    context = {
        "student": student,
        "subject_options": subject_options,
        "missing_grade": missing_grade,
        "missing_campus": missing_campus,
        "active_page": "subject_enrollment",
    }
    return render(request, "administrator/enroll_student_subjects.html", context)


@login_required
@require_POST
@staff_member_required
@csrf_protect
def update_requirement_status(request, student_id):
    """AJAX endpoint: mark a requirement as Completed"""
    if not request.user.is_staff:
        return JsonResponse({"error": "Access denied"}, status=403)
    try:
        student = get_object_or_404(StudentProfile, id=student_id)
        requirement = request.POST.get("requirement")  # 'bc' or 'vid'
        if requirement == "bc":
            student.bc_status = "completed"
            student.save(update_fields=["bc_status"])
            return JsonResponse({"status": "completed", "requirement": "bc"})
        elif requirement == "vid":
            student.vid_status = "completed"
            student.save(update_fields=["vid_status"])
            return JsonResponse({"status": "completed", "requirement": "vid"})
        else:
            return JsonResponse({"error": "Invalid requirement"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@never_cache
def student_dashboard(request):
    """Student dashboard - requires login"""
    try:
        student_profile = request.user.student_profile

        # Get module statistics
        if student_profile.enrolled_in and student_profile.campus:
            enrolled_subjects = student_profile.enrolled_subjects()
            # Get total modules available for this student (enrolled subjects only)
            total_modules = LearningModule.objects.filter(
                campus=student_profile.campus,
                grade_level=student_profile.enrolled_in,
                is_active=True,
                subject__in=enrolled_subjects,
            ).count()

            # Get completed modules (modules the student has accessed)
            accessed_modules = ModuleAccess.objects.filter(
                student=student_profile,
                module__subject__in=enrolled_subjects,
            ).values_list("module_id", flat=True)

            completed_modules = len(accessed_modules)

            # Requirements: Birth Certificate + Valid ID
            total_requirements = 2
            completed_requirements = sum(
                [
                    student_profile.bc_status == "completed",
                    student_profile.vid_status == "completed",
                ]
            )
        else:
            total_modules = 0
            completed_modules = 0
            total_requirements = 2
            completed_requirements = sum(
                [
                    student_profile.bc_status == "completed",
                    student_profile.vid_status == "completed",
                ]
            )

        # Get upcoming schedules (limit to next 3-5 for dashboard)
        upcoming_schedules = {"today": [], "upcoming": []}

        if student_profile.campus:
            # Base queryset for schedules
            campus_schedules = (
                Schedule.objects.filter(campus=student_profile.campus, is_active=True)
                .select_related("teacher__user")
                .order_by("day_of_week", "start_time")
            )

            # Filter by grade level if assigned
            if student_profile.enrolled_in:
                campus_schedules = campus_schedules.filter(
                    Q(grade_level="All Levels")
                    | Q(grade_level=student_profile.enrolled_in)
                )

            # Get today's day name
            import datetime

            today = datetime.datetime.now().strftime("%A")

            # Get today's schedules
            upcoming_schedules["today"] = campus_schedules.filter(day_of_week=today)[:3]

            # Get upcoming schedules for other days
            days_order = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            current_day_index = days_order.index(today) if today in days_order else 0

            upcoming_days = (
                days_order[current_day_index + 1 :] + days_order[:current_day_index]
            )
            upcoming_days = upcoming_days[:3]  # Next 3 days after today

            for day in upcoming_days:
                day_schedules = campus_schedules.filter(day_of_week=day)[:2]
                if day_schedules:
                    upcoming_schedules["upcoming"].append(
                        {"day": day, "schedules": day_schedules}
                    )

        context = {
            "student_profile": student_profile,
            "upcoming_schedules": upcoming_schedules,
            "has_schedule": bool(
                upcoming_schedules["today"] or upcoming_schedules["upcoming"]
            ),
            "current_grade": (
                student_profile.enrolled_in
                if student_profile.enrolled_in
                else "Not Assigned"
            ),
            "total_modules": total_modules,
            "completed_modules": completed_modules,
            "total_requirements": total_requirements,
            "completed_requirements": completed_requirements,
            "active_page": "dashboard",
        }
        return render(request, "student/student_dashboard.html", context)

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("home")


@login_required
@never_cache
def admission_management(request):
    """Admission management page - requires admin login"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("home")

    total_pending = StudentProfile.objects.filter(status="pending").count()
    total_approved = StudentProfile.objects.filter(status="approved").count()
    total_rejected = StudentProfile.objects.filter(status="rejected").count()

    pending_students = (
        StudentProfile.objects.select_related("user", "campus")
        .filter(status="pending")
        .order_by("-created_at")
    )

    context = {
        "total_pending": total_pending,
        "total_approved": total_approved,
        "total_rejected": total_rejected,
        "pending_students": pending_students,
        "active_page": "admission",
    }
    return render(request, "administrator/admission_management.html", context)


def teacher_login(request):
    """Teacher login page"""
    # If user is already logged in as teacher, redirect to dashboard
    if (
        request.user.is_authenticated
        and request.user.is_staff
        and not request.user.is_superuser
    ):
        return redirect("teacher_dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check if user is a teacher (staff but not superuser)
            if user.is_staff and not user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name}!")

                # Redirect to next parameter if exists
                next_url = request.GET.get("next", "teacher_dashboard")
                return redirect(next_url)
            else:
                messages.error(request, "Invalid teacher account.")
        else:
            messages.error(request, "Invalid username or password.")
        return redirect("teacher_login")

    return render(request, "landing/teacher_login.html")


@login_required
@never_cache
def teacher_dashboard(request):
    """Teacher dashboard - shows only students from their school"""
    # Check if user is a teacher
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    # Get teacher's school from their profile
    try:
        teacher_profile = request.user.teacher_profile
        teacher_school = (
            teacher_profile.campus.name if teacher_profile.campus else "Not Assigned"
        )

        # Get ONLY students from this teacher's school
        my_students = StudentProfile.objects.filter(
            campus=teacher_profile.campus, status="approved"
        ).select_related("user")

        # Statistics
        total_students = my_students.count()
        approved_count = total_students
        pending_count = StudentProfile.objects.filter(
            campus=teacher_profile.campus, status="pending"
        ).count()

        context = {
            "teacher_school": teacher_school,
            "my_students": my_students,
            "total_students": total_students,
            "approved_count": approved_count,
            "pending_count": pending_count,
            "active_page": "dashboard",
        }
        return render(request, "teacher/teacher_dashboard.html", context)

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
@never_cache
def teacher_management(request):
    """Teacher management page - requires admin login"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    # Get all teachers
    teachers = User.objects.filter(is_staff=True, is_superuser=False).prefetch_related(
        "teacher_profile__campus"
    )

    # Get all campuses with their assigned teachers
    campuses = (
        Campus.objects.filter(is_active=True)
        .prefetch_related("teachers")
        .order_by("name")
    )

    # Annotate each campus with its teacher (if any)
    for campus in campuses:
        campus.teacher = campus.teachers.first()

    context = {
        "teachers": teachers,
        "campuses": campuses,
        "total_campuses": campuses.count(),
        "active_page": "teachers",
    }
    return render(request, "administrator/teacher_management.html", context)


@login_required
def create_teacher(request):
    """Create a new teacher account"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        campus_input = request.POST.get("campus")
        campus = None
        if campus_input:
            try:
                # Try interpret as a PK
                campus = Campus.objects.get(id=int(campus_input))
            except (ValueError, Campus.DoesNotExist):
                try:
                    # Fallback to lookup by name
                    campus = Campus.objects.get(name=campus_input)
                except Campus.DoesNotExist:
                    campus = None
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Generate username if not provided
        if not username:
            username = generate_username(first_name, last_name)

        # Generate password if not provided
        if not password:
            password = generate_password(8)

        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return redirect("teacher_management")

        # Check if email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, f'Email "{email}" is already registered.')
            return redirect("teacher_management")

        # Validate campus selection
        if not campus:
            messages.error(request, "Selected campus not found or invalid.")
            return redirect("teacher_management")

        # Check if campus already has a teacher
        if Teacher.objects.filter(campus=campus).exists():
            existing_teacher = Teacher.objects.get(campus=campus)
            messages.error(
                request,
                f"A teacher for {campus.name} already exists: {existing_teacher.user.get_full_name()}",
            )
            return redirect("teacher_management")

        try:
            # Create user with staff status (but not superuser)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,  # Teachers have staff access but not admin
            )

            # Create teacher profile
            Teacher.objects.create(user=user, campus=campus, phone=phone)

            messages.success(request, f"✅ Teacher account created successfully!")

        except Exception as e:
            messages.error(request, f"Error creating teacher: {str(e)}")

        return redirect("teacher_management")

    return redirect("teacher_management")


@login_required
def reset_teacher_password(request, teacher_id):
    """Reset a teacher's password"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher = User.objects.get(id=teacher_id, is_staff=True, is_superuser=False)
        new_password = generate_password(8)

        teacher.set_password(new_password)
        teacher.save()

        messages.success(
            request,
            f"✅ Password reset for {teacher.get_full_name()}<br><br>"
            f"<strong>📋 NEW PASSWORD:</strong><br>"
            f"• Password: <strong>{new_password}</strong>",
        )

    except User.DoesNotExist:
        messages.error(request, "Teacher not found.")

    return redirect("teacher_management")


@login_required
def delete_teacher(request, teacher_id):
    """Delete a teacher account"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher = User.objects.get(id=teacher_id, is_staff=True, is_superuser=False)
        teacher_name = teacher.get_full_name()
        teacher.delete()
        messages.success(
            request, f"Teacher account for {teacher_name} has been deleted."
        )

    except User.DoesNotExist:
        messages.error(request, "Teacher not found.")

    return redirect("teacher_management")


# ============================================
# STUDENT MANAGEMENT FUNCTIONS (Admin Only)
# ============================================


@login_required
def approve_student(request, student_id):
    """Approve a student's registration and send email with login credentials"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        profile = StudentProfile.objects.get(id=student_id)

        # Generate a new password for the student
        new_password = generate_password(10)

        # IMPORTANT: Use set_password() to properly hash the password
        profile.user.set_password(new_password)
        profile.user.save()  # Save the user with the new hashed password

        # Update profile status
        profile.status = "approved"
        # Auto-set requirement status based on uploaded files
        if profile.birth_certificate and profile.bc_status == "not_available":
            profile.bc_status = "completed"
        if profile.valid_id and profile.vid_status == "not_available":
            profile.vid_status = "completed"
        profile.save()

        # Verify the password was set correctly
        from django.contrib.auth import authenticate

        verify_user = authenticate(
            username=profile.user.username, password=new_password
        )
        if verify_user is not None:
            print(f"✅ Password verified for {profile.user.username}")
        else:
            print(f"❌ Password verification FAILED for {profile.user.username}")

        # ── REAL-TIME: notify all dashboards ──
        broadcast_event(
            "student_status_changed",
            {
                "id": profile.id,
                "status": "approved",
                "name": profile.user.get_full_name(),
            },
        )

        # SEND EMAIL WITH CREDENTIALS
        if not profile.user.email:
            messages.warning(
                request,
                f"✅ Student {profile.user.get_full_name()} has been APPROVED! But no email is on file — credentials must be provided manually. Username: {profile.user.username}, Password: {new_password}",
            )
        else:
            email_sent = send_approval_email(profile, new_password)
            if email_sent:
                messages.success(
                    request,
                    f"✅ Student {profile.user.get_full_name()} has been APPROVED! An email with login credentials has been sent to {profile.user.email}.",
                )
            else:
                messages.warning(
                    request,
                    f"✅ Student {profile.user.get_full_name()} has been APPROVED! But the email with credentials failed to send. Username: {profile.user.username}, Password: {new_password}",
                )

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student not found.")

    return redirect("admin_dashboard")


@login_required
def reject_student(request, student_id):
    """Reject a student's registration"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        profile = StudentProfile.objects.get(id=student_id)
        profile.status = "rejected"
        profile.save()

        # Send rejection email
        if not profile.user.email:
            messages.warning(
                request,
                f"Student {profile.user.get_full_name()} has been rejected. But no email is on file.",
            )
        else:
            email_sent = send_rejection_email(profile)
            if email_sent:
                messages.success(
                    request,
                    f"Student {profile.user.get_full_name()} has been rejected. A notification email was sent.",
                )
            else:
                messages.warning(
                    request,
                    f"Student {profile.user.get_full_name()} has been rejected. But the notification email failed to send.",
                )

        # ── REAL-TIME: notify all dashboards ──
        broadcast_event(
            "student_status_changed",
            {
                "id": profile.id,
                "status": "rejected",
                "name": profile.user.get_full_name(),
            },
        )
    except StudentProfile.DoesNotExist:
        messages.error(request, "Student not found.")

    return redirect("admin_dashboard")


@login_required
def delete_student(request, student_id):
    """Delete a student and their profile"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        profile = StudentProfile.objects.get(id=student_id)
        user = profile.user
        user.delete()
        messages.success(request, "Student has been deleted successfully.")
    except StudentProfile.DoesNotExist:
        messages.error(request, "Student not found.")

    return redirect("manage_students")


@login_required
def edit_student(request, student_id):
    """Edit comprehensive student information"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        profile = StudentProfile.objects.select_related("user").get(id=student_id)
    except StudentProfile.DoesNotExist:
        messages.error(request, "Student not found.")
        return redirect("admin_dashboard")

    if request.method == "POST":
        try:
            # Update user fields
            user = profile.user
            user.first_name = request.POST.get("first_name", user.first_name)
            user.last_name = request.POST.get("last_name", user.last_name)
            user.email = request.POST.get("email", user.email)
            user.save()

            # Personal Information
            profile.middle_name = request.POST.get("middle_name", "")
            profile.extension_name = request.POST.get("extension_name", "")
            profile.birthdate = request.POST.get("birthdate") or profile.birthdate
            profile.age = (
                int(request.POST.get("age")) if request.POST.get("age") else profile.age
            )
            profile.gender = request.POST.get("gender", "")
            profile.place_of_birth = request.POST.get("place_of_birth", "")
            profile.civil_status = request.POST.get("civil_status", "")
            profile.religion = request.POST.get("religion", "")
            profile.mother_tongue = request.POST.get("mother_tongue", "")
            profile.lrn = request.POST.get("lrn", "") or None

            # Indigenous & 4Ps
            profile.is_indigenous_people = (
                request.POST.get("is_indigenous_people", "No") == "Yes"
            )
            profile.indigenous_specify = request.POST.get("indigenous_specify", "")
            profile.is_4ps_beneficiary = (
                request.POST.get("is_4ps_beneficiary", "No") == "Yes"
            )
            profile.fourps_household_id = request.POST.get("fourps_household_id", "")

            # Contact
            profile.contact_numbers = request.POST.get("contact_numbers", "")
            profile.phone = (
                request.POST.get("contact_numbers", "").split(",")[0].strip()
                if request.POST.get("contact_numbers")
                else ""
            )

            # Address
            profile.street_name = request.POST.get("street_name", "")
            profile.barangay = request.POST.get("barangay", "")
            profile.municipality = request.POST.get("municipality", "")
            profile.province = request.POST.get("province", "")
            profile.zip_code = request.POST.get("zip_code", "")

            # Create full address for compatibility
            address_parts = [
                profile.street_name,
                profile.barangay,
                profile.municipality,
                profile.province,
                profile.zip_code,
            ]
            profile.address = ", ".join([p for p in address_parts if p])

            # PWD
            profile.is_pwd = request.POST.get("is_pwd", "No") == "Yes"
            profile.has_pwd_id = request.POST.get("has_pwd_id", "No") == "Yes"
            profile.disability_types = ", ".join(
                request.POST.getlist("disability_types")
            )
            profile.disability_subtypes = ", ".join(
                request.POST.getlist("disability_subtypes")
            )

            # Section 5: Last Grade Level Completed
            profile.last_grade_levels = ", ".join(
                request.POST.getlist("last_grade_levels")
            )

            # Section 5A: ALS Attendance History
            profile.attended_als_before = (
                request.POST.get("attended_als_before", "No") == "Yes"
            )
            profile.als_programs = ", ".join(request.POST.getlist("als_programs"))
            profile.als_completed = request.POST.get("als_completed", "No") == "Yes"
            profile.als_not_completed_reason = request.POST.get(
                "als_not_completed_reason", ""
            )

            # Section 6: Reasons Not Schooling
            profile.reasons_not_schooling = ", ".join(
                request.POST.getlist("reasons_not_schooling")
            )
            profile.reason_not_schooling_other = request.POST.get(
                "reason_not_schooling_other", ""
            )

            # Section 7: Accessibility and Availability of CLC
            profile.learning_center_distance = request.POST.get(
                "learning_center_distance", ""
            )
            profile.learning_center_transport = request.POST.get(
                "learning_center_transport", ""
            )
            profile.learning_center_transport_other = request.POST.get(
                "learning_center_transport_other", ""
            )
            profile.travel_time = request.POST.get("travel_time", "").strip()
            profile.availability_monday = request.POST.get(
                "availability_monday", ""
            ).strip()
            profile.availability_tuesday = request.POST.get(
                "availability_tuesday", ""
            ).strip()
            profile.availability_wednesday = request.POST.get(
                "availability_wednesday", ""
            ).strip()
            profile.availability_thursday = request.POST.get(
                "availability_thursday", ""
            ).strip()
            profile.availability_friday = request.POST.get(
                "availability_friday", ""
            ).strip()
            profile.availability_saturday = request.POST.get(
                "availability_saturday", ""
            ).strip()
            profile.availability_sunday = request.POST.get(
                "availability_sunday", ""
            ).strip()

            # Parent/Guardian Names
            profile.father_first_name = request.POST.get("father_first_name", "")
            profile.father_middle_name = request.POST.get("father_middle_name", "")
            profile.father_last_name = request.POST.get("father_last_name", "")

            profile.mother_first_name = request.POST.get("mother_first_name", "")
            profile.mother_middle_name = request.POST.get("mother_middle_name", "")
            profile.mother_last_name = request.POST.get("mother_last_name", "")

            profile.guardian_first_name = request.POST.get("guardian_first_name", "")
            profile.guardian_middle_name = request.POST.get("guardian_middle_name", "")
            profile.guardian_last_name = request.POST.get("guardian_last_name", "")

            # Campus (resolve to Campus instance)
            campus_input = request.POST.get("campus", "")
            if campus_input:
                try:
                    if str(campus_input).isdigit():
                        profile.campus = Campus.objects.get(id=int(campus_input))
                    else:
                        profile.campus = Campus.objects.get(name=campus_input)
                except Campus.DoesNotExist:
                    profile.campus = None
            else:
                profile.campus = None

            # Enrolled In (IMPORTANT: Keep this field)
            profile.enrolled_in = request.POST.get("enrolled_in", "") or None

            profile.save()

            messages.success(request, "✅ Student information updated successfully.")
            return redirect("manage_students")

        except Exception as e:
            messages.error(request, f"Error updating student: {str(e)}")
            return redirect("manage_students")

    # For GET request
    campuses = Campus.objects.filter(is_active=True).order_by("name")
    context = {
        "student": profile,
        "campuses": campuses,
        "active_page": "manage_students",
    }
    return render(request, "administrator/edit_student.html", context)


@login_required
@never_cache
def student_modules(request):
    """Student learning modules page - shows modules for their grade level"""
    try:
        student_profile = request.user.student_profile

        # Check if student has grade level assigned
        if not student_profile.enrolled_in:
            context = {
                "student_profile": student_profile,
                "has_grade_level": False,
                "has_subject_enrollment": False,
                "modules": [],
                "active_page": "modules",
            }
            return render(request, "student/student_subjects.html", context)

        enrolled_subjects = student_profile.enrolled_subjects()
        if not enrolled_subjects:
            context = {
                "student_profile": student_profile,
                "has_grade_level": True,
                "has_subject_enrollment": False,
                "current_grade": student_profile.enrolled_in,
                "modules": [],
                "active_page": "modules",
            }
            return render(request, "student/student_subjects.html", context)

        # Get filter parameters
        filter_subject = request.GET.get("subject", "all")
        search_query = request.GET.get("search", "")

        # Base queryset - only show modules for student's grade, campus, and enrolled subjects
        modules = (
            LearningModule.objects.filter(
                campus=student_profile.campus,
                grade_level=student_profile.enrolled_in,
                is_active=True,
                subject__in=enrolled_subjects,
            )
            .select_related("teacher__user")
            .order_by("-created_at")
        )

        # Apply filters
        if filter_subject != "all":
            if filter_subject not in enrolled_subjects:
                modules = modules.none()
            else:
                modules = modules.filter(subject=filter_subject)

        if search_query:
            modules = modules.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(subject__icontains=search_query)
            )

        # Get accessed modules for this student
        accessed_modules = ModuleAccess.objects.filter(
            student=student_profile
        ).values_list("module_id", flat=True)

        # Group modules by subject
        subjects = {}
        for module in modules:
            if module.subject not in subjects:
                subjects[module.subject] = []
            subjects[module.subject].append(module)

        # Statistics
        total_modules = modules.count()
        new_modules = modules.exclude(id__in=accessed_modules).count()

        # Get unique values for filters (enrolled subjects only)
        subjects_list = (
            LearningModule.objects.filter(
                campus=student_profile.campus,
                grade_level=student_profile.enrolled_in,
                is_active=True,
                subject__in=enrolled_subjects,
            )
            .values_list("subject", flat=True)
            .distinct()
        )

        quarters = ["Quarter 1", "Quarter 2", "Quarter 3", "Quarter 4"]

        context = {
            "student_profile": student_profile,
            "subjects": subjects,
            "total_modules": total_modules,
            "new_modules": new_modules,
            "accessed_modules": list(accessed_modules),
            "subjects_list": subjects_list,
            "quarters": quarters,
            "current_filter": {
                "subject": filter_subject,
                "search": search_query,
            },
            "has_grade_level": True,
            "has_subject_enrollment": True,
            "current_grade": student_profile.enrolled_in,
            "active_page": "modules",
        }
        return render(request, "student/student_modules.html", context)

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("student_subjects")


@login_required
@never_cache
def view_module(request, module_id):
    """View module details and track access"""
    try:
        student_profile = request.user.student_profile
        enrolled_subjects = student_profile.enrolled_subjects()
        module = get_object_or_404(
            LearningModule,
            id=module_id,
            campus=student_profile.campus,
            grade_level=student_profile.enrolled_in,
            is_active=True,
            subject__in=enrolled_subjects,
        )

        # Record access
        access, created = ModuleAccess.objects.get_or_create(
            student=student_profile, module=module
        )

        context = {
            "student_profile": student_profile,
            "module": module,
            "accessed": not created,
            "active_page": "modules",
        }
        return render(request, "student/view_module.html", context)

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("home")


@login_required
def student_download_module(request, module_id):
    """Download module (student access)"""
    try:
        student_profile = request.user.student_profile
        enrolled_subjects = student_profile.enrolled_subjects()
        module = get_object_or_404(
            LearningModule,
            id=module_id,
            campus=student_profile.campus,
            grade_level=student_profile.enrolled_in,
            is_active=True,
            subject__in=enrolled_subjects,
        )

        # Record download
        access, created = ModuleAccess.objects.get_or_create(
            student=student_profile, module=module
        )
        access.downloaded = True
        access.save()

        # Increment download count
        module.increment_download_count()

        # Serve file
        response = FileResponse(module.file, as_attachment=True)
        return response

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("home")


@login_required
def student_requirements(request):
    """Student requirements page"""
    try:
        profile = request.user.student_profile
    except Exception:
        profile = None

    total = 2
    completed = 0
    if profile:
        if profile.bc_status == "completed":
            completed += 1
        if profile.vid_status == "completed":
            completed += 1

    context = {
        "active_page": "requirements",
        "profile": profile,
        "total_requirements": total,
        "completed_requirements": completed,
        "pending_requirements": total - completed,
    }
    return render(request, "student/student_requirements.html", context)


@login_required
@never_cache
def student_profile(request):
    """Student profile settings - password change only"""
    if request.method == "POST":
        current_password = request.POST.get("current_password", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not current_password or not new_password or not confirm_password:
            messages.error(request, "Please fill in all fields.")
        elif not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        elif len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "✅ Password updated successfully!")

        return redirect("student_profile")

    context = {"active_page": "profile"}
    return render(request, "student/student_profile.html", context)


@login_required
@never_cache
def teacher_schedules(request):
    """Teacher schedule management page with filtering"""
    # Check if user is a teacher
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile

        # Get filter parameters
        filter_grade = request.GET.get("grade_level", "all")
        filter_status = request.GET.get("status", "all")
        filter_day = request.GET.get("day", "all")

        # Base queryset
        schedules = Schedule.objects.filter(
            campus=teacher_profile.campus, teacher=teacher_profile
        ).order_by("day_of_week", "start_time")

        # Apply filters
        if filter_grade != "all":
            schedules = schedules.filter(grade_level=filter_grade)

        if filter_status == "active":
            schedules = schedules.filter(is_active=True)
        elif filter_status == "inactive":
            schedules = schedules.filter(is_active=False)

        if filter_day != "all":
            schedules = schedules.filter(day_of_week=filter_day)

        # Group schedules by day for display
        days_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        schedules_by_day = {}
        for day in days_order:
            schedules_by_day[day] = schedules.filter(day_of_week=day, is_active=True)

        # Get inactive schedules separately
        inactive_schedules = schedules.filter(is_active=False)

        # Get unique grade levels for filter dropdown
        grade_levels = [
            "All Levels",
            "Grade 7",
            "Grade 8",
            "Grade 9",
            "Grade 10",
            "Grade 11",
            "Grade 12",
        ]

        context = {
            "teacher_profile": teacher_profile,
            "teacher_school": (
                teacher_profile.campus.name
                if teacher_profile.campus
                else "Not Assigned"
            ),
            "active_page": "schedules",
            "schedules_by_day": schedules_by_day,
            "inactive_schedules": inactive_schedules,
            "total_schedules": Schedule.objects.filter(teacher=teacher_profile).count(),
            "active_schedules": Schedule.objects.filter(
                teacher=teacher_profile, is_active=True
            ).count(),
            "grade_levels": grade_levels,
            "days_order": days_order,
            "current_filter": {
                "grade": filter_grade,
                "status": filter_status,
                "day": filter_day,
            },
        }
        return render(request, "teacher/teacher_schedules.html", context)

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def create_schedule(request):
    """Create a new schedule"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile

        if request.method == "POST":
            day_of_week = request.POST.get("day_of_week")
            start_time = request.POST.get("start_time")
            end_time = request.POST.get("end_time")
            subject = request.POST.get("subject")
            grade_level = request.POST.get("grade_level", "All Levels")
            room = request.POST.get("room", "")
            notes = request.POST.get("notes", "")

            # Validation
            if not all([day_of_week, start_time, end_time, subject]):
                messages.error(request, "Please fill in all required fields.")
                return redirect("teacher_schedules")

            # Convert string times to time objects for comparison
            from datetime import datetime

            try:
                start_time_obj = datetime.strptime(start_time, "%H:%M").time()
                end_time_obj = datetime.strptime(end_time, "%H:%M").time()
            except ValueError:
                messages.error(request, "Invalid time format.")
                return redirect("teacher_schedules")

            # Validate that end time is after start time
            if start_time_obj >= end_time_obj:
                messages.error(request, "End time must be after start time.")
                return redirect("teacher_schedules")

            # Check for overlapping schedules
            existing = Schedule.objects.filter(
                teacher=teacher_profile,
                campus=teacher_profile.campus,
                day_of_week=day_of_week,
                start_time=start_time_obj,
                is_active=True,
            ).exists()

            if existing:
                messages.error(
                    request,
                    f"A schedule already exists for {day_of_week} at {start_time}.",
                )
                return redirect("teacher_schedules")

            # Create schedule
            schedule = Schedule.objects.create(
                teacher=teacher_profile,
                campus=teacher_profile.campus,
                day_of_week=day_of_week,
                start_time=start_time_obj,
                end_time=end_time_obj,
                subject=subject,
                grade_level=grade_level,
                room=room,
                notes=notes,
                is_active=True,
            )

            messages.success(
                request, f"Schedule created successfully for {day_of_week}!"
            )

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "schedule_created",
                {
                    "id": schedule.id,
                    "day": schedule.day_of_week,
                    "subject": schedule.subject,
                },
            )

            return redirect("teacher_schedules")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")

    return redirect("teacher_schedules")


@login_required
def edit_schedule(request, schedule_id):
    """Edit an existing schedule"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        schedule = get_object_or_404(Schedule, id=schedule_id, teacher=teacher_profile)

        if request.method == "POST":
            # Get form data
            day_of_week = request.POST.get("day_of_week")
            start_time = request.POST.get("start_time")
            end_time = request.POST.get("end_time")
            subject = request.POST.get("subject")
            grade_level = request.POST.get("grade_level", "All Levels")
            room = request.POST.get("room", "")
            notes = request.POST.get("notes", "")

            # Convert string times to time objects
            from datetime import datetime

            try:
                start_time_obj = datetime.strptime(start_time, "%H:%M").time()
                end_time_obj = datetime.strptime(end_time, "%H:%M").time()
            except ValueError:
                messages.error(request, "Invalid time format.")
                return redirect("teacher_schedules")

            # Validate that end time is after start time
            if start_time_obj >= end_time_obj:
                messages.error(request, "End time must be after start time.")
                return redirect("teacher_schedules")

            # Check for overlaps (excluding current schedule)
            overlapping = (
                Schedule.objects.filter(
                    teacher=teacher_profile,
                    campus=teacher_profile.campus,
                    day_of_week=day_of_week,
                    start_time=start_time_obj,
                    is_active=True,
                )
                .exclude(id=schedule.id)
                .exists()
            )

            if overlapping:
                messages.error(
                    request,
                    f"Another schedule already exists for {day_of_week} at {start_time}.",
                )
                return redirect("teacher_schedules")

            # Update schedule
            schedule.day_of_week = day_of_week
            schedule.start_time = start_time_obj
            schedule.end_time = end_time_obj
            schedule.subject = subject
            schedule.grade_level = grade_level
            schedule.room = room
            schedule.notes = notes
            schedule.save()

            messages.success(request, "Schedule updated successfully!")

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "schedule_updated",
                {
                    "id": schedule.id,
                    "day": schedule.day_of_week,
                    "subject": schedule.subject,
                },
            )

            return redirect("teacher_schedules")

        # GET request - return schedule data for AJAX
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = {
                "id": schedule.id,
                "day_of_week": schedule.day_of_week,
                "start_time": schedule.start_time.strftime("%H:%M"),
                "end_time": schedule.end_time.strftime("%H:%M"),
                "subject": schedule.subject,
                "grade_level": schedule.grade_level,
                "room": schedule.room,
                "notes": schedule.notes,
            }
            return JsonResponse(data)

        return redirect("teacher_schedules")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def delete_schedule(request, schedule_id):
    """Delete a schedule"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        schedule = get_object_or_404(Schedule, id=schedule_id, teacher=teacher_profile)

        if request.method == "POST":
            schedule_id = schedule.id
            schedule.delete()
            messages.success(request, "Schedule deleted successfully!")

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event("schedule_deleted", {"id": schedule_id})

        return redirect("teacher_schedules")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def toggle_schedule(request, schedule_id):
    """Toggle schedule active status"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        schedule = get_object_or_404(Schedule, id=schedule_id, teacher=teacher_profile)

        if request.method == "POST":
            schedule.is_active = not schedule.is_active
            schedule.save()
            status = "activated" if schedule.is_active else "deactivated"
            messages.success(request, f"Schedule {status} successfully!")

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "schedule_updated",
                {
                    "id": schedule.id,
                    "is_active": schedule.is_active,
                },
            )

        return redirect("teacher_schedules")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


# ============================================
# UPDATED STUDENT SCHEDULE VIEW
# ============================================


@login_required
@never_cache
def student_schedule(request):
    """Student schedule page - shows schedules for their campus with filtering"""
    try:
        student_profile = request.user.student_profile

        # Get filter parameters from request
        filter_grade = request.GET.get("grade_level", "all")
        filter_day = request.GET.get("day", "all")

        # Base queryset
        campus_schedules = (
            Schedule.objects.filter(campus=student_profile.campus, is_active=True)
            .select_related("teacher__user")
            .order_by("day_of_week", "start_time")
        )

        # Apply grade level filtering based on selection
        if filter_grade == "my_level" and student_profile.enrolled_in:
            campus_schedules = campus_schedules.filter(
                Q(grade_level="All Levels") | Q(grade_level=student_profile.enrolled_in)
            )
        elif filter_grade != "all" and filter_grade != "my_level":
            campus_schedules = campus_schedules.filter(grade_level=filter_grade)

        # Apply day filtering
        if filter_day != "all":
            campus_schedules = campus_schedules.filter(day_of_week=filter_day)

        # Group schedules by day
        days_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        schedules_by_day = {}
        for day in days_order:
            schedules_by_day[day] = campus_schedules.filter(day_of_week=day)

        # Get unique grade levels from schedules for filter dropdown
        available_grade_levels = (
            Schedule.objects.filter(campus=student_profile.campus, is_active=True)
            .values_list("grade_level", flat=True)
            .distinct()
            .order_by("grade_level")
        )

        # Convert to list and ensure 'All Levels' is first
        grade_levels = list(available_grade_levels)
        if "All Levels" in grade_levels:
            grade_levels.remove("All Levels")
            grade_levels.insert(0, "All Levels")

        context = {
            "student_profile": student_profile,
            "schedules_by_day": schedules_by_day,
            "days_order": days_order,
            "has_schedule": campus_schedules.exists(),
            "grade_levels": grade_levels,
            "filtered_count": campus_schedules.count(),
            "current_filter": {
                "grade": filter_grade,
                "day": filter_day,
            },
            "current_grade": (
                student_profile.enrolled_in if student_profile.enrolled_in else None
            ),
            "active_page": "schedule",
        }
        return render(request, "student/student_schedule.html", context)

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("home")


@login_required
@never_cache
def teacher_modules(request):
    """Teacher module management page"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile

        # Get filter parameters
        filter_grade = request.GET.get("grade_level", "all")
        filter_subject = request.GET.get("subject", "all")
        filter_quarter = request.GET.get("quarter", "all")
        filter_status = request.GET.get("status", "all")

        # Base queryset
        modules = LearningModule.objects.filter(
            teacher=teacher_profile, campus=teacher_profile.campus
        ).order_by("-created_at")

        # Apply filters
        if filter_grade != "all":
            modules = modules.filter(grade_level=filter_grade)

        if filter_subject != "all":
            modules = modules.filter(subject=filter_subject)

        if filter_quarter != "all":
            modules = modules.filter(quarter=filter_quarter)

        if filter_status == "active":
            modules = modules.filter(is_active=True)
        elif filter_status == "inactive":
            modules = modules.filter(is_active=False)

        # Pagination
        paginator = Paginator(modules, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Statistics
        total_modules = LearningModule.objects.filter(teacher=teacher_profile).count()
        active_modules = LearningModule.objects.filter(
            teacher=teacher_profile, is_active=True
        ).count()
        total_downloads = (
            LearningModule.objects.filter(teacher=teacher_profile).aggregate(
                total=Sum("download_count")
            )["total"]
            or 0
        )

        # Get unique values for filters
        grade_levels = [
            "Grade 7",
            "Grade 8",
            "Grade 9",
            "Grade 10",
            "Grade 11",
            "Grade 12",
        ]
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
        quarters = ["Quarter 1", "Quarter 2", "Quarter 3", "Quarter 4"]

        context = {
            "teacher_profile": teacher_profile,
            "teacher_school": (
                teacher_profile.campus.name
                if teacher_profile.campus
                else "Not Assigned"
            ),
            "active_page": "modules",
            "page_obj": page_obj,
            "modules": page_obj,
            "total_modules": total_modules,
            "active_modules": active_modules,
            "total_downloads": total_downloads,
            "grade_levels": grade_levels,
            "subjects": subjects,
            "quarters": quarters,
            "current_filter": {
                "grade": filter_grade,
                "subject": filter_subject,
                "quarter": filter_quarter,
                "status": filter_status,
            },
        }
        return render(request, "teacher/teacher_modules.html", context)

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def upload_module(request):
    """Upload a new learning module"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile

        if request.method == "POST":
            title = request.POST.get("title")
            description = request.POST.get("description", "")
            subject = request.POST.get("subject")
            grade_level = request.POST.get("grade_level")
            quarter = request.POST.get("quarter")
            pdf_file = request.FILES.get("pdf_file")
            cover_image = request.FILES.get("cover_image")

            # Validation
            if not all([title, subject, grade_level, quarter, pdf_file]):
                messages.error(request, "Please fill in all required fields.")
                return redirect(
                    f"{reverse('manage_subjects')}?subject={subject}&tab=modules"
                )

            # Check file type
            if not pdf_file.name.endswith(".pdf"):
                messages.error(request, "Only PDF files are allowed.")
                return redirect(
                    f"{reverse('manage_subjects')}?subject={subject}&tab=modules"
                )

            # Check file size (max 50MB)
            if pdf_file.size > 50 * 1024 * 1024:
                messages.error(request, "File size must be less than 50MB.")
                return redirect(
                    f"{reverse('manage_subjects')}?subject={subject}&tab=modules"
                )

            # Create module
            module = LearningModule.objects.create(
                teacher=teacher_profile,
                campus=teacher_profile.campus,
                title=title,
                description=description,
                subject=subject,
                grade_level=grade_level,
                quarter=quarter,
                file=pdf_file,
                thumbnail=cover_image,
                is_active=True,
            )

            messages.success(request, f'✅ Module "{title}" uploaded successfully!')

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "module_created",
                {
                    "id": module.id,
                    "title": module.title,
                },
            )

            return redirect(
                f"{reverse('manage_subjects')}?subject={subject}&tab=modules"
            )

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")

    return redirect("manage_subjects")


@login_required
def edit_module(request, module_id):
    """Edit an existing module"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        module = get_object_or_404(
            LearningModule, id=module_id, teacher=teacher_profile
        )

        if request.method == "POST":
            module.title = request.POST.get("title", module.title)
            module.description = request.POST.get("description", module.description)
            module.subject = request.POST.get("subject", module.subject)
            module.grade_level = request.POST.get("grade_level", module.grade_level)
            module.quarter = request.POST.get("quarter", module.quarter)

            # Handle new PDF file if uploaded
            if "pdf_file" in request.FILES:
                new_pdf = request.FILES["pdf_file"]
                if new_pdf.name.endswith(".pdf"):
                    if new_pdf.size <= 50 * 1024 * 1024:
                        if module.file:
                            module.file.delete(save=False)
                        module.file = new_pdf
                    else:
                        messages.error(request, "File size must be less than 50MB.")
                        return redirect(
                            f"{reverse('manage_subjects')}?subject={module.subject}&tab=modules"
                        )
                else:
                    messages.error(request, "Only PDF files are allowed.")
                    return redirect(
                        f"{reverse('manage_subjects')}?subject={module.subject}&tab=modules"
                    )

            # Handle new cover image if uploaded
            if "cover_image" in request.FILES:
                if module.thumbnail:
                    module.thumbnail.delete(save=False)
                module.thumbnail = request.FILES["cover_image"]

            module.save()
            messages.success(
                request, f'✅ Module "{module.title}" updated successfully!'
            )

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "module_updated",
                {
                    "id": module.id,
                    "title": module.title,
                },
            )

            return redirect(
                f"{reverse('manage_subjects')}?subject={module.subject}&tab=modules"
            )

        # GET request - return module data for AJAX
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = {
                "id": module.id,
                "title": module.title,
                "description": module.description,
                "subject": module.subject,
                "grade_level": module.grade_level,
                "quarter": module.quarter,
                "pdf_url": module.file.url if module.file else "",
                "cover_url": module.thumbnail.url if module.thumbnail else "",
            }
            return JsonResponse(data)

        return redirect(
            f"{reverse('manage_subjects')}?subject={module.subject}&tab=modules"
        )

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def delete_module(request, module_id):
    """Delete a module"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        module = get_object_or_404(
            LearningModule, id=module_id, teacher=teacher_profile
        )
        subject = module.subject

        if request.method == "POST":
            title = module.title
            module_id_saved = module.id
            if module.file:
                module.file.delete(save=False)
            if module.thumbnail:
                module.thumbnail.delete(save=False)
            module.delete()
            messages.success(request, f'✅ Module "{title}" deleted successfully!')

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "module_deleted",
                {
                    "id": module_id_saved,
                    "title": title,
                },
            )

        return redirect(f"{reverse('manage_subjects')}?subject={subject}&tab=modules")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def toggle_module(request, module_id):
    """Toggle module active status"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        module = get_object_or_404(
            LearningModule, id=module_id, teacher=teacher_profile
        )

        if request.method == "POST":
            module.is_active = not module.is_active
            module.save()
            status = "activated" if module.is_active else "deactivated"
            messages.success(
                request, f'✅ Module "{module.title}" {status} successfully!'
            )

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "module_updated",
                {
                    "id": module.id,
                    "title": module.title,
                    "is_active": module.is_active,
                },
            )

        return redirect(
            f"{reverse('manage_subjects')}?subject={module.subject}&tab=modules"
        )

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def download_module(request, module_id):
    """Download module (teacher access)"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        module = get_object_or_404(
            LearningModule, id=module_id, teacher=teacher_profile
        )

        # Increment download count
        module.increment_download_count()

        # Serve file
        response = FileResponse(module.file, as_attachment=True)
        return response

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


def teacher_view_module(request, module_id):
    """View module (teacher can view their own modules)"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        module = get_object_or_404(
            LearningModule, id=module_id, teacher=teacher_profile
        )

        # Serve file inline (for viewing in browser)
        response = FileResponse(module.file, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{module.title}.pdf"'
        response["X-Frame-Options"] = "SAMEORIGIN"
        return response

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


@login_required
@xframe_options_exempt
def serve_module_pdf(request, module_id):
    """Serve PDF file with proper headers for embedding"""
    try:
        student_profile = request.user.student_profile
        enrolled_subjects = student_profile.enrolled_subjects()
        module = get_object_or_404(
            LearningModule,
            id=module_id,
            campus=student_profile.campus,
            grade_level=student_profile.enrolled_in,
            is_active=True,
            subject__in=enrolled_subjects,
        )

        # Serve the file with proper headers
        response = FileResponse(module.file, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{module.title}.pdf"'
        response["X-Frame-Options"] = "SAMEORIGIN"  # Changed from DENY to SAMEORIGIN
        return response

    except StudentProfile.DoesNotExist:
        return HttpResponse("Access denied", status=403)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


@login_required
@never_cache
def admin_profile(request):
    """Admin profile page to change username and password"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "change_username":
            # Change username
            new_username = request.POST.get("new_username")
            confirm_username = request.POST.get("confirm_username")

            if not new_username or not confirm_username:
                messages.error(request, "Please fill in all fields.")
            elif new_username != confirm_username:
                messages.error(request, "Usernames do not match.")
            elif (
                User.objects.filter(username=new_username)
                .exclude(id=request.user.id)
                .exists()
            ):
                messages.error(
                    request, "Username already taken. Please choose another."
                )
            else:
                # Update username
                request.user.username = new_username
                request.user.save()
                messages.success(request, "Username updated successfully!")

        elif action == "change_password":
            # Change password
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not current_password or not new_password or not confirm_password:
                messages.error(request, "Please fill in all fields.")
            elif not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            elif len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
            else:
                # Update password
                request.user.set_password(new_password)
                request.user.save()
                # Keep the user logged in
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully!")

        return redirect("admin_profile")

    context = {
        "active_page": "profile",
    }
    return render(request, "administrator/admin_profile.html", context)


@login_required
@never_cache
def create_admin(request):
    """Create a new admin account (superuser)"""
    if not request.user.is_superuser:  # Only superusers can create new admins
        messages.error(request, "Access denied. Superuser privileges required.")
        return redirect("admin_dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")

        # Validation
        if not all([username, email, password]):
            messages.error(request, "Please fill in all required fields.")
            return redirect("create_admin")

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return redirect("create_admin")

        if User.objects.filter(email=email).exists():
            messages.error(request, f'Email "{email}" is already registered.')
            return redirect("create_admin")

        try:
            # Create superuser
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            messages.success(
                request, f"✅ Admin account created successfully for {username}!"
            )
            return redirect("admin_dashboard")

        except Exception as e:
            messages.error(request, f"Error creating admin: {str(e)}")
            return redirect("create_admin")

    context = {
        "active_page": "create_admin",
    }
    return render(request, "administrator/create_admin.html", context)


@login_required
@never_cache
def teacher_profile(request):
    """Teacher profile page to change username and password"""
    # Check if user is a teacher
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "change_username":
            # Change username
            new_username = request.POST.get("new_username")
            confirm_username = request.POST.get("confirm_username")

            if not new_username or not confirm_username:
                messages.error(request, "Please fill in all fields.")
            elif new_username != confirm_username:
                messages.error(request, "Usernames do not match.")
            elif (
                User.objects.filter(username=new_username)
                .exclude(id=request.user.id)
                .exists()
            ):
                messages.error(
                    request, "Username already taken. Please choose another."
                )
            else:
                # Update username
                request.user.username = new_username
                request.user.save()
                messages.success(request, "Username updated successfully!")

        elif action == "change_password":
            # Change password
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not current_password or not new_password or not confirm_password:
                messages.error(request, "Please fill in all fields.")
            elif not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            elif len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
            else:
                # Update password
                request.user.set_password(new_password)
                request.user.save()
                # Keep the user logged in
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully!")

        return redirect("teacher_profile")

    # Get teacher profile info
    try:
        teacher_profile = request.user.teacher_profile
        teacher_school = (
            teacher_profile.campus.name if teacher_profile.campus else "Not Assigned"
        )
    except:
        teacher_school = "Not Assigned"

    context = {
        "teacher_school": teacher_school,
        "active_page": "profile",
    }
    return render(request, "teacher/teacher_profile.html", context)


@login_required
@never_cache
def teacher_announcements(request):
    """Teacher announcements management page"""
    # Check if user is a teacher
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile

        # Get filter parameters
        filter_audience = request.GET.get("audience", "all")
        filter_priority = request.GET.get("priority", "all")
        filter_status = request.GET.get("status", "all")

        # Base queryset
        announcements = Announcement.objects.filter(
            teacher=teacher_profile, campus=teacher_profile.campus
        ).order_by("-created_at")

        # Apply filters
        if filter_audience != "all":
            announcements = announcements.filter(audience=filter_audience)

        if filter_priority != "all":
            announcements = announcements.filter(priority=filter_priority)

        if filter_status == "active":
            announcements = announcements.filter(is_active=True)
        elif filter_status == "inactive":
            announcements = announcements.filter(is_active=False)

        # Pagination
        paginator = Paginator(announcements, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Statistics
        total_announcements = Announcement.objects.filter(
            teacher=teacher_profile
        ).count()
        active_announcements = Announcement.objects.filter(
            teacher=teacher_profile, is_active=True
        ).count()

        context = {
            "teacher_profile": teacher_profile,
            "teacher_school": (
                teacher_profile.campus.name
                if teacher_profile.campus
                else "Not Assigned"
            ),
            "active_page": "announcements",
            "page_obj": page_obj,
            "announcements": page_obj,
            "total_announcements": total_announcements,
            "active_announcements": active_announcements,
            "audience_choices": Announcement.AUDIENCE_CHOICES,
            "priority_choices": Announcement.PRIORITY_CHOICES,
            "current_filter": {
                "audience": filter_audience,
                "priority": filter_priority,
                "status": filter_status,
            },
        }
        return render(request, "teacher/teacher_announcements.html", context)

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def create_announcement(request):
    """Create a new announcement"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile

        if request.method == "POST":
            title = request.POST.get("title")
            content = request.POST.get("content")
            audience = request.POST.get("audience")
            priority = request.POST.get("priority")
            attachment = request.FILES.get("attachment")

            # Validation
            if not all([title, content, audience, priority]):
                messages.error(request, "Please fill in all required fields.")
                return redirect("teacher_announcements")

            # Create announcement
            announcement = Announcement.objects.create(
                teacher=teacher_profile,
                campus=teacher_profile.campus,
                title=title,
                content=content,
                audience=audience,
                priority=priority,
                attachment=attachment,
                is_active=True,
            )

            messages.success(
                request, f'✅ Announcement "{title}" created successfully!'
            )

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "announcement_created",
                {
                    "id": announcement.id,
                    "title": announcement.title,
                },
            )

            return redirect("teacher_announcements")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")

    return redirect("teacher_announcements")


@login_required
def edit_announcement(request, announcement_id):
    """Edit an existing announcement"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        announcement = get_object_or_404(
            Announcement, id=announcement_id, teacher=teacher_profile
        )

        if request.method == "POST":
            announcement.title = request.POST.get("title", announcement.title)
            announcement.content = request.POST.get("content", announcement.content)
            announcement.audience = request.POST.get("audience", announcement.audience)
            announcement.priority = request.POST.get("priority", announcement.priority)

            # Handle new attachment if uploaded
            if "attachment" in request.FILES:
                # Delete old attachment
                if announcement.attachment:
                    announcement.attachment.delete(save=False)
                announcement.attachment = request.FILES["attachment"]

            announcement.save()
            messages.success(
                request, f'✅ Announcement "{announcement.title}" updated successfully!'
            )

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "announcement_updated",
                {
                    "id": announcement.id,
                    "title": announcement.title,
                },
            )

            return redirect("teacher_announcements")

        # GET request - return announcement data for AJAX
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = {
                "id": announcement.id,
                "title": announcement.title,
                "content": announcement.content,
                "audience": announcement.audience,
                "priority": announcement.priority,
                "attachment_url": (
                    announcement.attachment.url if announcement.attachment else ""
                ),
            }
            return JsonResponse(data)

        return redirect("teacher_announcements")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def delete_announcement(request, announcement_id):
    """Delete an announcement"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        announcement = get_object_or_404(
            Announcement, id=announcement_id, teacher=teacher_profile
        )

        if request.method == "POST":
            title = announcement.title
            # Delete attachment if exists
            if announcement.attachment:
                announcement.attachment.delete(save=False)
            announcement.delete()
            messages.success(
                request, f'✅ Announcement "{title}" deleted successfully!'
            )

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "announcement_deleted",
                {
                    "id": announcement_id,
                    "title": title,
                },
            )

        return redirect("teacher_announcements")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def toggle_announcement(request, announcement_id):
    """Toggle announcement active status"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        announcement = get_object_or_404(
            Announcement, id=announcement_id, teacher=teacher_profile
        )

        if request.method == "POST":
            announcement.is_active = not announcement.is_active
            announcement.save()
            status = "activated" if announcement.is_active else "deactivated"
            messages.success(
                request,
                f'✅ Announcement "{announcement.title}" {status} successfully!',
            )

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "announcement_updated",
                {
                    "id": announcement.id,
                    "title": announcement.title,
                    "is_active": announcement.is_active,
                },
            )

        return redirect("teacher_announcements")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
@never_cache
def teacher_assignments(request):
    """Teacher assignments management page"""
    # Check if user is a teacher
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile

        # Get filter parameters
        filter_grade = request.GET.get("grade_level", "all")
        filter_subject = request.GET.get("subject", "all")
        filter_status = request.GET.get("status", "all")

        # Base queryset
        assignments = Assignment.objects.filter(
            teacher=teacher_profile, campus=teacher_profile.campus
        ).order_by("-created_at")

        # Apply filters
        if filter_grade != "all":
            assignments = assignments.filter(grade_level=filter_grade)

        if filter_subject != "all":
            assignments = assignments.filter(subject=filter_subject)

        if filter_status == "active":
            assignments = assignments.filter(is_active=True)
        elif filter_status == "inactive":
            assignments = assignments.filter(is_active=False)

        # Pagination
        paginator = Paginator(assignments, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Statistics
        total_assignments = Assignment.objects.filter(teacher=teacher_profile).count()
        active_assignments = Assignment.objects.filter(
            teacher=teacher_profile, is_active=True
        ).count()

        # Get submission counts for each assignment
        for assignment in page_obj:
            assignment.submission_count = AssignmentSubmission.objects.filter(
                assignment=assignment
            ).count()
            assignment.graded_count = AssignmentSubmission.objects.filter(
                assignment=assignment, status="graded"
            ).count()

        context = {
            "teacher_profile": teacher_profile,
            "teacher_school": (
                teacher_profile.campus.name
                if teacher_profile.campus
                else "Not Assigned"
            ),
            "active_page": "assignments",
            "page_obj": page_obj,
            "assignments": page_obj,
            "total_assignments": total_assignments,
            "active_assignments": active_assignments,
            "grade_levels": [
                "Grade 7",
                "Grade 8",
                "Grade 9",
                "Grade 10",
                "Grade 11",
                "Grade 12",
            ],
            "subjects": Assignment.SUBJECT_CHOICES,
            "current_filter": {
                "grade": filter_grade,
                "subject": filter_subject,
                "status": filter_status,
            },
        }
        return render(request, "teacher/teacher_assignments.html", context)

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def create_assignment(request):
    """Create a new assignment"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile

        if request.method == "POST":
            title = request.POST.get("title")
            description = request.POST.get("description")
            subject = request.POST.get("subject")
            grade_level = request.POST.get("grade_level")
            due_date = request.POST.get("due_date")
            total_points = request.POST.get("total_points", 100)
            attachment = request.FILES.get("attachment")

            # Validation
            if not all([title, description, subject, grade_level, due_date]):
                messages.error(request, "Please fill in all required fields.")
                return redirect("teacher_assignments")

            # Convert due_date string to datetime
            from datetime import datetime

            due_date_obj = datetime.strptime(due_date, "%Y-%m-%dT%H:%M")

            # Create assignment
            assignment = Assignment.objects.create(
                teacher=teacher_profile,
                campus=teacher_profile.campus,
                title=title,
                description=description,
                subject=subject,
                grade_level=grade_level,
                due_date=due_date_obj,
                total_points=total_points,
                attachment=attachment,
                is_active=True,
            )

            messages.success(request, f'✅ Assignment "{title}" created successfully!')

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "assignment_created",
                {
                    "id": assignment.id,
                    "title": assignment.title,
                },
            )

            return redirect(f"{reverse('manage_subjects')}?subject={subject}")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")

    return redirect("manage_subjects")


@login_required
def edit_assignment(request, assignment_id):
    """Edit an existing assignment"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        assignment = get_object_or_404(
            Assignment, id=assignment_id, teacher=teacher_profile
        )

        if request.method == "POST":
            assignment.title = request.POST.get("title", assignment.title)
            assignment.description = request.POST.get(
                "description", assignment.description
            )
            assignment.subject = request.POST.get("subject", assignment.subject)
            assignment.grade_level = request.POST.get(
                "grade_level", assignment.grade_level
            )
            assignment.total_points = request.POST.get(
                "total_points", assignment.total_points
            )

            # Update due date
            due_date = request.POST.get("due_date")
            if due_date:
                from datetime import datetime

                assignment.due_date = datetime.strptime(due_date, "%Y-%m-%dT%H:%M")

            # Handle new attachment if uploaded
            if "attachment" in request.FILES:
                # Delete old attachment
                if assignment.attachment:
                    assignment.attachment.delete(save=False)
                assignment.attachment = request.FILES["attachment"]

            assignment.save()
            messages.success(
                request, f'✅ Assignment "{assignment.title}" updated successfully!'
            )

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "assignment_updated",
                {
                    "id": assignment.id,
                    "title": assignment.title,
                },
            )

            return redirect("teacher_assignments")

        # GET request - return assignment data for AJAX
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = {
                "id": assignment.id,
                "title": assignment.title,
                "description": assignment.description,
                "subject": assignment.subject,
                "grade_level": assignment.grade_level,
                "due_date": assignment.due_date.strftime("%Y-%m-%dT%H:%M"),
                "total_points": assignment.total_points,
                "attachment_url": (
                    assignment.attachment.url if assignment.attachment else ""
                ),
            }
            return JsonResponse(data)

        return redirect("teacher_assignments")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def delete_assignment(request, assignment_id):
    """Delete an assignment"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        assignment = get_object_or_404(
            Assignment, id=assignment_id, teacher=teacher_profile
        )

        if request.method == "POST":
            title = assignment.title
            # Delete attachment if exists
            if assignment.attachment:
                assignment.attachment.delete(save=False)
            assignment.delete()
            messages.success(request, f'✅ Assignment "{title}" deleted successfully!')

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "assignment_deleted",
                {
                    "id": assignment_id,
                    "title": title,
                },
            )

        return redirect("manager_subjects")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def toggle_assignment(request, assignment_id):
    """Toggle assignment active status"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        assignment = get_object_or_404(
            Assignment, id=assignment_id, teacher=teacher_profile
        )

        if request.method == "POST":
            assignment.is_active = not assignment.is_active
            assignment.save()
            status = "activated" if assignment.is_active else "deactivated"
            messages.success(
                request, f'✅ Assignment "{assignment.title}" {status} successfully!'
            )

            # ── REAL-TIME: notify all dashboards ──
            broadcast_event(
                "assignment_updated",
                {
                    "id": assignment.id,
                    "title": assignment.title,
                    "is_active": assignment.is_active,
                },
            )

        return redirect("teacher_assignments")

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def view_submissions(request, assignment_id):
    """View submissions for an assignment"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        teacher_profile = request.user.teacher_profile
        assignment = get_object_or_404(
            Assignment, id=assignment_id, teacher=teacher_profile
        )

        # Get all submissions for this assignment
        submissions = AssignmentSubmission.objects.filter(
            assignment=assignment
        ).select_related("student__user")

        # Statistics
        total_submissions = submissions.count()
        graded_count = submissions.filter(status="graded").count()
        pending_count = submissions.filter(status="submitted").count()
        late_count = submissions.filter(status="late").count()

        context = {
            "teacher_profile": teacher_profile,
            "teacher_school": (
                teacher_profile.campus.name
                if teacher_profile.campus
                else "Not Assigned"
            ),
            "assignment": assignment,
            "submissions": submissions,
            "total_submissions": total_submissions,
            "graded_count": graded_count,
            "pending_count": pending_count,
            "late_count": late_count,
        }
        return render(request, "teacher/teacher_submissions.html", context)

    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("home")


@login_required
def grade_submission(request, submission_id):
    """Grade a student submission"""
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    try:
        submission = get_object_or_404(AssignmentSubmission, id=submission_id)

        # Check if the assignment belongs to this teacher
        if submission.assignment.teacher.user != request.user:
            messages.error(request, "Access denied.")
            return redirect("home")

        if request.method == "POST":
            grade = request.POST.get("grade")
            feedback = request.POST.get("feedback")

            if grade:
                submission.grade = grade
                submission.feedback = feedback
                submission.save()
                messages.success(request, f"✅ Submission graded successfully!")

                # ── REAL-TIME: notify the student their submission was graded ──
                broadcast_event(
                    "submission_graded",
                    {
                        "id": submission.id,
                        "assignment_title": submission.assignment.title,
                        "student_id": submission.student.id,
                    },
                )

        return redirect("view_submissions", assignment_id=submission.assignment.id)

    except AssignmentSubmission.DoesNotExist:
        messages.error(request, "Submission not found.")
        return redirect("teacher_assignments")


@login_required
@never_cache
def student_assignments(request):
    """Student assignments page - shows assignments for their grade level"""
    try:
        student_profile = request.user.student_profile

        # Check if student has grade level assigned
        if not student_profile.enrolled_in:
            context = {
                "student_profile": student_profile,
                "has_grade_level": False,
                "has_subject_enrollment": False,
                "assignments": [],
                "active_page": "assignments",
            }
            return render(request, "student/student_assignments.html", context)

        enrolled_subjects = student_profile.enrolled_subjects()
        if not enrolled_subjects:
            return redirect("student_subjects")

        # Get filter parameters
        filter_subject = request.GET.get("subject", "all")
        filter_status = request.GET.get("status", "all")

        # Base queryset - enrolled subjects only
        assignments = Assignment.objects.filter(
            campus=student_profile.campus,
            grade_level=student_profile.enrolled_in,
            is_active=True,
            subject__in=enrolled_subjects,
        ).order_by("-created_at")

        # Apply filters
        if filter_subject != "all":
            if filter_subject not in enrolled_subjects:
                assignments = assignments.none()
            else:
                assignments = assignments.filter(subject=filter_subject)

        # Get student's submissions
        submissions = AssignmentSubmission.objects.filter(
            student=student_profile
        ).select_related("assignment")

        submitted_assignment_ids = submissions.values_list("assignment_id", flat=True)

        # Create a dictionary of submission status for each assignment
        submission_status = {}
        for submission in submissions:
            submission_status[submission.assignment_id] = {
                "status": submission.status,
                "grade": submission.grade,
                "feedback": submission.feedback,
                "submitted_at": submission.submitted_at,
            }

        # Calculate pending count for badge
        pending_count = assignments.exclude(id__in=submitted_assignment_ids).count()

        # Get unique subjects for filter
        subjects_list = (
            Assignment.objects.filter(
                campus=student_profile.campus,
                grade_level=student_profile.enrolled_in,
                is_active=True,
                subject__in=enrolled_subjects,
            )
            .values_list("subject", flat=True)
            .distinct()
        )

        context = {
            "student_profile": student_profile,
            "assignments": assignments,
            "submitted_ids": list(submitted_assignment_ids),
            "submission_status": submission_status,
            "subjects_list": subjects_list,
            "pending_count": pending_count,
            "current_filter": {
                "subject": filter_subject,
                "status": filter_status,
            },
            "has_grade_level": True,
            "has_subject_enrollment": True,
            "current_grade": student_profile.enrolled_in,
            "active_page": "assignments",
        }
        return render(request, "student/student_subjects.html", context)

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("student_subjects")


@login_required
@never_cache
def student_my_submissions(request):
    """Student submissions page - shows all their submissions"""
    try:
        student_profile = request.user.student_profile

        # Get all submissions for this student
        submissions = (
            AssignmentSubmission.objects.filter(student=student_profile)
            .select_related("assignment")
            .order_by("-submitted_at")
        )

        # Statistics
        total_submissions = submissions.count()
        graded_count = submissions.filter(status="graded").count()
        pending_count = submissions.filter(status="submitted").count()
        late_count = submissions.filter(status="late").count()

        context = {
            "student_profile": student_profile,
            "submissions": submissions,
            "total_submissions": total_submissions,
            "graded_count": graded_count,
            "pending_count": pending_count,
            "late_count": late_count,
            "active_page": "submissions",
        }
        return render(request, "student/student_subjects.html", context)

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("student_subjects")


@login_required
def submit_assignment(request, assignment_id):
    """Submit an assignment"""
    try:
        student_profile = request.user.student_profile
        enrolled_subjects = student_profile.enrolled_subjects()
        assignment = get_object_or_404(
            Assignment,
            id=assignment_id,
            campus=student_profile.campus,
            grade_level=student_profile.enrolled_in,
            is_active=True,
            subject__in=enrolled_subjects,
        )

        # Check if already submitted
        existing_submission = AssignmentSubmission.objects.filter(
            assignment=assignment, student=student_profile
        ).first()

        if existing_submission:
            messages.warning(request, "You have already submitted this assignment.")
            return redirect("student_subjects")

        if request.method == "POST":
            submission_file = request.FILES.get("submission_file")
            comments = request.POST.get("comments", "")

            if not submission_file:
                messages.error(request, "Please upload a file.")
                return redirect("student_subjects")

            # Check file size (max 20MB)
            if submission_file.size > 20 * 1024 * 1024:
                messages.error(request, "File size must be less than 20MB.")
                return redirect("student_subjects")

            # Check if submission is late
            from django.utils import timezone

            status = "late" if timezone.now() > assignment.due_date else "submitted"

            # Create submission
            AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student_profile,
                submission_file=submission_file,
                comments=comments,
                status=status,
            )

            messages.success(
                request, f'✅ Assignment "{assignment.title}" submitted successfully!'
            )

            # ── REAL-TIME: notify teacher of new submission ──
            broadcast_event(
                "assignment_submitted",
                {
                    "assignment_id": assignment.id,
                    "assignment_title": assignment.title,
                    "student_name": request.user.get_full_name(),
                },
            )

            return redirect("student_subjects")

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("student_subjects")

    return redirect("student_subjects")


@login_required
@never_cache
def student_announcements(request):
    """Student announcements page - shows announcements from teachers"""
    try:
        student_profile = request.user.student_profile

        # Build the student's grade filter for announcements
        # Announcements target either "all" students or the specific grade level
        from django.db.models import Q

        grade_mapping = {
            "Grade 7": "grade_7",
            "Grade 8": "grade_8",
            "Grade 9": "grade_9",
            "Grade 10": "grade_10",
            "Grade 11": "grade_11",
            "Grade 12": "grade_12",
        }

        grade_audience = grade_mapping.get(student_profile.enrolled_in, "")

        # Get filter parameters
        filter_priority = request.GET.get("priority", "all")
        search_query = request.GET.get("search", "").strip()

        # Base queryset - announcements from teachers at the same campus
        announcements = (
            Announcement.objects.filter(
                campus=student_profile.campus,
                is_active=True,
            )
            .filter(
                # Announcements targeting "all" students or the student's specific grade
                Q(audience="all")
                | Q(audience=grade_audience)
            )
            .select_related("teacher__user")
            .order_by("-created_at")
        )

        # Apply priority filter
        if filter_priority != "all":
            announcements = announcements.filter(priority=filter_priority)

        # Apply search filter
        if search_query:
            announcements = announcements.filter(
                Q(title__icontains=search_query) | Q(content__icontains=search_query)
            )

        # Pagination
        paginator = Paginator(announcements, 8)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Statistics
        total_announcements = (
            Announcement.objects.filter(
                campus=student_profile.campus,
                is_active=True,
            )
            .filter(Q(audience="all") | Q(audience=grade_audience))
            .count()
        )

        urgent_announcements = announcements.filter(priority="urgent").count()
        high_announcements = announcements.filter(priority="high").count()

        context = {
            "student_profile": student_profile,
            "announcements": page_obj,
            "total_announcements": total_announcements,
            "urgent_count": urgent_announcements,
            "high_count": high_announcements,
            "current_filter": {
                "priority": filter_priority,
                "search": search_query,
            },
            "current_grade": (
                student_profile.enrolled_in
                if student_profile.enrolled_in
                else "Not Assigned"
            ),
            "active_page": "announcements",
        }
        return render(request, "student/student_announcements.html", context)

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("home")


@login_required
@staff_member_required
@never_cache
def campus_management(request):
    """Campus management page for admin"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    campuses = Campus.objects.all().order_by("name")

    context = {
        "campuses": campuses,
        "total_campuses": campuses.count(),
        "active_campuses": campuses.filter(is_active=True).count(),
        "active_page": "campuses",
    }
    return render(request, "administrator/campus_management.html", context)


@login_required
@staff_member_required
def create_campus(request):
    """Create a new campus"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        address = request.POST.get("address", "").strip()
        contact_number = request.POST.get("contact_number", "").strip()

        if not name:
            messages.error(request, "Campus name is required.")
            return redirect("campus_management")

        # Check if campus already exists
        if Campus.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Campus "{name}" already exists.')
            return redirect("campus_management")

        # Generate code if not provided
        if not code:
            code = name.upper().replace(" ", "_")

        # Check if code already exists
        if Campus.objects.filter(code__iexact=code).exists():
            messages.error(
                request,
                f'Campus code "{code}" already exists. Please provide a different code.',
            )
            return redirect("campus_management")

        try:
            campus = Campus.objects.create(
                name=name,
                code=code,
                address=address,
                contact_number=contact_number,
                is_active=True,
            )
            messages.success(request, f'✅ Campus "{name}" created successfully!')
        except Exception as e:
            messages.error(request, f"Error creating campus: {str(e)}")

        return redirect("campus_management")

    return redirect("campus_management")


@login_required
@staff_member_required
def edit_campus(request, campus_id):
    """Edit an existing campus"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    campus = get_object_or_404(Campus, id=campus_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        address = request.POST.get("address", "").strip()
        contact_number = request.POST.get("contact_number", "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Campus name is required.")
            return redirect("campus_management")

        # Check if name already exists (excluding current campus)
        if Campus.objects.filter(name__iexact=name).exclude(id=campus.id).exists():
            messages.error(request, f'Campus "{name}" already exists.')
            return redirect("campus_management")

        # Generate code if not provided
        if not code:
            code = name.upper().replace(" ", "_")

        # Check if code already exists (excluding current campus)
        if Campus.objects.filter(code__iexact=code).exclude(id=campus.id).exists():
            messages.error(
                request,
                f'Campus code "{code}" already exists. Please provide a different code.',
            )
            return redirect("campus_management")

        campus.name = name
        campus.code = code
        campus.address = address
        campus.contact_number = contact_number
        campus.is_active = is_active
        campus.save()

        messages.success(request, f'✅ Campus "{name}" updated successfully!')
        return redirect("campus_management")

    return redirect("campus_management")


@login_required
@staff_member_required
def delete_campus(request, campus_id):
    """Delete a campus"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    campus = get_object_or_404(Campus, id=campus_id)

    # Check if campus is in use
    has_students = StudentProfile.objects.filter(campus=campus).exists()
    has_teachers = Teacher.objects.filter(campus=campus).exists()
    has_schedules = Schedule.objects.filter(campus=campus).exists()
    has_modules = LearningModule.objects.filter(campus=campus).exists()

    if has_students or has_teachers or has_schedules or has_modules:
        messages.error(
            request,
            f'Cannot delete "{campus.name}" because it has associated records. Deactivate it instead.',
        )
        return redirect("campus_management")

    if request.method == "POST":
        name = campus.name
        campus.delete()
        messages.success(request, f'✅ Campus "{name}" deleted successfully!')

    return redirect("campus_management")


@login_required
@staff_member_required
def toggle_campus(request, campus_id):
    """Toggle campus active status"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect("home")

    campus = get_object_or_404(Campus, id=campus_id)

    if request.method == "POST":
        campus.is_active = not campus.is_active
        campus.save()
        status = "activated" if campus.is_active else "deactivated"
        messages.success(request, f'✅ Campus "{campus.name}" {status} successfully!')

    return redirect("campus_management")


def get_active_campuses(request):
    """API endpoint to get active campuses for registration page"""
    campuses = (
        Campus.objects.filter(is_active=True)
        .order_by("name")
        .values("id", "name", "code")
    )
    return JsonResponse(list(campuses), safe=False)


@login_required
@staff_member_required
def get_student_details(request, student_id):
    """API endpoint to get comprehensive student details for modal"""
    try:
        student = StudentProfile.objects.select_related("user", "campus").get(
            id=student_id
        )

        # Helper function to format lists
        def format_list(comma_separated):
            if not comma_separated:
                return []
            return [item.strip() for item in comma_separated.split(",")]

        # Basic Information
        data = {
            "id": student.id,
            "registration_date": (
                student.registration_date.strftime("%B %d, %Y")
                if student.registration_date
                else None
            ),
            # Personal Information
            "lrn": student.lrn,
            "first_name": student.user.first_name,
            "last_name": student.user.last_name,
            "middle_name": student.middle_name,
            "extension_name": student.extension_name,
            "email": student.user.email,
            "birthdate": (
                student.birthdate.strftime("%B %d, %Y") if student.birthdate else None
            ),
            "age": student.age,
            "gender": student.gender,
            "place_of_birth": student.place_of_birth,
            "civil_status": student.civil_status,
            "religion": student.religion,
            "mother_tongue": student.mother_tongue,
            # Indigenous People
            "is_indigenous_people": student.is_indigenous_people,
            "indigenous_specify": student.indigenous_specify,
            # 4Ps Information
            "is_4ps_beneficiary": student.is_4ps_beneficiary,
            "fourps_household_id": student.fourps_household_id,
            # Contact Information
            "phone": student.phone,
            "contact_numbers": student.contact_numbers,
            # Current Address
            "street_name": student.street_name,
            "province": student.province,
            "municipality": student.municipality,
            "barangay": student.barangay,
            "zip_code": student.zip_code,
            "address": student.address,
            # Permanent Address
            "same_address": student.same_address,
            "permanent_street_name": student.permanent_street_name,
            "permanent_province": student.permanent_province,
            "permanent_municipality": student.permanent_municipality,
            "permanent_barangay": student.permanent_barangay,
            "permanent_zip_code": student.permanent_zip_code,
            # PWD Information
            "is_pwd": student.is_pwd,
            "has_pwd_id": student.has_pwd_id,
            "disability_types": format_list(student.disability_types),
            "disability_subtypes": format_list(student.disability_subtypes),
            # Grade Levels
            "last_grade_levels": format_list(student.last_grade_levels),
            # ALS History
            "attended_als_before": student.attended_als_before,
            "als_programs": format_list(student.als_programs),
            "als_completed": student.als_completed,
            "als_not_completed_reason": student.als_not_completed_reason,
            # Reasons Not Schooling
            "reasons_not_schooling": format_list(student.reasons_not_schooling),
            "reason_not_schooling_other": student.reason_not_schooling_other,
            # Learning Center
            "learning_center_distance": student.learning_center_distance,
            "learning_center_transport": student.learning_center_transport,
            "learning_center_transport_other": student.learning_center_transport_other,
            "travel_time": student.travel_time,
            # Weekly Availability
            "availability": {
                "Monday": student.availability_monday,
                "Tuesday": student.availability_tuesday,
                "Wednesday": student.availability_wednesday,
                "Thursday": student.availability_thursday,
                "Friday": student.availability_friday,
                "Saturday": student.availability_saturday,
                "Sunday": student.availability_sunday,
            },
            # Parents/Guardians (combined names)
            "father_name": f"{student.father_first_name or ''} {student.father_middle_name or ''} {student.father_last_name or ''}".strip(),
            "mother_name": f"{student.mother_first_name or ''} {student.mother_middle_name or ''} {student.mother_last_name or ''}".strip(),
            "guardian_name": f"{student.guardian_first_name or ''} {student.guardian_middle_name or ''} {student.guardian_last_name or ''}".strip(),
            # Parents/Guardians (individual fields)
            "father_first_name": student.father_first_name,
            "father_middle_name": student.father_middle_name,
            "father_last_name": student.father_last_name,
            "mother_first_name": student.mother_first_name,
            "mother_middle_name": student.mother_middle_name,
            "mother_last_name": student.mother_last_name,
            "guardian_first_name": student.guardian_first_name,
            "guardian_middle_name": student.guardian_middle_name,
            "guardian_last_name": student.guardian_last_name,
            # Learning Modalities
            "learning_modalities": format_list(student.learning_modalities),
            "criteria_plan": format_list(student.criteria_plan),
            # Campus and Status
            "campus": student.campus.name if student.campus else None,
            "campus_id": student.campus.id if student.campus else None,
            "enrolled_in": student.enrolled_in,
            "status": student.status,
            # All active campuses for dropdown
            "campuses": list(
                Campus.objects.filter(is_active=True)
                .order_by("name")
                .values("id", "name")
            ),
            # Requirement Status
            "bc_status": student.bc_status,
            "vid_status": student.vid_status,
            # Documents
            "documents": [],
        }

        # Add document info
        if student.birth_certificate:
            data["documents"].append(
                {
                    "name": "Birth Certificate",
                    "url": student.birth_certificate.url,
                    "icon": (
                        "file-pdf"
                        if student.birth_certificate.name.endswith(".pdf")
                        else "file-image"
                    ),
                }
            )

        if student.valid_id:
            data["documents"].append(
                {
                    "name": "Valid ID",
                    "url": student.valid_id.url,
                    "icon": (
                        "file-pdf"
                        if student.valid_id.name.endswith(".pdf")
                        else "file-image"
                    ),
                }
            )

        return JsonResponse(data)

    except StudentProfile.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)


@login_required
@staff_member_required
def get_student_documents(request, student_id):
    """API endpoint to get student documents"""
    try:
        student = StudentProfile.objects.get(id=student_id)

        print(f"Debug - Student {student_id}:")
        print(f"  LRN: {student.lrn}")
        print(f"  Birth Cert: {student.birth_certificate}")
        print(f"  Valid ID: {student.valid_id}")
        print(
            f"  Birth Cert URL: {student.birth_certificate.url if student.birth_certificate else 'None'}"
        )
        print(f"  Valid ID URL: {student.valid_id.url if student.valid_id else 'None'}")

        data = {"lrn": student.lrn, "birth_certificate": None, "valid_id": None}

        if student.birth_certificate:
            data["birth_certificate"] = {
                "url": student.birth_certificate.url,
                "name": student.birth_certificate.name,
                "uploaded_at": (
                    student.documents_uploaded_at.strftime("%Y-%m-%d %H:%M")
                    if student.documents_uploaded_at
                    else "Unknown"
                ),
            }

        if student.valid_id:
            data["valid_id"] = {
                "url": student.valid_id.url,
                "name": student.valid_id.name,
                "uploaded_at": (
                    student.documents_uploaded_at.strftime("%Y-%m-%d %H:%M")
                    if student.documents_uploaded_at
                    else "Unknown"
                ),
            }

        return JsonResponse(data)

    except StudentProfile.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)


@login_required
@login_required
@never_cache
def manage_subjects(request):
    try:
        teacher = request.user.teacher_profile
    except Teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found.")
        return redirect("teacher_dashboard")

    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect("home")

    valid_subjects = {value for value, _label in SUBJECT_CHOICES}

    # ── Create / delete subject ──────────────────────────────
    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "create_subject":
            subject_name = request.POST.get("subject_name", "").strip()
            grade_level = request.POST.get("grade_level", "All Levels").strip()
            if subject_name not in valid_subjects:
                messages.error(request, "Invalid subject selected.")
            elif TeacherSubject.objects.filter(
                teacher=teacher, subject=subject_name
            ).exists():
                messages.warning(
                    request, f'"{subject_name}" is already in your subject list.'
                )
            else:
                TeacherSubject.objects.create(
                    teacher=teacher,
                    subject=subject_name,
                    grade_level=grade_level or "All Levels",
                )
                messages.success(request, f'Subject "{subject_name}" added.')
            if subject_name in valid_subjects:
                return redirect(f"{reverse('manage_subjects')}?subject={subject_name}")
            return redirect("manage_subjects")

        if action == "delete_subject":
            subject_name = request.POST.get("subject_name", "").strip()
            try:
                teacher_subject = TeacherSubject.objects.get(
                    teacher=teacher, subject=subject_name
                )
            except TeacherSubject.DoesNotExist:
                messages.error(request, "Subject not found in your list.")
                return redirect("manage_subjects")

            # Remove this teacher's modules and assignments for the subject
            module_count = LearningModule.objects.filter(
                teacher=teacher, subject=subject_name
            ).count()
            assignment_count = Assignment.objects.filter(
                teacher=teacher, subject=subject_name
            ).count()
            LearningModule.objects.filter(
                teacher=teacher, subject=subject_name
            ).delete()
            Assignment.objects.filter(
                teacher=teacher, subject=subject_name
            ).delete()
            teacher_subject.delete()

            messages.success(
                request,
                f'Subject "{subject_name}" deleted'
                f" ({module_count} module(s), {assignment_count} assignment(s) removed).",
            )
            return redirect("manage_subjects")

    # ── Subjects the teacher has added ───────────────────────
    teacher_subjects = TeacherSubject.objects.filter(teacher=teacher).order_by(
        "subject"
    )
    subjects_with_counts = []
    for ts in teacher_subjects:
        value = ts.subject
        label = dict(SUBJECT_CHOICES).get(value, value)
        module_count = LearningModule.objects.filter(
            teacher=teacher, subject=value
        ).count()
        assignment_count = Assignment.objects.filter(
            teacher=teacher, subject=value
        ).count()
        submission_count = AssignmentSubmission.objects.filter(
            assignment__teacher=teacher,
            assignment__subject=value,
        ).count()
        subjects_with_counts.append(
            {
                "value": value,
                "label": label,
                "module_count": module_count,
                "assignment_count": assignment_count,
                "submission_count": submission_count,
                "grade_level": ts.grade_level,
            }
        )

    # Choices not yet added (for Add Subject modal)
    owned = {s["value"] for s in subjects_with_counts}
    available_subject_choices = [
        (value, label)
        for value, label in SUBJECT_CHOICES
        if value not in owned
    ]

    # ---- Active subject ----
    active_subject = request.GET.get("subject", None)
    owned_values = [s["value"] for s in subjects_with_counts]
    if active_subject not in owned_values:
        active_subject = owned_values[0] if owned_values else None

    # ---- Modules ----
    modules_qs = LearningModule.objects.filter(teacher=teacher)
    if active_subject:
        modules_qs = modules_qs.filter(subject=active_subject)

    grade_filter = request.GET.get("grade_level", "all")
    quarter_filter = request.GET.get("quarter", "all")
    status_filter = request.GET.get("status", "all")

    if grade_filter != "all":
        modules_qs = modules_qs.filter(grade_level=grade_filter)
    if quarter_filter != "all":
        modules_qs = modules_qs.filter(quarter=quarter_filter)
    if status_filter == "active":
        modules_qs = modules_qs.filter(is_active=True)
    elif status_filter == "inactive":
        modules_qs = modules_qs.filter(is_active=False)

    # ---- Assignments + submission detail ----
    assignments_qs = list(
        Assignment.objects.filter(teacher=teacher, subject=active_subject)
        if active_subject
        else Assignment.objects.filter(teacher=teacher)
    )

    for assignment in assignments_qs:
        subs = AssignmentSubmission.objects.filter(
            assignment=assignment
        ).select_related("student", "student__user")

        assignment.submissions_detail = subs
        assignment.submission_count = subs.count()
        assignment.graded_count = subs.filter(status="graded").count()
        assignment.late_count = subs.filter(status="late").count()
        assignment.pending_count = max(
            0,
            assignment.submission_count
            - assignment.graded_count
            - assignment.late_count,
        )

    # ---- Overall stats ----
    total_modules = LearningModule.objects.filter(teacher=teacher).count()
    total_assignments = Assignment.objects.filter(teacher=teacher).count()
    from django.db import models as db_models

    total_downloads = (
        LearningModule.objects.filter(teacher=teacher).aggregate(
            total=db_models.Sum("download_count")
        )["total"]
        or 0
    )

    grade_levels = [c[0] for c in LearningModule.GRADE_LEVEL_CHOICES]
    quarters = [c[0] for c in LearningModule.QUARTER_CHOICES]

    context = {
        "active_page": "subjects",
        "subjects": subjects_with_counts,
        "active_subject": active_subject,
        "modules": modules_qs,
        "assignments": assignments_qs,
        "all_subject_choices": available_subject_choices,
        "grade_levels": grade_levels,
        "quarters": quarters,
        "total_modules": total_modules,
        "total_assignments": total_assignments,
        "total_downloads": total_downloads,
        "current_filter": {
            "grade": grade_filter,
            "quarter": quarter_filter,
            "status": status_filter,
        },
    }

    return render(request, "teacher/manage_subjects.html", context)


@login_required
@never_cache
def student_subjects(request):
    """
    Unified Subjects page.
    Replaces: student_modules, student_assignments, student_my_submissions.

    Context keys
    ------------
    has_grade_level  : bool
    current_grade    : str
    subject_data     : dict  { subject_name: { modules, assignments, submissions, pending_count } }
    accessed_modules : list of module IDs the student has already opened
    submission_map   : dict  { assignment_id: AssignmentSubmission instance }
    submitted_ids    : list of assignment IDs the student has submitted
    total_modules    : int
    total_assignments: int
    total_pending    : int
    total_submissions: int
    """
    try:
        student_profile = request.user.student_profile

        # ── No grade level yet ───────────────────────────────
        if not student_profile.enrolled_in:
            return render(
                request,
                "student/student_subjects.html",
                {
                    "student_profile": student_profile,
                    "has_grade_level": False,
                    "has_subject_enrollment": False,
                    "active_page": "subjects",
                },
            )

        enrolled_subjects = student_profile.enrolled_subjects()
        if not enrolled_subjects:
            return render(
                request,
                "student/student_subjects.html",
                {
                    "student_profile": student_profile,
                    "has_grade_level": True,
                    "has_subject_enrollment": False,
                    "current_grade": student_profile.enrolled_in,
                    "subject_data": {},
                    "active_page": "subjects",
                },
            )

        campus = student_profile.campus
        grade_level = student_profile.enrolled_in

        # ── Fetch active modules for enrolled subjects only ──
        all_modules = (
            LearningModule.objects.filter(
                campus=campus,
                grade_level=grade_level,
                is_active=True,
                subject__in=enrolled_subjects,
            )
            .select_related("teacher__user")
            .order_by("-created_at")
        )

        # Track which modules the student has already accessed
        accessed_modules = list(
            ModuleAccess.objects.filter(student=student_profile).values_list(
                "module_id", flat=True
            )
        )

        # ── Fetch active assignments for enrolled subjects ───
        all_assignments = Assignment.objects.filter(
            campus=campus,
            grade_level=grade_level,
            is_active=True,
            subject__in=enrolled_subjects,
        ).order_by("-created_at")

        # ── Fetch student's submissions ──────────────────────
        all_submissions = (
            AssignmentSubmission.objects.filter(student=student_profile)
            .select_related("assignment")
            .order_by("-submitted_at")
        )

        submitted_ids = list(all_submissions.values_list("assignment_id", flat=True))

        # Build a lookup: assignment_id → AssignmentSubmission instance
        submission_map = {sub.assignment_id: sub for sub in all_submissions}

        # ── Collect every unique enrolled subject that has content ────
        subjects_from_modules = set(all_modules.values_list("subject", flat=True))
        subjects_from_assignments = set(
            all_assignments.values_list("subject", flat=True)
        )
        all_subjects = sorted(subjects_from_modules | subjects_from_assignments)

        # ── Build per-subject data dict ──────────────────────
        subject_data = {}
        for subj in all_subjects:
            subj_modules = [m for m in all_modules if m.subject == subj]
            subj_assignments = [a for a in all_assignments if a.subject == subj]
            subj_submissions = [
                s for s in all_submissions if s.assignment.subject == subj
            ]
            subj_submitted_ids = {s.assignment_id for s in subj_submissions}
            pending_count = sum(
                1 for a in subj_assignments if a.id not in subj_submitted_ids
            )

            subject_data[subj] = {
                "modules": subj_modules,
                "assignments": subj_assignments,
                "submissions": subj_submissions,
                "pending_count": pending_count,
            }

        # ── Global counters for stats cards ─────────────────
        total_modules = all_modules.count()
        total_assignments = all_assignments.count()
        total_pending = sum(d["pending_count"] for d in subject_data.values())
        total_submissions = all_submissions.count()

        context = {
            "student_profile": student_profile,
            "has_grade_level": True,
            "has_subject_enrollment": True,
            "current_grade": grade_level,
            "subject_data": subject_data,
            "accessed_modules": accessed_modules,
            "submission_map": submission_map,
            "submitted_ids": submitted_ids,
            "total_modules": total_modules,
            "total_assignments": total_assignments,
            "total_pending": total_pending,
            "total_submissions": total_submissions,
            "active_page": "subjects",
        }
        return render(request, "student/student_subjects.html", context)

    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect("home")
