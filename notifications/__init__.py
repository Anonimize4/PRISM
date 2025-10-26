"""
PRISM Real-Time Notification System

A comprehensive notification system with real-time capabilities, multiple delivery channels,
templates, analytics, and advanced user preferences.

Features:
- Real-time WebSocket notifications
- Email notifications with scheduling
- Push notifications for mobile devices
- Notification templates with variables
- User preference management
- Batch processing
- Analytics and metrics
- Admin interface
- Signal-based automation

Usage:
1. Add 'notifications' to INSTALLED_APPS in settings.py
2. Include notifications.urls in your main urls.py
3. Configure WebSocket routing asgi.py
4. Set up Celery and Redis for background tasks
5. Run migrations: python manage.py migrate

Real-time Features:
- WebSocket connections for live updates
- Typing indicators
- File upload notifications
- Video call invitations
- Screen sharing
- User status updates

Security:
- User authentication required
- Permission-based access
- Secure delivery channels
- Activity tracking
"""

__version__ = '1.0.0'
__author__ = 'PRISM Development Team'
__email__ = 'support@prism.com'

# Package constants
PRIORITY_CHOICES = (
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('urgent', 'Urgent')
)

# Import utility functions that don't depend on Django models
def create_notification(user, title, message, notification_type='info', **kwargs):
    """
    Create a new notification for a user
    
    Args:
        user: User instance
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        **kwargs: Additional notification parameters
    
    Returns:
        Notification instance
    """
    from .models import Notification
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        **kwargs
    )
    
    # Signal will handle the rest
    return notification

def create_notification_from_template(user, template_name, context=None, **kwargs):
    """
    Create a notification from a template
    
    Args:
        user: User instance
        template_name: Name of the template
        context: Context variables for template
        **kwargs: Additional notification parameters
    
    Returns:
        Notification instance
    """
    from .models import NotificationTemplate
    try:
        template = NotificationTemplate.objects.get(name=template_name)
        return template.create_notification(user, context or {}, **kwargs)
    except NotificationTemplate.DoesNotExist:
        raise ValueError(f"Template '{template_name}' not found")

def send_batch_notification(template_name, user_ids, context=None):
    """
    Send notifications to multiple users using a template
    
    Args:
        template_name: Name of the template
        user_ids: List of user IDs
        context: Context variables for template
    
    Returns:
        NotificationBatch instance
    """
    from .models import NotificationBatch, NotificationTemplate
    from .tasks import process_notification_batch
    
    template = NotificationTemplate.objects.get(name=template_name)
    context = context or {}
    
    batch = NotificationBatch.objects.create(
        name=f"Batch - {template_name} - {len(user_ids)} users",
        template=template,
        context=context,
        total_count=len(user_ids),
        metadata={'user_ids': user_ids}
    )
    
    # Process batch asynchronously
    process_notification_batch.delay(batch.id)
    return batch
