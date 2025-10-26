from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.university_dashboard, name='university_dashboard'),
    path('accepted-students/', views.accepted_students, name='accepted_students'),
    path('assign-supervisor/', views.assign_supervisor, name='assign_supervisor'),
    path('bulk-assign-supervisor/', views.bulk_supervisor_assignment, name='bulk_supervisor_assignment'),
    path('supervisor-assignments/', views.supervisor_assignments, name='supervisor_assignments'),
    path('supervisor-workload/', views.supervisor_workload, name='supervisor_workload'),
    path('student-performance/<int:student_id>/', views.student_performance, name='student_performance'),
    path('student-reports/<int:student_id>/', views.student_reports, name='student_reports'),
    path('performance-overview/', views.performance_overview, name='performance_overview'),
    path('performance-alerts/', views.performance_alerts, name='performance_alerts'),
    path('company-evaluations/', views.company_evaluations, name='company_evaluations'),
    path('final-evaluations/', views.final_evaluations, name='final_evaluations'),
    path('create-final-evaluation/<int:student_id>/', views.create_final_evaluation, name='create_final_evaluation'),
    path('attendance-management/', views.attendance_management, name='attendance_management'),
    path('analytics-dashboard/', views.analytics_dashboard, name='analytics_dashboard'),
    path('export-student-data/', views.export_student_data, name='export_student_data'),
]
