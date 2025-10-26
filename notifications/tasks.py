from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_notification_email(notification_id, user_id):
    """Send email notification to user"""
    try:
        from .models import Notification, NotificationHistory
        
        notification = Notification.objects.get(id=notification_id)
        user = User.objects.get(id=user_id)
        
        # Get user preferences
        try:
            preference = user.notificationpreference
            if not (preference.email_notifications and 
                   preference.should_send_notification(notification.notification_type)):
                return {'success': False, 'reason': 'Email notifications disabled for this type'}
        except:
            return {'success': False, 'reason': 'User preferences not found'}
        
        # Send email
        subject = notification.title
        message = notification.message
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@prism.com')
        recipient_list = [user.email]
        
        try:
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
            return {'success': True, 'user_id': user_id, 'notification_id': notification_id}
            
        except Exception as e:
            logger.error(f"Failed to send email to {user.email}: {str(e)}")
            # Create failed history record
            NotificationHistory.objects.create(
                notification=notification,
                user=user,
                channel='email',
                status='failed',
                metadata={'error': str(e)}
            )
            return {'success': False, 'reason': str(e)}
            
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {'success': False, 'reason': 'Notification not found'}
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'reason': 'User not found'}
    except Exception as e:
        logger.error(f"Error in send_notification_email task: {str(e)}")
        return {'success': False, 'reason': str(e)}

@shared_task
def send_notification_push(notification_id, user_id):
    """Send push notification to user"""
    try:
        from .models import Notification, NotificationHistory
        
        notification = Notification.objects.get(id=notification_id)
        user = User.objects.get(id=user_id)
        
        # Get user preferences
        try:
            preference = user.notificationpreference
            if not (preference.push_notifications and 
                   preference.should_send_notification(notification.notification_type)):
                return {'success': False, 'reason': 'Push notifications disabled for this type'}
        except:
            return {'success': False, 'reason': 'User preferences not found'}
        
        # Get push notification token (this would come from a mobile device management system)
        # For now, we'll simulate the push notification
        push_token = getattr(user, 'push_notification_token', None)
        
        if not push_token:
            logger.warning(f"No push token found for user {user_id}")
            return {'success': False, 'reason': 'No push token found'}
        
        # Here you would integrate with a push notification service like:
        # - Firebase Cloud Messaging (FCM)
        # - Apple Push Notification Service (APNS)
        # - OneSignal
        # - Custom WebSocket implementation
        
        # For simulation, we'll create a history record
        NotificationHistory.objects.create(
            notification=notification,
            user=user,
            channel='push',
            status='sent'
        )
        
        logger.info(f"Push notification sent to user {user_id}")
        return {'success': True, 'user_id': user_id, 'notification_id': notification_id}
        
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {'success': False, 'reason': 'Notification not found'}
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'reason': 'User not found'}
    except Exception as e:
        logger.error(f"Error in send_notification_push task: {str(e)}")
        return {'success': False, 'reason': str(e)}

@shared_task
def send_realtime_notification(notification_id, user_id):
    """Send real-time notification via WebSocket"""
    try:
        from .models import Notification, NotificationHistory
        
        notification = Notification.objects.get(id=notification_id)
        user = User.objects.get(id=user_id)
        
        # Get user preferences
        try:
            preference = user.notificationpreference
            if not (preference.in_app_notifications and 
                   preference.should_send_notification(notification.notification_type)):
                return {'success': False, 'reason': 'In-app notifications disabled for this type'}
        except:
            return {'success': False, 'reason': 'User preferences not found'}
        
        # Send WebSocket notification
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{user_id}_notifications',
            {
                'type': 'notification_message',
                'notification': {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.notification_type,
                    'is_read': notification.is_read,
                    'created_at': notification.created_at.isoformat(),
                    'data': notification.data,
                }
            }
        )
        
        # Create history record
        NotificationHistory.objects.create(
            notification=notification,
            user=user,
            channel='in_app',
            status='delivered'
        )
        
        logger.info(f"Real-time notification sent to user {user_id}")
        return {'success': True, 'user_id': user_id, 'notification_id': notification_id}
        
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {'success': False, 'reason': 'Notification not found'}
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'reason': 'User not found'}
    except Exception as e:
        logger.error(f"Error in send_realtime_notification task: {str(e)}")
        return {'success': False, 'reason': str(e)}

@shared_task
def process_notification_batch(batch_id):
    """Process a notification batch"""
    try:
        from .models import NotificationBatch, Notification
        
        batch = NotificationBatch.objects.get(id=batch_id)
        
        if batch.status != 'pending':
            logger.error(f"Batch {batch_id} is not in pending status")
            return {'success': False, 'reason': 'Batch not in pending status'}
        
        # Start processing
        batch.start_sending()
        
        # Get users to notify
        user_ids = batch.metadata.get('user_ids', [])
        if not user_ids:
            logger.error(f"No user IDs found in batch {batch_id}")
            batch.fail()
            return {'success': False, 'reason': 'No user IDs found'}
        
        # Create notifications for each user
        created_notifications = []
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                
                # Render template with context
                context = batch.context.copy()
                context.update({
                    'user_name': user.get_full_name() or user.username,
                    'user_email': user.email,
                })
                
                notification = batch.template.create_notification(user, context)
                created_notifications.append(notification)
                
                # Update batch progress
                batch.sent_count += 1
                batch.save(update_fields=['sent_count'])
                
                # Send notification via different channels
                # (This could be parallelized using Celery)
                send_realtime_notification.delay(notification.id, user_id)
                
                # Optionally send email and push notifications
                if user.notificationpreference.email_notifications:
                    send_notification_email.delay(notification.id, user_id)
                
                if user.notificationpreference.push_notifications:
                    send_notification_push.delay(notification.id, user_id)
                
            except User.DoesNotExist:
                logger.warning(f"User {user_id} not found, skipping")
                batch.failed_count += 1
                batch.save(update_fields=['failed_count'])
            except Exception as e:
                logger.error(f"Error creating notification for user {user_id}: {str(e)}")
                batch.failed_count += 1
                batch.save(update_fields=['failed_count'])
        
        # Mark batch as completed
        batch.complete()
        
        logger.info(f"Batch {batch_id} processed successfully. Created {len(created_notifications)} notifications.")
        return {
            'success': True, 
            'batch_id': batch_id, 
            'created_count': len(created_notifications),
            'failed_count': batch.failed_count
        }
        
    except NotificationBatch.DoesNotExist:
        logger.error(f"Batch {batch_id} not found")
        return {'success': False, 'reason': 'Batch not found'}
    except Exception as e:
        logger.error(f"Error in process_notification_batch task: {str(e)}")
        if 'batch' in locals():
            batch.fail()
        return {'success': False, 'reason': str(e)}

@shared_task
def cleanup_old_notifications():
    """Clean up expired and old notifications"""
    try:
        from .models import Notification, NotificationHistory
        
        # Delete expired notifications
        expired_count = Notification.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        # Delete old notification history (older than 90 days)
        ninety_days_ago = timezone.now() - timezone.timedelta(days=90)
        old_history_count = NotificationHistory.objects.filter(
            created_at__lt=ninety_days_ago
        ).delete()[0]
        
        # Delete archived notifications older than 180 days
        one_eighty_days_ago = timezone.now() - timezone.timedelta(days=180)
        archived_count = Notification.objects.filter(
            is_archived=True,
            created_at__lt=one_eighty_days_ago
        ).delete()[0]
        
        logger.info(f"Cleanup completed: {expired_count} expired, {old_history_count} old history, {archared_count} archived notifications deleted")
        
        return {
            'success': True,
            'expired_count': expired_count,
            'old_history_count': old_history_count,
            'archived_count': archived_count
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_notifications task: {str(e)}")
        return {'success': False, 'reason': str(e)}

@shared_task
def generate_notification_analytics():
    """Generate notification analytics and metrics"""
    try:
        from .models import Notification, NotificationHistory
        from django.db.models import Count, Q
        from datetime import datetime, timedelta
        
        # Get time range (last 30 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Overall statistics
        total_notifications = Notification.objects.filter(
            created_at__gte=start_date
        ).count()
        
        total_delivered = NotificationHistory.objects.filter(
            status='delivered',
            created_at__gte=start_date
        ).count()
        
        total_read = NotificationHistory.objects.filter(
            status='read',
            created_at__gte=start_date
        ).count()
        
        total_clicked = NotificationHistory.objects.filter(
            status='clicked',
            created_at__gte=start_date
        ).count()
        
        # Type distribution
        type_distribution = Notification.objects.filter(
            created_at__gte=start_date
        ).values('notification_type').annotate(count=Count('id'))
        
        # Channel distribution
        channel_distribution = NotificationHistory.objects.filter(
            created_at__gte=start_date
        ).values('channel').annotate(count=Count('id'))
        
        # Daily trend
        daily_trend = []
        for i in range(30):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            daily_count = Notification.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).count()
            
            daily_trend.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'count': daily_count
            })
        
        analytics = {
            'period': '30_days',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_notifications': total_notifications,
            'total_delivered': total_delivered,
            'total_read': total_read,
            'total_clicked': total_clicked,
            'delivery_rate': (total_delivered / total_notifications * 100) if total_notifications > 0 else 0,
            'open_rate': (total_read / total_delivered * 100) if total_delivered > 0 else 0,
            'click_rate': (total_clicked / total_read * 100) if total_read > 0 else 0,
            'type_distribution': list(type_distribution),
            'channel_distribution': list(channel_distribution),
            'daily_trend': daily_trend,
            'generated_at': timezone.now().isoformat()
        }
        
        # Store analytics (could be saved to a model or external system)
        logger.info(f"Notification analytics generated: {analytics}")
        
        return {
            'success': True,
            'analytics': analytics
        }
        
    except Exception as e:
        logger.error(f"Error in generate_notification_analytics task: {str(e)}")
        return {'success': False, 'reason': str(e)}

@shared_task
def check_scheduled_notifications():
    """Check and send scheduled notifications"""
    try:
        from .models import Notification
        
        # Get notifications that are scheduled to be sent now
        now = timezone.now()
        scheduled_notifications = Notification.objects.filter(
            scheduled_time__lte=now,
            is_read=False,
            created_at__lt=now  # Ensure notification exists before scheduled time
        )
        
        sent_count = 0
        for notification in scheduled_notifications:
            # Send real-time notification
            send_realtime_notification.delay(notification.id, notification.user.id)
            sent_count += 1
            
            # Mark as sent (or keep as unread until user interacts)
            logger.info(f"Sent scheduled notification {notification.id} to user {notification.user.id}")
        
        logger.info(f"Processed {sent_count} scheduled notifications")
        return {'success': True, 'sent_count': sent_count}
        
    except Exception as e:
        logger.error(f"Error in check_scheduled_notifications task: {str(e)}")
        return {'success': False, 'reason': str(e)}

@shared_task
def send_user_activity_notification(user_id, activity_type, activity_data):
    """Send user activity notification"""
    try:
        from .models import Notification
        
        user = User.objects.get(id=user_id)
        
        # Create activity notification
        notification = Notification.objects.create(
            user=user,
            title=f"Activity: {activity_type.replace('_', ' ').title()}",
            message=f"Your {activity_type.replace('_', ' ')} activity has been recorded.",
            notification_type='activity',
            data={
                'activity_type': activity_type,
                'activity_data': activity_data,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Send real-time notification
        send_realtime_notification.delay(notification.id, user_id)
        
        logger.info(f"Sent activity notification {notification.id} to user {user_id}")
        return {'success': True, 'notification_id': notification.id}
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for activity notification")
        return {'success': False, 'reason': 'User not found'}
    except Exception as e:
        logger.error(f"Error in send_user_activity_notification task: {str(e)}")
        return {'success': False, 'reason': str(e)}
