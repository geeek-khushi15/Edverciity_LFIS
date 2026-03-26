from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, TrainerProfile, EmployeeAttendanceLog, StudentProfile, StudentDoubt
admin.site.register(StudentProfile)

class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('email', 'role')}),
    )
    list_display = ['username', 'email', 'role', 'is_staff']

admin.site.register(User, CustomUserAdmin)
admin.site.register(TrainerProfile)
admin.site.register(EmployeeAttendanceLog)


@admin.register(StudentDoubt)
class StudentDoubtAdmin(admin.ModelAdmin):
    list_display = ['student', 'trainer', 'title', 'status', 'created_at', 'resolved_at']
    list_filter = ['status', 'created_at', 'resolved_at']
    search_fields = ['student__username', 'student__email', 'title', 'description', 'response']
