from django.contrib import admin
from .models import Assignment, AssignmentSubmission, Test, Question, TestAttempt

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
	list_display = ('title', 'course', 'module', 'batch', 'trainer', 'due_date', 'max_marks')
	list_filter = ('course', 'module', 'batch', 'trainer')
	search_fields = ('title', 'description')


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
	list_display = ('assignment', 'student', 'status', 'marks_obtained', 'submitted_at')
	list_filter = ('status', 'assignment__batch')
	search_fields = ('assignment__title', 'student__username')


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
	list_display = ('title', 'course', 'module', 'batch', 'trainer', 'created_at')
	list_filter = ('course', 'module', 'batch', 'trainer')
	search_fields = ('title',)

admin.site.register(Question)
admin.site.register(TestAttempt)
