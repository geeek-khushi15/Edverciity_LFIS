from django.urls import path
from . import views

urlpatterns = [
    path('materials/upload/', views.MaterialCreateView.as_view(), name='material_create'),
    path('batch/<int:batch_id>/materials/', views.MaterialListView.as_view(), name='material_list'),
]
