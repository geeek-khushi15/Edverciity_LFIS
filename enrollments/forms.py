from django import forms
from .models import Enrollment
from batches.models import Batch
from accounts.models import User
from courses.models import CourseModule, Course

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'enrollment_type', 'module', 'batch']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.filter(role=User.Role.STUDENT).order_by('username')
        self.fields['course'].queryset = Course.objects.order_by('title')
        self.fields['batch'].queryset = Batch.objects.select_related('course').order_by('name')
        self.fields['module'].queryset = CourseModule.objects.select_related('course').order_by('course__title', 'order_number', 'name')
        self.fields['module'].required = False

        selected_course_id = None
        if self.is_bound:
            selected_course_id = self.data.get('course')
        elif self.instance and self.instance.pk:
            selected_course_id = self.instance.course_id

        if selected_course_id:
            self.fields['batch'].queryset = self.fields['batch'].queryset.filter(course_id=selected_course_id)
            self.fields['module'].queryset = self.fields['module'].queryset.filter(course_id=selected_course_id)

    def clean(self):
        cleaned_data = super().clean()
        enrollment_type = cleaned_data.get('enrollment_type')
        module = cleaned_data.get('module')
        course = cleaned_data.get('course')
        batch = cleaned_data.get('batch')

        if enrollment_type == Enrollment.EnrollmentType.MODULE and not module:
            self.add_error('module', 'Module is required for module enrollment type.')

        if enrollment_type == Enrollment.EnrollmentType.FULL:
            cleaned_data['module'] = None

        if module and course and module.course_id != course.id:
            self.add_error('module', 'Selected module must belong to the selected course.')

        if batch and course and batch.course_id != course.id:
            self.add_error('batch', 'Selected batch must belong to the selected course.')

        if batch and batch.module_id:
            if enrollment_type == Enrollment.EnrollmentType.MODULE:
                if not module:
                    self.add_error('module', 'Select a module for module enrollment.')
                elif batch.module_id != module.id:
                    self.add_error('batch', 'Selected batch does not match the selected module.')
            elif enrollment_type == Enrollment.EnrollmentType.FULL and module:
                self.add_error('module', 'Module must be empty for full-course enrollment.')

        return cleaned_data
