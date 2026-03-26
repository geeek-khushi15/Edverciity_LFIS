from django import forms
from .models import CertificationApplication

class CertificationApplicationForm(forms.ModelForm):
    passport_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = CertificationApplication
        fields = [
            'full_name', 'fathers_name', 'mothers_name', 'date_of_birth',
            'email_id', 'contact_number', 'course_start_date', 'course_end_date',
            'caste_category', 'highest_education', 'address_with_pincode',
            'passport_photo'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'course_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'course_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'fathers_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mothers_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email_id': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'caste_category': forms.Select(attrs={'class': 'form-select'}),
            'highest_education': forms.Select(attrs={'class': 'form-select'}),
            'address_with_pincode': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
