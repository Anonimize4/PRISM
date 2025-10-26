from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class Notification(models.Model):
    """
    Enhanced notification model with real-time capabilities
    """
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
        ('application', 'Application Update'),
        ('message', 'New Message'),
        ('deadline', 'Deadline Reminder'),
        ('system', 'System Notification'),
        ('collaboration', 'Collaboration'),
        ('metrics', 'Metrics Update'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    
    # Enhanced notification data storage
    data = models.JSONField(default=dict, blank=True)
    
    # Status tracking
    is_read = models.BooleanField(default=False)
    is_priority = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Additional metadata
    source = models.CharField(max_length=100, blank=True, help_text="Source of the notification")
    target_url = models.CharField(max_length=500, blank=True, help_text="URL for notification action")
    action_required = models.BooleanField(default=False, help_text="Whether user action is required")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_unread(self):
        """Mark notification as unread"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])
    
    def archive(self):
        """Archive the notification"""
        self.is_archived = True
        self.save(update_fields=['is_archived'])
    
    def unarchive(self):
        """Unarchive the notification"""
        self.is_archived = False
        self.save(update_fields=['is_archived'])
    
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def get_absolute_url(self):
        """Get absolute URL for notification action"""
        return self.target_url or "/"

class NotificationTemplate(models.Model):
    """
    Template for creating repeated notifications
    """
    name = models.CharField(max_length=100, unique=True)
    title_template = models.CharField(max_length=200)
    message_template = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Notification.NOTIFICATION_TYPES)
    
    # Template variables that can be replaced
    template_variables = models.JSONField(default=dict, help_text="Variables that can be replaced in templates")
    
    # Default settings
    is_priority = models.BooleanField(default=False)
    default_target_url = models.CharField(max_length=500, blank=True)
    action_required = models.BooleanField(default=False)
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def render(self, context=None):
        """Render template with context variables"""
        context = context or {}
        
        # Render title
        title = self.title_template.format(**context)
        
        # Render message
        message = self.message_template.format(**context)
        
        return {
            'title': title,
            'message': message,
            'notification_type': self.notification_type,
            'is_priority': self.is_priority,
            'action_required': self.action_required,
            'target_url': context.get('target_url', self.default_target_url)
        }
    
    def create_notification(self, user, context=None):
        """Create a notification from this template"""
        rendered = self.render(context)
        
        notification = Notification.objects.create(
            user=user,
            title=rendered['title'],
            message=rendered['message'],
            notification_type=rendered['notification_type'],
            is_priority=rendered['is_priority'],
            action_required=rendered['action_required'],
            target_url=rendered['target_url'],
            source=f'template:{self.name}'
        )
        
        # Update template usage
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])
        
        return notification

class NotificationPreference(models.Model):
    """
    User notification preferences
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Email notifications
    email_notifications = models.BooleanField(default=True)
    email_frequency = models.CharField(
        max_length=20,
        choices=[('immediate', 'Immediate'), 'daily', 'weekly', 'never'],
        default='immediate'
    )
    
    # Push notifications
    push_notifications = models.BooleanField(default=True)
    
    # In-app notifications
    in_app_notifications = models.BooleanField(default=True)
    
    # Notification types preferences
    email_types = models.JSONField(default=dict, help_text="Notification types to email")
    push_types = models.JSONField(default=dict, help_text="Notification types to push")
    in_app_types = models.JSONField(default=dict, help_text="Notification types to show in-app")
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_start = models.TimeField(null=True, blank=True)
    quiet_end = models.TimeField(null=True, blank=True)
    
    # Do not disturb
    do_not_disturb = models.BooleanField(default=False)
    do_not_disturb_until = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Notification Preferences"
    
    def __str__(self):
        return f"{self.user.username} - Notification Preferences"
    
    def should_send_notification(self, notification_type, notification_time=None):
        """Check if notification should be sent based on preferences"""
        if not notification_time:
            notification_time = timezone.now()
        
        # Check if user has do not disturb enabled
        if self.do_not_disturb:
            if self.do_not_disturb_until and notification_time < self.do_not_disturb_until:
                return False
        
        # Check quiet hours
        if self.quiet_hours_enabled and self.quiet_start and self.quiet_end:
            current_time = notification_time.time()
            if self.quiet_start <= self.quiet_end:
                # Normal day
                if self.quiet_start <= current_time <= self.quiet_end:
                    return False
            else:
                # Overnight quiet hours
                if current_time >= self.quiet_start or current_time <= self.quiet_end:
                    return False
        
        # Check notification type preferences
        type_preferences = getattr(self, f'{self.get_channel_type()}_types', {})
        
        if notification_type in type_preferences:
            return type_preferences[notification_type]
        
        return True
    
    def get_channel_type(self):
        """Get the default channel type for preferences"""
        # This could be extended to be more sophisticated
        return 'in_app'

class NotificationHistory(models.Model):
    """
    Track notification delivery and engagement
    """
    NOTIFICATION_STATUS = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('clicked', 'Clicked'),
        ('dismissed', 'Dismissed'),
        ('failed', 'Failed'),
    ]
    
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Delivery information
    channel = models.CharField(max_length=20, choices=[('email', 'Email'), ('push', 'Push'), ('in_app', 'In-App')])
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification', '-created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['channel', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.notification.title} ({self.status})"
    
    def mark_delivered(self):
        """Mark as delivered"""
        if self.status != 'delivered':
            self.status = 'delivered'
            self.delivered_at = timezone.now()
            self.save(update_fields=['status', 'delivered_at'])
    
    def mark_read(self):
        """Mark as read"""
        if self.status != 'read':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])
    
    def mark_clicked(self):
        """Mark as clicked"""
        if self.status != 'clicked':
            self.status = 'clicked'
            self.clicked_at = timezone.now()
            self.save(update_fields=['status', 'clicked_at'])
    
    def mark_dismissed(self):
        """Mark as dismissed"""
        if self.status != 'dismissed':
            self.status = 'dismissed'
            self.dismissed_at = timezone.now()
            self.save(update_fields=['status', 'dismissed_at'])

class NotificationBatch(models.Model):
    """
    Track batches of notifications for bulk operations
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Batch details
    total_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    read_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('sending', 'Sending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    context = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Batch {self.name} - {self.status}"
    
    def start_sending(self):
        """Start sending batch"""
        self.status = 'sending'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def complete(self):
        """Mark batch as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def fail(self):
        """Mark batch as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
