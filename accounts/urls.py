from django.urls import path
from . import views

urlpatterns = [
    path('', views.LandingPageView.as_view(), name='landing_page'),
    path('register/student/', views.student_register, name='student_register'),
    path('register/trainer/', views.trainer_register, name='trainer_register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('doubts/raise/', views.student_raise_doubt, name='student_raise_doubt'),
    path('profile/', views.StudentProfileView.as_view(), name='student_profile'),
    path('progress/', views.StudentProgressView.as_view(), name='student_progress'),
    path('trainer/profile/', views.TrainerProfileView.as_view(), name='trainer_profile'),
    path('trainer/batch-report/', views.trainer_batch_report, name='trainer_batch_report'),
    path('trainer/doubts/', views.trainer_doubts, name='trainer_doubts'),
    path('admin/doubts/', views.admin_doubts, name='admin_doubts'),
    path('trainer/setup-face/', views.trainer_setup_face, name='trainer_setup_face'),
    path('employee/verify/', views.employee_verification, name='employee_verification'),
    path('api/employee-verify/', views.api_employee_verification, name='api_employee_verification'),
    path('api/employee-checkout/', views.api_employee_checkout, name='api_employee_checkout'),
]
