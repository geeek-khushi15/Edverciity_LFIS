from django.urls import path
from . import views

urlpatterns = [
    path('batches/', views.BatchListView.as_view(), name='batch_list'),
    path('batches/create/', views.BatchCreateView.as_view(), name='batch_create'),
]
