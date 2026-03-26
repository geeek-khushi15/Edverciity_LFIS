from django.views.generic import CreateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from .models import Material
from batches.models import Batch
from .forms import MaterialForm

class TrainerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'TRAINER'

class MaterialCreateView(LoginRequiredMixin, TrainerRequiredMixin, CreateView):
    model = Material
    form_class = MaterialForm
    template_name = 'materials/material_form.html'
    success_url = reverse_lazy('dashboard') # Simple redirect back to dashboard for now

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['trainer'] = self.request.user
        return kwargs

class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    template_name = 'materials/material_list.html'
    context_object_name = 'materials'

    def get_queryset(self):
        batch_id = self.kwargs.get('batch_id')
        batch = get_object_or_404(Batch, id=batch_id)
        
        # Access control
        user = self.request.user
        if getattr(user, 'role', '') == 'STUDENT':
            # Verify the student has access to this batch (full or module enrollment)
            from enrollments.models import Enrollment
            if not Enrollment.has_module_access(user, batch):
                return Material.objects.none()  # Or raise 403
        elif getattr(user, 'role', '') == 'TRAINER':
            # Verify the trainer owns this batch
            if batch.trainer != user:
                return Material.objects.none()
        else:
            # Admin or someone else
            return Material.objects.none()
                
        return Material.objects.filter(batch=batch)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['batch'] = get_object_or_404(Batch, id=self.kwargs.get('batch_id'))
        return context
