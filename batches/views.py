from django.views.generic import CreateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from .models import Batch
from .forms import BatchForm

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'ADMIN'

class BatchCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Batch
    form_class = BatchForm
    template_name = 'batches/batch_form.html'
    success_url = reverse_lazy('batch_list')

class BatchListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Batch
    template_name = 'batches/batch_list.html'
    context_object_name = 'batches'
