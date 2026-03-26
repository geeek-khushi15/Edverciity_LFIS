from django import forms
from .models import ClassSession
from batches.models import Batch

class ClassSessionForm(forms.ModelForm):
    class Meta:
        model = ClassSession
        fields = ['batch', 'date', 'topics_covered']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500'}),
            'topics_covered': forms.Textarea(attrs={'rows': 4, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500', 'placeholder': 'E.g., CSS Flexbox, Grid Layouts, Responsive Design paradigms.'}),
            'batch': forms.Select(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500'}),
        }

    def __init__(self, *args, **kwargs):
        trainer = kwargs.pop('trainer', None)
        super().__init__(*args, **kwargs)
        if trainer:
            self.fields['batch'].queryset = Batch.objects.filter(trainer=trainer)
