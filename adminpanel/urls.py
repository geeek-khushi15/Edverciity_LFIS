from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.adminpanel_login, name='adminpanel_login'),
    path('logout/', views.adminpanel_logout, name='adminpanel_logout'),
    path('', views.adminpanel_dashboard, name='adminpanel_dashboard'),
    path('students/', views.adminpanel_students, name='adminpanel_students'),
    path('students/create/', views.adminpanel_student_create, name='adminpanel_student_create'),
    path('trainers/', views.adminpanel_trainers, name='adminpanel_trainers'),
    path('trainers/create/', views.adminpanel_trainer_create, name='adminpanel_trainer_create'),
    path('courses/', views.adminpanel_courses, name='adminpanel_courses'),
    path('modules/', views.adminpanel_modules, name='adminpanel_modules'),
    path('topics/', views.adminpanel_topics, name='adminpanel_topics'),
    path('topics/import/', views.adminpanel_topics_import, name='adminpanel_topics_import'),
    path('batches/', views.adminpanel_batches, name='adminpanel_batches'),
    path('enrollments/', views.adminpanel_enrollments, name='adminpanel_enrollments'),
    path('attendance/', views.adminpanel_attendance, name='adminpanel_attendance'),
    path('assignments/', views.adminpanel_assignments, name='adminpanel_assignments'),
    path('tests/', views.adminpanel_tests, name='adminpanel_tests'),
    path('doubts/', views.adminpanel_doubts, name='adminpanel_doubts'),
    path('certificates/', views.adminpanel_certificates, name='adminpanel_certificates'),
    path('reports/', views.adminpanel_reports, name='adminpanel_reports'),
]
