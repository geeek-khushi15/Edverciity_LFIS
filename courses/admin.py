from django.contrib import admin
from .models import Course, CourseModule, CourseTopic, TopicAcknowledgement, TopicProgress


class CourseModuleInline(admin.TabularInline):
    model = CourseModule
    extra = 1
    fields = ('name', 'description', 'order_number')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('created_at',)
    inlines = [CourseModuleInline]


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'order_number')
    search_fields = ('name', 'description', 'course__title')
    list_filter = ('course',)
    ordering = ('course__title', 'order_number')


@admin.register(CourseTopic)
class CourseTopicAdmin(admin.ModelAdmin):
    list_display = ('course', 'topic_number', 'title', 'created_by', 'created_at')
    search_fields = ('title', 'description', 'course__title', 'created_by__username')
    list_filter = ('course', 'created_at')
    ordering = ('course__title', 'topic_number')


@admin.register(TopicAcknowledgement)
class TopicAcknowledgementAdmin(admin.ModelAdmin):
    list_display = ('topic', 'student', 'acknowledged', 'acknowledged_at')
    search_fields = ('topic__title', 'topic__course__title', 'student__username', 'student__email')
    list_filter = ('acknowledged', 'topic__course')


@admin.register(TopicProgress)
class TopicProgressAdmin(admin.ModelAdmin):
    list_display = (
        'topic',
        'student',
        'trainer',
        'trainer_marked_taught',
        'trainer_marked_at',
        'student_marked_understood',
        'student_marked_at',
    )
    search_fields = (
        'topic__title',
        'topic__course__title',
        'student__username',
        'trainer__username',
    )
    list_filter = (
        'topic__course',
        'trainer_marked_taught',
        'student_marked_understood',
    )
