from django.urls import path
from . import views

urlpatterns = [
    path('enrollments/', views.StudentEnrollmentListView.as_view(), name='enrollment_list'),
    path('enrollments/create/', views.EnrollmentCreateView.as_view(), name='enrollment_create'),
]
