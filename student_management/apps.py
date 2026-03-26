from django.apps import AppConfig


class StudentManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'student_management'

    def ready(self):
        # Restrict Django admin (/secure-admin/) to SUPERADMIN role only.
        from django.contrib.admin import AdminSite

        def _superadmin_only(self, request):
            return (
                request.user.is_active
                and getattr(request.user, 'role', '') == 'SUPERADMIN'
            )

        AdminSite.has_permission = _superadmin_only
