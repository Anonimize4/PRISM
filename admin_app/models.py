from django.db import models
from django.conf import settings

class SystemLog(models.Model):
    LOG_LEVEL_CHOICES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical')
    ]
    
    level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES)
    message = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.level} - {self.timestamp}"

class SystemHealth(models.Model):
    cpu_usage = models.DecimalField(max_digits=5, decimal_places=2)
    memory_usage = models.DecimalField(max_digits=5, decimal_places=2)
    disk_usage = models.DecimalField(max_digits=5, decimal_places=2)
    active_users = models.IntegerField()
    database_connections = models.IntegerField()
    server_response_time = models.DecimalField(max_digits=10, decimal_places=3)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"System Health - {self.timestamp}"

class UserActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=50)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp}"

class SystemNotification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('security', 'Security'),
        ('update', 'Update'),
        ('alert', 'Alert'),
        ('info', 'Information')
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.priority}"

class BackupRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="Size in bytes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    backup_type = models.CharField(max_length=20, choices=[
        ('full', 'Full Backup'),
        ('incremental', 'Incremental Backup'),
        ('database', 'Database Only')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Backup {self.filename} - {self.status}"

class SecurityAudit(models.Model):
    AUDIT_TYPE_CHOICES = [
        ('login_attempt', 'Login Attempt'),
        ('password_change', 'Password Change'),
        ('permission_change', 'Permission Change'),
        ('data_access', 'Data Access'),
        ('system_config', 'System Configuration')
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    audit_type = models.CharField(max_length=30, choices=AUDIT_TYPE_CHOICES)
    action = models.CharField(max_length=100)
    resource = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.audit_type} - {self.action} - {self.timestamp}"

class SystemConfiguration(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True, null=True)
    is_sensitive = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.key
