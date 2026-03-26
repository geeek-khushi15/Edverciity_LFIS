from django.contrib import admin
from .models import Batch

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'trainer', 'start_date', 'end_date')
    list_filter = ('course', 'trainer', 'start_date', 'end_date')
    search_fields = ('name', 'course__title', 'trainer__username')
