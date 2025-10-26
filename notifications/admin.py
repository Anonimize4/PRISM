from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Notification, NotificationTemplate, NotificationPreference, NotificationHistory, NotificationBatch

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'notification_type', 'is_read', 'is_priority', 'created_at',
        'expires_at_display', 'action_required_display', 'source_display'
    ]
    list_filter = [
        'notification_type', 'is_read', 'is_priority', 'is_archived',
        'action_required', 'created_at', 'expires_at'
    ]
    search_fields = ['title', 'message', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'read_at', 'expires_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'message', 'notification_type')
        }),
        ('Status', {
            'fields': ('is_read', 'is_priority', 'is_archived', 'action_required')
        }),
        ('Timing', {
            'fields': ('created_at', 'read_at', 'expires_at')
        }),
        ('Advanced', {
            'fields': ('source', 'target_url', 'data'),
            'classes': ('collapse',)
        }),
    )
    
    def expires_at_display(self, obj):
        if obj.expires_at:
            return obj.expires_at.strftime('%Y-%m-%d %H:%M')
        return 'Never'
    expires_at_display.short_description = 'Expires At'
    
    def action_required_display(self, obj):
        return "Yes" if obj.action_required else "No"
    action_required_display.short_description = 'Action Required'
    
    def source_display(self, obj):
        if obj.source:
            return obj.source
        return 'Manual'
    source_display.short_description = 'Source'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    actions = ['mark_as_read', 'mark_as_unread', 'archive_notifications', 'delete_expired']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark selected notifications as unread'
    
    def archive_notifications(self, request, queryset):
        updated = queryset.update(is_archived=True)
        self.message_user(request, f'{updated} notifications archived.')
    archive_notifications.short_description = 'Archive selected notifications'
    
    def delete_expired(self, request, queryset):
        expired_count = queryset.filter(expires_at__lt=timezone.now()).count()
        deleted_count, _ = queryset.filter(expires_at__lt=timezone.now()).delete()
        self.message_user(request, f'{deleted_count} expired notifications deleted.')
    delete_expired.short_description = 'Delete expired notifications'

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'notification_type', 'is_priority', 'usage_count', 
        'last_used_display', 'created_at'
    ]
    list_filter = [
        'notification_type', 'is_priority', 'created_at', 'last_used'
    ]
    search_fields = ['name', 'title_template', 'message_template']
    readonly_fields = ['usage_count', 'last_used', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'notification_type', 'title_template', 'message_template')
        }),
        ('Settings', {
            'fields': ('is_priority', 'default_target_url', 'action_required')
        }),
        ('Template Variables', {
            'fields': ('template_variables',),
            'description': 'Define variables that can be used in the template using {variable_name}'
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'last_used', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def last_used_display(self, obj):
        if obj.last_used:
            return obj.last_used.strftime('%Y-%m-%d %H:%M')
        return 'Never'
    last_used_display.short_description = 'Last Used'
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-usage_count')

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'email_notifications', 'push_notifications', 'in_app_notifications',
        'email_frequency_display', 'quiet_hours_enabled', 'do_not_disturb_display'
    ]
    list_filter = [
        'email_notifications', 'push_notifications', 'in_app_notifications',
        'email_frequency', 'quiet_hours_enabled', 'do_not_disturb'
    ]
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Notification Channels', {
            'fields': ('email_notifications', 'email_frequency', 'push_notifications', 'in_app_notifications')
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_enabled', 'quiet_start', 'quiet_end')
        }),
        ('Do Not Disturb', {
            'fields': ('do_not_disturb', 'do_not_disturb_until')
        }),
        ('Notification Type Preferences', {
            'fields': ('email_types', 'push_types', 'in_app_types'),
            'description': 'Configure which notification types to send via each channel'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def email_frequency_display(self, obj):
        return dict(NotificationPreference._meta.get_field('email_frequency').choices).get(obj.email_frequency, obj.email_frequency)
    email_frequency_display.short_description = 'Email Frequency'
    
    def do_not_disturb_display(self, obj):
        return "Yes" if obj.do_not_disturb else "No"
    do_not_disturb_display.short_description = 'Do Not Disturb'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(NotificationHistory)
class NotificationHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'notification', 'user', 'channel', 'status', 'created_at',
        'delivered_at_display', 'read_at_display', 'clicked_at_display'
    ]
    list_filter = [
        'channel', 'status', 'created_at'
    ]
    search_fields = [
        'notification__title', 'user__username', 'user__email'
    ]
    readonly_fields = [
        'notification', 'user', 'channel', 'status', 'created_at',
        'delivered_at', 'read_at', 'clicked_at', 'dismissed_at', 'metadata'
    ]
    date_hierarchy = 'created_at'
    
    def delivered_at_display(self, obj):
        if obj.delivered_at:
            return obj.delivered_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    delivered_at_display.short_description = 'Delivered At'
    
    def read_at_display(self, obj):
        if obj.read_at:
            return obj.read_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    read_at_display.short_description = 'Read At'
    
    def clicked_at_display(self, obj):
        if obj.clicked_at:
            return obj.clicked_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    clicked_at_display.short_description = 'Clicked At'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification', 'user')

@admin.register(NotificationBatch)
class NotificationBatchAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'status', 'total_count', 'sent_count', 'delivered_count',
        'read_count', 'failed_count', 'created_at', 'progress_bar'
    ]
    list_filter = [
        'status', 'created_at'
    ]
    search_fields = ['name', 'description']
    readonly_fields = [
        'total_count', 'sent_count', 'delivered_count', 'read_count',
        'failed_count', 'created_at', 'started_at', 'completed_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'template')
        }),
        ('Progress', {
            'fields': ('status', 'total_count', 'sent_count', 'delivered_count', 'read_count', 'failed_count')
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
        ('Context', {
            'fields': ('context', 'metadata'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_bar(self, obj):
        if obj.total_count > 0:
            progress = (obj.sent_count / obj.total_count) * 100
            return format_html(
                '<div style="width: 100%; background-color: #eee;">'
                '<div style="width: {}%; background-color: #4CAF50; height: 20px; text-align: center; color: white;">'
                '{}%</div></div>', progress, round(progress)
            )
        return '0%'
    progress_bar.short_description = 'Progress'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('template').order_by('-created_at')

# Inline for related objects
class NotificationInline(admin.TabularInline):
    model = Notification
    extra = 0
    readonly_fields = ['created_at', 'notification_type']

class NotificationHistoryInline(admin.TabularInline):
    model = NotificationHistory
    extra = 0
    readonly_fields = ['channel', 'status', 'created_at']
