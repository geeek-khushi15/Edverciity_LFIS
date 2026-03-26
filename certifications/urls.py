from django.urls import path
from . import views

urlpatterns = [
    path('certifications/', views.StudentCertificationListView.as_view(), name='student_certification_list'),
    path('certifications/apply/<int:batch_id>/', views.ApplyCertificationView.as_view(), name='apply_certification'),
    
    # Admin Views
    path('manage/applications/', views.AdminApplicationListView.as_view(), name='admin_application_list'),
    path('manage/applications/<int:app_id>/approve/', views.AdminApproveApplicationView.as_view(), name='approve_application'),
    path('manage/applications/<int:app_id>/reject/', views.AdminRejectApplicationView.as_view(), name='reject_application'),
]
