from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import SystemLog, SystemHealth, UserActivity, SystemNotification, BackupRecord, SecurityAudit, SystemConfiguration
from recruitment.models import InternshipApplication
import json

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    # Get system health metrics
    latest_health = SystemHealth.objects.order_by('-timestamp').first()
    
    # Get recent user activity
    recent_activities = UserActivity.objects.order_by('-timestamp')[:10]
    
    # Get system statistics
    total_users = get_user_model().objects.count()
    active_users = get_user_model().objects.filter(last_login__gte=timezone.now() - timezone.timedelta(days=7)).count()
    
    # Get application statistics
    total_applications = InternshipApplication.objects.count()
    pending_applications = InternshipApplication.objects.filter(status='pending').count()
    
    # Get recent system logs
    recent_logs = SystemLog.objects.order_by('-timestamp')[:10]
    
    # Get active system notifications
    active_notifications = SystemNotification.objects.filter(
        is_active=True,
        expires_at__gte=timezone.now()
    ).order_by('-priority')
    
    context = {
        'system_health': latest_health,
        'recent_activities': recent_activities,
        'total_users': total_users,
        'active_users': active_users,
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'recent_logs': recent_logs,
        'active_notifications': active_notifications,
    }
    return render(request, 'admin_app/dashboard.html', context)

@login_required
def user_management(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    users = get_user_model().objects.all().order_by('-date_joined')
    
    # Filtering
    role_filter = request.GET.get('role')
    search_query = request.GET.get('search')
    
    if role_filter:
        users = users.filter(role=role_filter)
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'search_query': search_query,
    }
    return render(request, 'admin_app/user_management.html', context)

@login_required
def create_user(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        role = request.POST.get('role')
        
        User = get_user_model()
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('create_user')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return redirect('create_user')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        
        # Log user creation
        UserActivity.objects.create(
            user=request.user,
            activity_type='user_creation',
            description=f'Created new user: {username} with role: {role}'
        )
        
        messages.success(request, 'User created successfully!')
        return redirect('user_management')
    
    return render(request, 'admin_app/create_user.html')

@login_required
def edit_user(request, user_id):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    User = get_user_model()
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.role = request.POST.get('role')
        user.is_active = request.POST.get('is_active') == 'on'
        user.save()
        
        # Log user update
        UserActivity.objects.create(
            user=request.user,
            activity_type='user_update',
            description=f'Updated user: {user.username}'
        )
        
        messages.success(request, 'User updated successfully!')
        return redirect('user_management')
    
    return render(request, 'admin_app/edit_user.html', {'user': user})

@login_required
def delete_user(request, user_id):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    User = get_user_model()
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        
        # Log user deletion
        UserActivity.objects.create(
            user=request.user,
            activity_type='user_deletion',
            description=f'Deleted user: {username}'
        )
        
        messages.success(request, 'User deleted successfully!')
        return redirect('user_management')
    
    return render(request, 'admin_app/delete_user.html', {'user': user})

@login_required
def system_health_monitoring(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    health_records = SystemHealth.objects.order_by('-timestamp')[:100]
    
    # Get latest metrics
    latest_metrics = SystemHealth.objects.order_by('-timestamp').first()
    
    context = {
        'health_records': health_records,
        'latest_metrics': latest_metrics,
    }
    return render(request, 'admin_app/system_health.html', context)

@login_required
def user_activity_logs(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    activities = UserActivity.objects.all().order_by('-timestamp')
    
    # Filtering
    activity_type = request.GET.get('activity_type')
    user_filter = request.GET.get('user')
    
    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    if user_filter:
        activities = activities.filter(user__username__icontains=user_filter)
    
    # Pagination
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'activity_type': activity_type,
        'user_filter': user_filter,
    }
    return render(request, 'admin_app/user_activity_logs.html', context)

@login_required
def system_logs(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    logs = SystemLog.objects.all().order_by('-timestamp')
    
    # Filtering
    level_filter = request.GET.get('level')
    user_filter = request.GET.get('user')
    
    if level_filter:
        logs = logs.filter(level=level_filter)
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'level_filter': level_filter,
        'user_filter': user_filter,
    }
    return render(request, 'admin_app/system_logs.html', context)

@login_required
def system_notifications(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    notifications = SystemNotification.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        notification_type = request.POST.get('notification_type')
        priority = request.POST.get('priority')
        expires_at = request.POST.get('expires_at')
        
        SystemNotification.objects.create(
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            expires_at=expires_at if expires_at else None
        )
        
        messages.success(request, 'System notification created successfully!')
        return redirect('system_notifications')
    
    return render(request, 'admin_app/system_notifications.html', {'notifications': notifications})

@login_required
def toggle_notification(request, notification_id):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    notification = get_object_or_404(SystemNotification, id=notification_id)
    notification.is_active = not notification.is_active
    notification.save()
    
    messages.success(request, f'Notification {"activated" if notification.is_active else "deactivated"} successfully!')
    return redirect('system_notifications')

@login_required
def backup_management(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    backups = BackupRecord.objects.all().order_by('-created_at')
    
    context = {
        'backups': backups,
    }
    return render(request, 'admin_app/backup_management.html', context)

@login_required
def security_audit(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    audits = SecurityAudit.objects.all().order_by('-timestamp')
    
    # Filtering
    audit_type = request.GET.get('audit_type')
    user_filter = request.GET.get('user')
    
    if audit_type:
        audits = audits.filter(audit_type=audit_type)
    if user_filter:
        audits = audits.filter(user__username__icontains=user_filter)
    
    # Pagination
    paginator = Paginator(audits, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'audit_type': audit_type,
        'user_filter': user_filter,
    }
    return render(request, 'admin_app/security_audit.html', context)

@login_required
def system_configuration(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    configurations = SystemConfiguration.objects.all().order_by('key')
    
    if request.method == 'POST':
        key = request.POST.get('key')
        value = request.POST.get('value')
        description = request.POST.get('description')
        is_sensitive = request.POST.get('is_sensitive') == 'on'
        
        config, created = SystemConfiguration.objects.get_or_create(
            key=key,
            defaults={
                'value': value,
                'description': description,
                'is_sensitive': is_sensitive,
                'modified_by': request.user
            }
        )
        
        if not created:
            config.value = value
            config.description = description
            config.is_sensitive = is_sensitive
            config.modified_by = request.user
            config.save()
        
        messages.success(request, f'Configuration {"created" if created else "updated"} successfully!')
        return redirect('system_configuration')
    
    return render(request, 'admin_app/system_configuration.html', {'configurations': configurations})

@login_required
def analytics_dashboard(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    # Get user statistics by role
    User = get_user_model()
    user_stats = User.objects.values('role').annotate(count=Count('id'))
    
    # Get application statistics
    app_stats = InternshipApplication.objects.values('status').annotate(count=Count('id'))
    
    # Get recent activity trends
    recent_activities = UserActivity.objects.filter(
        timestamp__gte=timezone.now() - timezone.timedelta(days=30)
    ).extra({'date': "date(timestamp)"}).values('date').annotate(count=Count('id')).order_by('date')
    
    # Get system health trends
    health_trends = SystemHealth.objects.filter(
        timestamp__gte=timezone.now() - timezone.timedelta(days=7)
    ).order_by('timestamp')
    
    context = {
        'user_stats': user_stats,
        'app_stats': app_stats,
        'recent_activities': list(recent_activities),
        'health_trends': health_trends,
    }
    
    return render(request, 'admin_app/analytics_dashboard.html', context)

@login_required
def api_system_health(request):
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    latest_health = SystemHealth.objects.order_by('-timestamp').first()
    
    if latest_health:
        data = {
            'cpu_usage': float(latest_health.cpu_usage),
            'memory_usage': float(latest_health.memory_usage),
            'disk_usage': float(latest_health.disk_usage),
            'active_users': latest_health.active_users,
            'database_connections': latest_health.database_connections,
            'server_response_time': float(latest_health.server_response_time),
            'timestamp': latest_health.timestamp.isoformat(),
        }
    else:
        data = {'error': 'No health data available'}
    
    return JsonResponse(data)

@login_required
def api_user_stats(request):
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    User = get_user_model()
    total_users = User.objects.count()
    active_users = User.objects.filter(last_login__gte=timezone.now() - timezone.timedelta(days=7)).count()
    
    user_stats = User.objects.values('role').annotate(count=Count('id'))
    
    data = {
        'total_users': total_users,
        'active_users': active_users,
        'by_role': list(user_stats),
    }
    
    return JsonResponse(data)
