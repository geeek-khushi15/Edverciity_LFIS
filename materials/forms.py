from django import forms
from .models import Material

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['title', 'batch', 'material_type', 'file', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        trainer = kwargs.pop('trainer', None)
        super().__init__(*args, **kwargs)
        if trainer:
            # Trainers can only upload materials to batches they are assigned to
            from batches.models import Batch
            self.fields['batch'].queryset = Batch.objects.filter(trainer=trainer)

    def clean(self):
        cleaned_data = super().clean()
        material_type = cleaned_data.get('material_type')
        file = cleaned_data.get('file')
        content = cleaned_data.get('content')

        if material_type in ['PDF', 'VIDEO'] and not file:
            self.add_error('file', 'A file must be uploaded for this material type.')
        if material_type in ['NOTE', 'LINK'] and not content:
            self.add_error('content', 'Content must be provided for notes or links.')

        return cleaned_data
