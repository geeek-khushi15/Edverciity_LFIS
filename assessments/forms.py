from django import forms
from django.utils import timezone
from .models import Test, Question, Assignment, AssignmentSubmission
from batches.models import Batch
from courses.models import Course, CourseModule

class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = [
            'title',
            'course',
            'module',
            'batch',
            'total_marks',
            'duration',
            'start_time',
            'end_time',
            'passing_marks',
        ]
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        trainer = kwargs.pop('trainer', None)
        super().__init__(*args, **kwargs)
        if trainer:
            batches = Batch.objects.filter(trainer=trainer)
            self.fields['batch'].queryset = batches
            self.fields['course'].queryset = Course.objects.filter(
                id__in=batches.values_list('course_id', flat=True)
            ).distinct()
            self.fields['module'].queryset = CourseModule.objects.filter(
                course_id__in=self.fields['course'].queryset.values_list('id', flat=True)
            ).order_by('course__title', 'order_number')

        selected_course_id = self.data.get('course') if self.is_bound else getattr(self.instance, 'course_id', None)
        if selected_course_id:
            self.fields['module'].queryset = self.fields['module'].queryset.filter(course_id=selected_course_id)

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError('End time must be later than start time.')

        course = cleaned_data.get('course')
        module = cleaned_data.get('module')
        batch = cleaned_data.get('batch')

        if batch and course and batch.course_id != course.id:
            raise forms.ValidationError('Selected batch must belong to selected course.')

        if module and course and module.course_id != course.id:
            raise forms.ValidationError('Selected module must belong to selected course.')

        return cleaned_data

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3}),
        }


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'course', 'module', 'batch', 'due_date', 'max_marks']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        trainer = kwargs.pop('trainer', None)
        super().__init__(*args, **kwargs)
        if trainer:
            batches = Batch.objects.filter(trainer=trainer)
            self.fields['batch'].queryset = batches
            self.fields['course'].queryset = Course.objects.filter(
                id__in=batches.values_list('course_id', flat=True)
            ).distinct()
            self.fields['module'].queryset = CourseModule.objects.filter(
                course_id__in=self.fields['course'].queryset.values_list('id', flat=True)
            ).order_by('course__title', 'order_number')

        selected_course_id = self.data.get('course') if self.is_bound else getattr(self.instance, 'course_id', None)
        if selected_course_id:
            self.fields['module'].queryset = self.fields['module'].queryset.filter(course_id=selected_course_id)

    def clean_due_date(self):
        due_date = self.cleaned_data['due_date']
        if due_date <= timezone.now():
            raise forms.ValidationError('Due date must be in the future.')
        return due_date

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        module = cleaned_data.get('module')
        batch = cleaned_data.get('batch')

        if batch and course and batch.course_id != course.id:
            raise forms.ValidationError('Selected batch must belong to selected course.')

        if module and course and module.course_id != course.id:
            raise forms.ValidationError('Selected module must belong to selected course.')

        return cleaned_data


class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['file_upload']


class AssignmentEvaluationForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['marks_obtained', 'feedback', 'status']
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 4}),
        }
