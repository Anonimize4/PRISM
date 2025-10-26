from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification management URLs
    path('', views.NotificationListView.as_view(), name='list'),
    path('detail/<int:pk>/', views.NotificationDetailView.as_view(), name='detail'),
    path('delete/<int:pk>/', views.NotificationDeleteView.as_view(), name='delete'),
    
    # AJAX endpoints
    path('mark-read/', views.mark_notification_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_notifications_read, name='mark_all_read'),
    path('delete/', views.delete_notification, name='delete_ajax'),
    path('send-test/', views.send_test_notification, name='send_test'),
    path('dismiss/<int:notification_id>/', views.dismiss_notification, name='dismiss'),
    path('search/', views.notification_search, name='search'),
    path('unread-count/', views.get_unread_count, name='unread_count'),
    
    # Notification template URLs
    path('templates/', views.NotificationTemplateListView.as_view(), name='template_list'),
    path('templates/<int:pk>/', views.NotificationTemplateDetailView.as_view(), name='template_detail'),
    
    # User preference URLs
    path('preferences/', views.notification_preferences, name='preferences'),
    path('stats/', views.notification_stats, name='stats'),
    path('settings/', views.notification_settings, name='settings'),
    
    # Batch processing URLs
    path('batch/create/', views.create_notification_batch, name='batch_create'),
    path('batch/<int:batch_id>/', views.notification_batch_detail, name='batch_detail'),
    
    # WebSocket endpoints (these are handled by Channels routing)
    # path('ws/notifications/', views.NotificationConsumer.as_asgi()),
    # path('ws/metrics/', views.RealtimeMetricsConsumer.as_asgi()),
    # path('ws/collaboration/', views.CollaborationConsumer.as_asgi()),
]
