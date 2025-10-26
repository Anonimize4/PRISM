from django.urls import path
from . import views

app_name = 'admin_app'

urlpatterns = [
    # Admin Dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # User Management
    path('user-management/', views.user_management, name='user_management'),
    path('create-user/', views.create_user, name='create_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    
    # System Monitoring
    path('system-health/', views.system_health_monitoring, name='system_health_monitoring'),
    path('user-activity-logs/', views.user_activity_logs, name='user_activity_logs'),
    path('system-logs/', views.system_logs, name='system_logs'),
    
    # System Notifications
    path('system-notifications/', views.system_notifications, name='system_notifications'),
    path('toggle-notification/<int:notification_id>/', views.toggle_notification, name='toggle_notification'),
    
    # Backup and Security
    path('backup-management/', views.backup_management, name='backup_management'),
    path('security-audit/', views.security_audit, name='security_audit'),
    
    # System Configuration
    path('system-configuration/', views.system_configuration, name='system_configuration'),
    
    # Analytics
    path('analytics-dashboard/', views.analytics_dashboard, name='analytics_dashboard'),
    
    # API Endpoints
    path('api/system-health/', views.api_system_health, name='api_system_health'),
    path('api/user-stats/', views.api_user_stats, name='api_user_stats'),
]
