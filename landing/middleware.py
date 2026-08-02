from django.shortcuts import redirect
from django.urls import resolve
from django.urls.exceptions import Resolver404
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin


class SessionTimeoutMiddleware(MiddlewareMixin):
    """Middleware to check if user session is still valid"""

    def process_request(self, request):
        # Names of URL patterns that don't require authentication
        exempt_names = {
            "home",
            "admin_login",
            "student_login",
            "teacher_login",
            "register",
            "logout",
        }

        # Resolve the current request to a url name where possible
        try:
            resolver_match = resolve(request.path_info)
            url_name = resolver_match.url_name
        except Resolver404:
            url_name = None

        # If the requested view is exempt, do nothing
        if url_name in exempt_names:
            return None

        # Check if user is authenticated
        if not request.user.is_authenticated:
            # For AJAX requests, return 401
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                from django.http import JsonResponse

                return JsonResponse({"error": "Session expired"}, status=401)

            # For regular requests, redirect to appropriate login page.
            # Use path content as a fallback if url_name is not helpful.
            if "admin" in request.path or url_name == "admin_dashboard":
                storage = messages.get_messages(request)
                for _ in storage:
                    pass
                storage.used = True
                return redirect("admin_login")
            elif "teacher" in request.path or (
                url_name and url_name.startswith("teacher")
            ):
                storage = messages.get_messages(request)
                for _ in storage:
                    pass
                storage.used = True
                return redirect("teacher_login")
            elif "student" in request.path or (
                url_name and url_name.startswith("student")
            ):
                storage = messages.get_messages(request)
                for _ in storage:
                    pass
                storage.used = True
                return redirect("student_login")
            else:
                return redirect("home")

        return None


class TeacherSessionMiddleware(MiddlewareMixin):
    """Middleware to check teacher session validity"""

    def process_request(self, request):
        # Teacher protected URLs
        teacher_names = {
            "teacher_dashboard",
            "teacher_schedules",
            "teacher_modules",
            "teacher_announcements",
            "teacher_assignments",
            "teacher_profile",
        }

        # Try to resolve the path to a url name
        try:
            resolver_match = resolve(request.path_info)
            url_name = resolver_match.url_name
        except Resolver404:
            url_name = None

        # Check if the requested path is a teacher page
        if (url_name in teacher_names) or request.path.startswith("/teacher/"):
            if (
                not request.user.is_authenticated
                or not request.user.is_staff
                or request.user.is_superuser
            ):
                # For AJAX requests
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    from django.http import JsonResponse

                    return JsonResponse({"error": "Session expired"}, status=401)

                # For regular requests, redirect to teacher login WITHOUT adding message
                # Clear any messages before redirect
                storage = messages.get_messages(request)
                storage.used = True
                return redirect("teacher_login")

        return None
