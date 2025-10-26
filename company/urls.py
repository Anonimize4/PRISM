from django.urls import path
from . import views

urlpatterns = [
    # Company Dashboard and Profile
    path('dashboard/', views.company_dashboard, name='company_dashboard'),
    path('create-company-profile/', views.create_company_profile, name='create_company_profile'),
    path('view-company-profile/', views.view_company_profile, name='view_company_profile'),
    path('edit-company-profile/', views.edit_company_profile, name='edit_company_profile'),
    
    # Mentor Management
    path('manage-mentors/', views.manage_mentors, name='manage_mentors'),
    
    # Meeting Management
    path('schedule-meeting/', views.schedule_meeting, name='schedule_meeting'),
    path('meetings/', views.meetings, name='meetings'),
    path('meeting-detail/<int:meeting_id>/', views.meeting_detail, name='meeting_detail'),
    
    # Student Evaluations
    path('student-evaluations/', views.student_evaluations, name='student_evaluations'),
    path('create-evaluation/<int:application_id>/', views.create_evaluation, name='create_evaluation'),
    
    # Settings
    path('notification-settings/', views.notification_settings, name='notification_settings'),
    
    # Reports and Analytics
    path('reports-analytics/', views.reports_analytics, name='reports_analytics'),
]
