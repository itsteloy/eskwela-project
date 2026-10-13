from django.urls import path
from . import views

urlpatterns = [
    # ========== PUBLIC PAGES (No Login Required) ==========
    path("", views.index, name="home"),
    path("admin_login/", views.admin_login, name="admin_login"),
    path("student_login/", views.student_login, name="student_login"),
    path("teacher_login/", views.teacher_login, name="teacher_login"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
    # ========== ADMIN DASHBOARD & MANAGEMENT ==========
    # Dashboard
    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path(
        "admission_management/", views.admission_management, name="admission_management"
    ),
    # Admin Profile Management
    path("administrator/profile/", views.admin_profile, name="admin_profile"),
    path("administrator/create/", views.create_admin, name="create_admin"),
    # Teacher Management (Admin Only)
    path("teacher_management/", views.teacher_management, name="teacher_management"),
    path("create_teacher/", views.create_teacher, name="create_teacher"),
    path(
        "reset_teacher_password/<int:teacher_id>/",
        views.reset_teacher_password,
        name="reset_teacher_password",
    ),
    path(
        "delete_teacher/<int:teacher_id>/", views.delete_teacher, name="delete_teacher"
    ),
    path("edit_teacher/<int:teacher_id>/", views.edit_teacher, name="edit_teacher"),
    # Student Management (Admin Only)
    path(
        "approve_student/<int:student_id>/",
        views.approve_student,
        name="approve_student",
    ),
    path(
        "reject_student/<int:student_id>/", views.reject_student, name="reject_student"
    ),
    path(
        "delete_student/<int:student_id>/", views.delete_student, name="delete_student"
    ),
    path("manage_students/<int:student_id>/", views.edit_student, name="edit_student"),
    # ========== STUDENT PAGES ==========
    path("student_dashboard/", views.student_dashboard, name="student_dashboard"),
    path("student_schedule/", views.student_schedule, name="student_schedule"),
    path("student_modules/", views.student_modules, name="student_modules"),
    path(
        "student_requirements/", views.student_requirements, name="student_requirements"
    ),
    path("student_profile/", views.student_profile, name="student_profile"),
    path("student_assignments/", views.student_assignments, name="student_assignments"),
    path(
        "student_announcements/",
        views.student_announcements,
        name="student_announcements",
    ),
    path(
        "student_my_submissions/",
        views.student_my_submissions,
        name="student_my_submissions",
    ),
    path(
        "student/submit_assignment/<int:assignment_id>/",
        views.submit_assignment,
        name="submit_assignment",
    ),
    # Student Module Access
    path(
        "student/modules/view/<int:module_id>/", views.view_module, name="view_module"
    ),
    path(
        "student/modules/download/<int:module_id>/",
        views.student_download_module,
        name="student_download_module",
    ),
    path(
        "student/modules/serve/<int:module_id>/",
        views.serve_module_pdf,
        name="serve_module_pdf",
    ),
    # ========== TEACHER PAGES ==========
    # Teacher Dashboard
    path("teacher_dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/profile/", views.teacher_profile, name="teacher_profile"),
    # Teacher Schedule Management
    path("teacher/schedules/", views.teacher_schedules, name="teacher_schedules"),
    path("teacher/schedules/create/", views.create_schedule, name="create_schedule"),
    path(
        "teacher/schedules/edit/<int:schedule_id>/",
        views.edit_schedule,
        name="edit_schedule",
    ),
    path(
        "teacher/schedules/delete/<int:schedule_id>/",
        views.delete_schedule,
        name="delete_schedule",
    ),
    path(
        "teacher/schedules/toggle/<int:schedule_id>/",
        views.toggle_schedule,
        name="toggle_schedule",
    ),
    # Teacher Manage Subjects (replaces teacher_modules + teacher_assignments pages)
    path("teacher/subjects/", views.manage_subjects, name="manage_subjects"),
    # Teacher Module Management
    path("teacher/modules/", views.teacher_modules, name="teacher_modules"),
    path("teacher/modules/upload/", views.upload_module, name="upload_module"),
    path(
        "teacher/modules/edit/<int:module_id>/", views.edit_module, name="edit_module"
    ),
    path(
        "teacher/modules/delete/<int:module_id>/",
        views.delete_module,
        name="delete_module",
    ),
    path(
        "teacher/modules/toggle/<int:module_id>/",
        views.toggle_module,
        name="toggle_module",
    ),
    path(
        "teacher/modules/download/<int:module_id>/",
        views.download_module,
        name="download_module",
    ),
    path(
        "teacher/modules/view/<int:module_id>/",
        views.teacher_view_module,
        name="teacher_view_module",
    ),
    # Teacher Announcements
    path(
        "teacher/announcements/",
        views.teacher_announcements,
        name="teacher_announcements",
    ),
    path(
        "teacher/announcements/create/",
        views.create_announcement,
        name="create_announcement",
    ),
    path(
        "teacher/announcements/edit/<int:announcement_id>/",
        views.edit_announcement,
        name="edit_announcement",
    ),
    path(
        "teacher/announcements/delete/<int:announcement_id>/",
        views.delete_announcement,
        name="delete_announcement",
    ),
    path(
        "teacher/announcements/toggle/<int:announcement_id>/",
        views.toggle_announcement,
        name="toggle_announcement",
    ),
    # Teacher Assignments
    path("teacher/assignments/", views.teacher_assignments, name="teacher_assignments"),
    path(
        "teacher/assignments/create/", views.create_assignment, name="create_assignment"
    ),
    path(
        "teacher/assignments/edit/<int:assignment_id>/",
        views.edit_assignment,
        name="edit_assignment",
    ),
    path(
        "teacher/assignments/delete/<int:assignment_id>/",
        views.delete_assignment,
        name="delete_assignment",
    ),
    path(
        "teacher/assignments/toggle/<int:assignment_id>/",
        views.toggle_assignment,
        name="toggle_assignment",
    ),
    path(
        "teacher/assignments/submissions/<int:assignment_id>/",
        views.view_submissions,
        name="view_submissions",
    ),
    path(
        "teacher/assignments/grade/<int:submission_id>/",
        views.grade_submission,
        name="grade_submission",
    ),
    # Campus Management (Admin Only)
    path("campus_management/", views.campus_management, name="campus_management"),
    path("create_campus/", views.create_campus, name="create_campus"),
    path("edit_campus/<int:campus_id>/", views.edit_campus, name="edit_campus"),
    path("delete_campus/<int:campus_id>/", views.delete_campus, name="delete_campus"),
    path("toggle_campus/<int:campus_id>/", views.toggle_campus, name="toggle_campus"),
    # API endpoint for registration page
    path(
        "api/get_active_campuses/",
        views.get_active_campuses,
        name="get_active_campuses",
    ),
    path(
        "api/get_student_details/<int:student_id>/",
        views.get_student_details,
        name="get_student_details",
    ),
    path(
        "api/get_student_documents/<int:student_id>/",
        views.get_student_documents,
        name="get_student_documents",
    ),
    path("manage_students/", views.manage_students, name="manage_students"),
    path(
        "manage_students/update-requirement/<int:student_id>/",
        views.update_requirement_status,
        name="update_requirement_status",
    ),
    path(
        "subject_enrollment/",
        views.subject_enrollment,
        name="subject_enrollment",
    ),
    path(
        "subject_enrollment/<int:student_id>/",
        views.enroll_student_subjects,
        name="enroll_student_subjects",
    ),
    path("student_subjects/", views.student_subjects, name="student_subjects"),
]
