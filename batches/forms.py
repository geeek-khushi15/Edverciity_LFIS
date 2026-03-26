from django import forms
from courses.models import CourseModule
from .models import Batch

class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['name', 'course', 'module', 'trainer', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['module'].required = False
        self.fields['module'].queryset = CourseModule.objects.select_related('course').order_by('course__title', 'order_number', 'name')

        selected_course_id = None
        if self.is_bound:
            selected_course_id = self.data.get('course')
        elif self.instance and self.instance.pk:
            selected_course_id = self.instance.course_id

        if selected_course_id:
            self.fields['module'].queryset = self.fields['module'].queryset.filter(course_id=selected_course_id)
