from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from .models import User, StudentProfile, StudentDoubt, TrainerProfile
from courses.models import Course
from attendance.models import ClassSession
from enrollments.models import Enrollment


# =========================
# Student Registration
# =========================

class StudentRegistrationForm(UserCreationForm):

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        if commit:
            user.save()
        return user


# =========================
# Trainer Registration
# =========================

class TrainerRegistrationForm(UserCreationForm):

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TRAINER
        if commit:
            user.save()
        return user


# =========================
# Student Profile Form
# =========================

class StudentProfileForm(forms.ModelForm):

    class Meta:
        model = StudentProfile

        fields = [
            'full_name',
            'father_name',
            'mother_name',
            'date_of_birth',
            'contact_number',
            'caste_category',
            'highest_education',
            'address',
            'pincode',
            'course_start_date',
            'course_end_date',
            'profile_photo',
        ]

        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'course_start_date': forms.DateInput(attrs={'type': 'date'}),
            'course_end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class AdminStudentProfileCreateForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = StudentProfile
        fields = [
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'full_name',
            'father_name',
            'mother_name',
            'date_of_birth',
            'contact_number',
            'caste_category',
            'highest_education',
            'address',
            'pincode',
            'course_start_date',
            'course_end_date',
            'profile_photo',
        ]
        widgets = {
            'password': forms.PasswordInput(),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'course_start_date': forms.DateInput(attrs={'type': 'date'}),
            'course_end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = 'w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-500'
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{existing} {base_class}".strip()

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            raise ValueError('AdminStudentProfileCreateForm requires commit=True')

        user = User.objects.create(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            role=User.Role.STUDENT,
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
        )
        user.set_password(self.cleaned_data['password'])
        user.save(update_fields=['password'])

        profile = super().save(commit=False)
        profile.user = user
        profile.save()
        return profile


class AdminTrainerProfileCreateForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = TrainerProfile
        fields = [
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'profile_photo',
            'full_name',
            'father_name',
            'date_of_birth',
            'gender',
            'contact_number',
            'address',
            'pincode',
            'trainer_id',
            'department',
            'highest_education',
            'years_of_experience',
            'specialization',
        ]
        widgets = {
            'password': forms.PasswordInput(),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'gender': forms.Select(choices=[
                ('', 'Select gender'),
                ('Male', 'Male'),
                ('Female', 'Female'),
                ('Other', 'Other'),
            ]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = 'w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-500'
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{existing} {base_class}".strip()

        self.fields['trainer_id'].required = True

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_trainer_id(self):
        trainer_id = (self.cleaned_data.get('trainer_id') or '').strip()
        if not trainer_id:
            raise forms.ValidationError('Trainer ID is required.')
        if TrainerProfile.objects.filter(trainer_id__iexact=trainer_id).exists():
            raise forms.ValidationError('This trainer ID already exists.')
        return trainer_id

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            raise ValueError('AdminTrainerProfileCreateForm requires commit=True')

        user = User.objects.create(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            role=User.Role.TRAINER,
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
        )
        user.set_password(self.cleaned_data['password'])
        user.save(update_fields=['password'])

        profile = super().save(commit=False)
        profile.user = user
        profile.save()
        return profile


class TrainerProfileForm(forms.ModelForm):

    class Meta:
        model = TrainerProfile
        fields = [
            'profile_photo',
            'full_name',
            'father_name',
            'date_of_birth',
            'gender',
            'contact_number',
            'address',
            'pincode',
            'trainer_id',
            'department',
            'highest_education',
            'years_of_experience',
            'specialization',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.Select(choices=[
                ('', 'Select gender'),
                ('Male', 'Male'),
                ('Female', 'Female'),
                ('Other', 'Other'),
            ]),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            base_class = 'w-full rounded-xl border border-slate-300 px-3 py-2 text-sm'

            if isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs.update({'class': 'w-full rounded-xl border border-slate-300 p-2 text-sm'})
                continue

            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': base_class, 'rows': 3})
                continue

            field.widget.attrs.update({'class': base_class})


class StudentDoubtForm(forms.ModelForm):

    QUERY_TYPE_CHOICES = (
        ('subject_topic', 'Subject / Topic Related Query'),
        ('soft_skill', 'Soft Skill Related Query'),
        ('placement', 'Placement Related Query'),
    )

    query_type = forms.ChoiceField(
        choices=QUERY_TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border-gray-300'})
    )

    class Meta:
        model = StudentDoubt
        fields = ['title', 'description', 'related_course', 'related_session']
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'w-full rounded-lg border-gray-300',
                    'placeholder': 'Write a short title for your doubt'
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'w-full rounded-lg border-gray-300',
                    'rows': 5,
                    'placeholder': 'Describe your doubt in detail so trainers can help faster'
                }
            ),
            'related_course': forms.Select(attrs={'class': 'w-full rounded-lg border-gray-300'}),
            'related_session': forms.Select(attrs={'class': 'w-full rounded-lg border-gray-300'}),
        }

    def __init__(self, *args, **kwargs):
        student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)

        self.fields['related_course'].required = False
        self.fields['related_session'].required = False

        self.fields['related_course'].empty_label = 'Optional: Select related course'
        self.fields['related_session'].empty_label = 'Optional: Select related session'

        self.fields['related_course'].queryset = Course.objects.none()
        self.fields['related_session'].queryset = ClassSession.objects.none()

        if student is not None:
            enrollments = Enrollment.objects.filter(
                student=student
            ).select_related('batch', 'batch__course')

            course_ids = enrollments.values_list('batch__course_id', flat=True)
            batch_ids = enrollments.values_list('batch_id', flat=True)

            self.fields['related_course'].queryset = Course.objects.filter(id__in=course_ids).distinct()
            self.fields['related_session'].queryset = ClassSession.objects.filter(
                batch_id__in=batch_ids
            ).select_related('batch').order_by('-date')

            self.fields['related_session'].label_from_instance = (
                lambda obj: f"{obj.batch.name} ({obj.date})"
            )