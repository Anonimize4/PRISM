from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification, NotificationHistory, NotificationPreference
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Notification)
def create_notification_history(sender, instance, created, **kwargs):
    """
    Create notification history record when notification is created
    """
    if created:
        # Create initial history record for delivery
        NotificationHistory.objects.create(
            notification=instance,
            user=instance.user,
            channel='in_app',
            status='created'
        )

@receiver(post_save, sender=User)
def create_default_notification_preferences(sender, instance, created, **kwargs):
    """
    Create default notification preferences for new users
    """
    if created:
        NotificationPreference.objects.create(
            user=instance,
            email_notifications=True,
            email_frequency='immediate',
            push_notifications=True,
            in_app_notifications=True,
            email_types={'info': True, 'success': True, 'warning': True, 'error': True, 'application': True, 'message': True},
            push_types={'info': True, 'success': True, 'warning': True, 'error': True, 'application': True, 'message': True},
            in_app_types={'info': True, 'success': True, 'warning': True, 'error': True, 'application': True, 'message': True, 'deadline': True, 'system': True, 'collaboration': True, 'metrics': True}
        )

@receiver(pre_save, sender=Notification)
def handle_notification_status_change(sender, instance, **kwargs):
    """
    Handle notification status changes and send appropriate notifications
    """
    try:
        # Get existing notification if it exists
        existing = Notification.objects.get(pk=instance.pk) if instance.pk else None
        
        # Check if notification was just marked as read
        if existing and not existing.is_read and instance.is_read:
            logger.info(f"Notification {instance.id} marked as read by user {instance.user.id}")
            
            # Send real-time WebSocket update
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'user_{instance.user.id}_notifications',
                {
                    'type': 'notification_message',
                    'notification': {
                        'type': 'read',
                        'id': instance.id,
                        'timestamp': timezone.now().isoformat(),
                    }
                }
            )
            
            # Update history record
            try:
                history = NotificationHistory.objects.get(
                    notification=instance,
                    user=instance.user,
                    status='delivered'
                )
                history.mark_read()
            except NotificationHistory.DoesNotExist:
                logger.warning(f"No history record found for notification {instance.id}")
                
    except Notification.DoesNotExist:
        pass  # New notification, no existing record

@receiver(post_save, sender=Notification)
def send_notification_via_channels(sender, instance, created, **kwargs):
    """
    Send notification through different channels based on user preferences
    """
    if not created:
        return  # Only handle new notifications
    
    try:
        # Get user preferences
        preference = instance.user.notificationpreference
        
        # Skip if notifications are disabled for this type
        if not preference.should_send_notification(instance.notification_type):
            logger.info(f"Skipping notification for user {instance.user.id} - type disabled")
            return
        
        # Send real-time notification via WebSocket
        if preference.in_app_notifications:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'user_{instance.user.id}_notifications',
                {
                    'type': 'notification_message',
                    'notification': {
                        'id': instance.id,
                        'title': instance.title,
                        'message': instance.message,
                        'type': instance.notification_type,
                        'is_read': instance.is_read,
                        'created_at': instance.created_at.isoformat(),
                        'data': instance.data,
                    }
                }
            )
            
            # Update history to delivered
            try:
                history = NotificationHistory.objects.get(
                    notification=instance,
                    user=instance.user,
                    status='created'
                )
                history.mark_delivered()
            except NotificationHistory.DoesNotExist:
                # Create delivered history record
                NotificationHistory.objects.create(
                    notification=instance,
                    user=instance.user,
                    channel='in_app',
                    status='delivered'
                )
        
        # Send email notification if enabled
        if preference.email_notifications and preference.email_frequency == 'immediate':
            send_notification_email_task.delay(instance.id, instance.user.id)
        
        # Send push notification if enabled and token exists
        if preference.push_notifications:
            # Check if user has push token (this would be set from mobile devices)
            if hasattr(instance.user, 'push_notification_token') and instance.user.push_notification_token:
                send_notification_push_task.delay(instance.id, instance.user.id)
        
        logger.info(f"Notification {instance.id} sent to user {instance.user.id}")
        
    except NotificationPreference.DoesNotExist:
        logger.warning(f"No notification preferences found for user {instance.user.id}")
    except Exception as e:
        logger.error(f"Error sending notification {instance.id}: {str(e)}")

@receiver(post_save, sender=Notification)
def handle_scheduled_notifications(sender, instance, created, **kwargs):
    """
    Handle scheduled notifications
    """
    if not created or not instance.scheduled_time:
        return
    
    # If notification is scheduled for later, don't send immediately
    if instance.scheduled_time > timezone.now():
        logger.info(f"Scheduled notification {instance.id} for {instance.scheduled_time}")
        return
    
    # If scheduled time has passed, send immediately
    from .tasks import send_realtime_notification, send_notification_email, send_notification_push
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    # Send real-time notification
    send_realtime_notification.delay(instance.id, instance.user.id)
    
    # Send email and push notifications if preferences allow
    try:
        preference = instance.user.notificationpreference
        if preference.email_notifications:
            send_notification_email.delay(instance.id, instance.user.id)
        if preference.push_notifications and hasattr(instance.user, 'push_notification_token'):
            send_notification_push.delay(instance.id, instance.user.id)
    except NotificationPreference.DoesNotExist:
        pass
    
    logger.info(f"Sent scheduled notification {instance.id} to user {instance.user.id}")

def send_notification_email_task(notification_id, user_id):
    """
    Helper function to send email notification (can be called from signals or tasks)
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        user = User.objects.get(id=user_id)
        
        subject = notification.title
        message = notification.message
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@prism.com')
        recipient_list = [user.email]
        
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            html_message=message,
            fail_silently=False
        )
        
        # Create history record
        NotificationHistory.objects.create(
            notification=notification,
            user=user,
            channel='email',
            status='sent'
        )
        
        logger.info(f"Email notification sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Error sending email notification: {str(e)}")
        # Create failed history record
        if 'notification' in locals() and 'user' in locals():
            NotificationHistory.objects.create(
                notification=notification,
                user=user,
                channel='email',
                status='failed',
                metadata={'error': str(e)}
            )

def send_notification_push_task(notification_id, user_id):
    """
    Helper function to send push notification (can be called from signals or tasks)
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        user = User.objects.get(id=user_id)
        
        # Check if user has push token
        if hasattr(user, 'push_notification_token') and user.push_notification_token:
            # Here you would integrate with a push notification service
            # For now, just create a history record
            NotificationHistory.objects.create(
                notification=notification,
                user=user,
                channel='push',
                status='sent'
            )
            
            logger.info(f"Push notification sent to user {user.id}")
        
    except Exception as e:
        logger.error(f"Error sending push notification: {str(e)}")

# User activity signals
def send_login_activity_notification(sender, user, request, **kwargs):
    """
    Send notification when user logs in
    """
    try:
        Notification.objects.create(
            user=user,
            title="Login Activity",
            message=f"You have successfully logged in from {request.META.get('REMOTE_ADDR', 'unknown')}",
            notification_type="system",
            data={
                'activity_type': 'login',
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'timestamp': timezone.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error sending login notification: {str(e)}")

def send_profile_update_notification(sender, user, old_data, new_data, **kwargs):
    """
    Send notification when user profile is updated
    """
    try:
        changed_fields = []
        for key, old_value in old_data.items():
            if key in new_data and old_value != new_data[key]:
                changed_fields.append(key)
        
        if changed_fields:
            Notification.objects.create(
                user=user,
                title="Profile Updated",
                message=f"Your profile has been updated. Changed fields: {', '.join(changed_fields)}",
                notification_type="system",
                data={
                    'activity_type': 'profile_update',
                    'changed_fields': changed_fields,
                    'timestamp': timezone.now().isoformat()
                }
            )
    except Exception as e:
        logger.error(f"Error sending profile update notification: {str(e)}")

def send_password_change_notification(sender, user, request, **kwargs):
    """
    Send notification when user changes password
    """
    try:
        Notification.objects.create(
            user=user,
            title="Password Changed",
            message="Your password has been successfully changed.",
            notification_type="security",
            is_priority=True,
            action_required=True,
            data={
                'activity_type': 'password_change',
                'ip_address': request.META.get('REMOTE_ADDR', 'unknown'),
                'timestamp': timezone.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error sending password change notification: {str(e)}")

# Connect these signals to the appropriate user activities
# These would be connected in the apps.py ready() method
