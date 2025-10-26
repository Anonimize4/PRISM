from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = _('Notifications')
    
    def ready(self):
        """
        Initialize the notifications app and register signals
        """
        import notifications.signals
        import notifications.tasks
        
        # Schedule periodic tasks
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        
        # Create or update cleanup task
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='2'
        )
        
        PeriodicTask.objects.update_or_create(
            name='cleanup_old_notifications',
            defaults={
                'crontab': schedule,
                'task': 'notifications.tasks.cleanup_old_notifications',
                'enabled': True
            }
        )
        
        # Create or update analytics task
        schedule2, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='1'
        )
        
        PeriodicTask.objects.update_or_create(
            name='generate_notification_analytics',
            defaults={
                'crontab': schedule2,
                'task': 'notifications.tasks.generate_notification_analytics',
                'enabled': True
            }
        )
        
        # Create or update scheduled notifications task
        schedule3, _ = CrontabSchedule.objects.get_or_create(
            minute='*',
            hour='*'
        )
        
        PeriodicTask.objects.update_or_create(
            name='check_scheduled_notifications',
            defaults={
                'crontab': schedule3,
                'task': 'notifications.tasks.check_scheduled_notifications',
                'enabled': True
            }
        )
