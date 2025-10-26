from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import Notification, NotificationTemplate, NotificationPreference, NotificationHistory, NotificationBatch
from .forms import NotificationForm, NotificationPreferenceForm
from .tasks import send_notification_email, send_notification_push, process_notification_batch

class NotificationListView(LoginRequiredMixin, ListView):
    """List user notifications"""
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter == 'unread':
            queryset = queryset.filter(is_read=False)
        elif status_filter == 'read':
            queryset = queryset.filter(is_read=True)
        elif status_filter == 'archived':
            queryset = queryset.filter(is_archived=True)
        
        # Filter by type
        type_filter = self.request.GET.get('type')
        if type_filter:
            queryset = queryset.filter(notification_type=type_filter)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(message__icontains=search_query)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_types'] = Notification.NOTIFICATION_TYPES
        context['status_filter'] = self.request.GET.get('status', '')
        context['type_filter'] = self.request.GET.get('type', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context

class NotificationDetailView(LoginRequiredMixin, DetailView):
    """View notification details"""
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Mark notification as read when viewed
        if not self.object.is_read:
            self.object.mark_as_read()
        
        # Get notification history
        context['history'] = self.object.history.all()
        
        return context

class NotificationDeleteView(LoginRequiredMixin, DeleteView):
    """Delete notification"""
    model = Notification
    success_url = reverse_lazy('notifications:list')
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        # Archive instead of delete for soft delete
        self.object.archive()
        
        return redirect(success_url)

@login_required
@require_http_methods(["POST"])
def mark_notification_read(request):
    """Mark a notification as read"""
    try:
        notification_id = request.POST.get('notification_id')
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        
        if not notification.is_read:
            notification.mark_as_read()
            
            # Send WebSocket update
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'user_{request.user.id}_notifications',
                {
                    'type': 'notification_message',
                    'notification': {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'type': notification.notification_type,
                        'is_read': True,
                        'created_at': notification.created_at.isoformat(),
                    }
                }
            )
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    try:
        request.user.notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        
        # Send WebSocket update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{request.user.id}_notifications',
            {
                'type': 'notification_message',
                'notification': {
                    'type': 'all_read',
                    'message': 'All notifications marked as read',
                    'timestamp': timezone.now().isoformat(),
                }
            }
        )
        
        return JsonResponse({'success': True, 'count': request.user.notifications.filter(is_read=False).count()})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def delete_notification(request):
    """Delete a notification"""
    try:
        notification_id = request.POST.get('notification_id')
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        
        # Archive instead of delete
        notification.archive()
        
        # Send WebSocket update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{request.user.id}_notifications',
            {
                'type': 'notification_message',
                'notification': {
                    'type': 'deleted',
                    'id': notification.id,
                    'message': 'Notification deleted',
                    'timestamp': timezone.now().isoformat(),
                }
            }
        )
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def send_test_notification(request):
    """Send a test notification to the current user"""
    try:
        notification = Notification.objects.create(
            user=request.user,
            title="Test Notification",
            message="This is a test notification to verify the real-time system is working.",
            notification_type="info",
            is_priority=True,
            source="test",
            data={"test": True}
        )
        
        # Send WebSocket notification
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{request.user.id}_notifications',
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
        
        return JsonResponse({
            'success': True, 
            'message': 'Test notification sent successfully',
            'notification_id': notification.id
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

class NotificationTemplateListView(LoginRequiredMixin, ListView):
    """List notification templates"""
    model = NotificationTemplate
    template_name = 'notifications/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = NotificationTemplate.objects.all()
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(title_template__icontains=search_query) |
                Q(message_template__icontains=search_query)
            )
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class NotificationTemplateDetailView(LoginRequiredMixin, DetailView):
    """View notification template details"""
    model = NotificationTemplate
    template_name = 'notifications/template_detail.html'
    context_object_name = 'template'

@login_required
def notification_preferences(request):
    """User notification preferences"""
    try:
        preference, created = NotificationPreference.objects.get_or_create(user=request.user)
    except:
        preference = None
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            preference = form.save()
            return redirect('notifications:preferences')
    else:
        form = NotificationPreferenceForm(instance=preference)
    
    return render(request, 'notifications/preferences.html', {
        'form': form,
        'notification_types': Notification.NOTIFICATION_TYPES,
    })

@login_required
def notification_stats(request):
    """User notification statistics"""
    user = request.user
    
    # Get notification counts
    total_notifications = user.notifications.count()
    unread_notifications = user.notifications.filter(is_read=False).count()
    read_notifications = user.notifications.filter(is_read=True).count()
    archived_notifications = user.notifications.filter(is_archived=True).count()
    
    # Get notification type counts
    type_counts = user.notifications.values('notification_type').annotate(count=Count('id'))
    
    # Get last 30 days activity
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    recent_notifications = user.notifications.filter(created_at__gte=thirty_days_ago)
    
    # Calculate engagement metrics
    engagement_metrics = {
        'open_rate': 0,
        'click_rate': 0,
        'response_time': 0,
    }
    
    # Get notification history for engagement calculation
    history = NotificationHistory.objects.filter(
        notification__user=user,
        status__in=['read', 'clicked']
    ).order_by('-created_at')[:100]
    
    if history:
        # Calculate engagement rates
        delivered = history.filter(status='delivered').count()
        read = history.filter(status='read').count()
        clicked = history.filter(status='clicked').count()
        
        if delivered > 0:
            engagement_metrics['open_rate'] = (read / delivered) * 100
        if read > 0:
            engagement_metrics['click_rate'] = (clicked / read) * 100
        
        # Calculate average response time (time from sent to read)
        response_times = []
        for item in history.filter(status='read'):
            if item.read_at and item.created_at:
                response_time = (item.read_at - item.created_at).total_seconds()
                response_times.append(response_time)
        
        if response_times:
            engagement_metrics['response_time'] = sum(response_times) / len(response_times)
    
    return render(request, 'notifications/stats.html', {
        'total_notifications': total_notifications,
        'unread_notifications': unread_notifications,
        'read_notifications': read_notifications,
        'archived_notifications': archived_notifications,
        'type_counts': type_counts,
        'recent_notifications': recent_notifications[:10],
        'engagement_metrics': engagement_metrics,
    })

@login_required
def notification_settings(request):
    """Advanced notification settings"""
    return render(request, 'notifications/settings.html')

@login_required
@require_http_methods(["POST"])
def create_notification_batch(request):
    """Create a notification batch"""
    try:
        template_id = request.POST.get('template_id')
        user_ids = request.POST.get('user_ids', '').split(',')
        context_data = json.loads(request.POST.get('context_data', '{}'))
        
        template = get_object_or_404(NotificationTemplate, id=template_id)
        
        # Create batch
        batch = NotificationBatch.objects.create(
            name=f"Batch - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            description=request.POST.get('description', ''),
            template=template,
            context=context_data,
            total_count=len(user_ids),
            metadata={'user_ids': user_ids}
        )
        
        # Process batch asynchronously
        process_notification_batch.delay(batch.id)
        
        return JsonResponse({'success': True, 'batch_id': batch.id})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def notification_batch_detail(request, batch_id):
    """View notification batch details"""
    batch = get_object_or_404(NotificationBatch, id=batch_id)
    
    # Get associated notifications
    notifications = Notification.objects.filter(
        source__startswith=f'batch:{batch_id}'
    ).order_by('-created_at')
    
    return render(request, 'notifications/batch_detail.html', {
        'batch': batch,
        'notifications': notifications,
    })

@login_required
def get_unread_count(request):
    """Get unread notification count for AJAX requests"""
    try:
        count = request.user.notifications.filter(is_read=False).count()
        return JsonResponse({'count': count})
    except Exception as e:
        return JsonResponse({'count': 0, 'error': str(e)}, status=400)

@login_required
def dismiss_notification(request, notification_id):
    """Dismiss a notification without marking as read"""
    try:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        
        # Create history record for dismissal
        NotificationHistory.objects.create(
            notification=notification,
            channel='in_app',
            status='dismissed'
        )
        
        # Send WebSocket update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{request.user.id}_notifications',
            {
                'type': 'notification_message',
                'notification': {
                    'type': 'dismissed',
                    'id': notification.id,
                    'message': 'Notification dismissed',
                    'timestamp': timezone.now().isoformat(),
                }
            }
        )
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def notification_search(request):
    """Search notifications"""
    query = request.GET.get('q', '')
    
    if len(query) < 3:
        return JsonResponse({'results': []})
    
    notifications = Notification.objects.filter(
        user=request.user,
        Q(title__icontains=query) | Q(message__icontains=query)
    ).order_by('-created_at')[:20]
    
    results = []
    for notification in notifications:
        results.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
            'type': notification.notification_type,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat()
        })
    
    return JsonResponse({'results': results})
