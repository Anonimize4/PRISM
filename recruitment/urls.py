from django.urls import path
from . import views

urlpatterns = [
    # Student URLs
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/create-application/', views.create_application, name='create_application'),
    path('student/application-status/', views.application_status, name='application_status'),
    path('student/submit-weekly-report/', views.submit_weekly_report, name='submit_weekly_report'),
    path('student/report-history/', views.report_history, name='report_history'),
    path('student/submit-leave-request/', views.submit_leave_request, name='submit_leave_request'),
    path('student/leave-requests/', views.leave_requests, name='leave_requests'),
    path('student/messaging/', views.messaging, name='messaging'),
    
    # Company URLs
    path('company/dashboard/', views.company_dashboard, name='company_dashboard'),
    path('company/manage-applications/', views.manage_applications, name='manage_applications'),
    path('company/update-application-status/<int:application_id>/', views.update_application_status, name='update_application_status'),
    path('company/review-reports/', views.review_reports, name='review_reports'),
    path('company/submit-feedback/<int:report_id>/', views.submit_feedback, name='submit_feedback'),
    path('company/create-team/', views.create_team, name='create_team'),
    path('company/team-management/', views.team_management, name='team_management'),
    path('company/create-project/', views.create_project, name='create_project'),
    path('company/project-management/', views.project_management, name='project_management'),
    path('company/update-leave-status/<int:leave_id>/', views.update_leave_status, name='update_leave_status'),
    
    # Common URLs
    path('messaging/', views.messaging, name='messaging'),
]
