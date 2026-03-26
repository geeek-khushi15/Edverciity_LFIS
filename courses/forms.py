from django import forms
from .models import Course, CourseTopic


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'duration']


class TopicsImportForm(forms.Form):
    """Form for importing topics from CSV or text input"""
    course = forms.ModelChoiceField(
        queryset=Course.objects.all().order_by('title'),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_course_import',
        }),
        label='Select Course'
    )
    
    import_method = forms.ChoiceField(
        choices=[
            ('text', 'Paste Topic List (one per line)'),
            ('csv', 'Upload CSV File')
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'ml-2',
        }),
        label='Import Method',
        initial='text'
    )
    
    topic_list = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Introduction to C++\nBasic Input Output\nVariables and Data Types\n...',
            'rows': 10,
            'id': 'id_topic_list',
        }),
        label='Topic Names (one per line)',
        required=False,
        help_text='Delete existing content and paste your topics'
    )
    
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.txt',
            'id': 'id_csv_file',
        }),
        label='CSV/Text File',
        required=False,
        help_text='Format: one topic name per line'
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Optional: Default description for all topics',
            'rows': 3,
            'id': 'id_description',
        }),
        label='Default Description (Optional)',
        required=False,
        help_text='If not provided, will use "Content for [Topic Name]"'
    )
    
    start_topic_number = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave empty to auto-increment from last topic',
            'id': 'id_start_topic_number',
        }),
        label='Starting Topic Number (Optional)',
        required=False,
        help_text='Default: auto-increment from last topic'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        import_method = cleaned_data.get('import_method')
        topic_list = cleaned_data.get('topic_list', '').strip()
        csv_file = cleaned_data.get('csv_file')
        
        if import_method == 'text' and not topic_list:
            raise forms.ValidationError('Please paste topic names for text import method.')
        
        if import_method == 'csv' and not csv_file:
            raise forms.ValidationError('Please upload a CSV file for CSV import method.')
        
        return cleaned_data
