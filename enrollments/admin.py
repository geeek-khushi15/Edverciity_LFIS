from django.contrib import admin
from .forms import EnrollmentForm
from .models import Enrollment

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    form = EnrollmentForm
    list_display = ('student', 'course', 'enrollment_type', 'module', 'batch', 'enrolled_at')
    list_filter = ('course', 'enrollment_type', 'batch', 'enrollment_date')
    search_fields = (
        'student__username',
        'student__email',
        'student__first_name',
        'student__last_name',
        'course__title',
        'module__name',
        'batch__name',
    )
