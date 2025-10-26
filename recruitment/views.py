from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import InternshipApplication, Report, Team, Project, Message, LeaveRequest
from django.core.paginator import Paginator

@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    applications = InternshipApplication.objects.filter(student=request.user).order_by('-applied_date')
    pending_reports = Report.objects.filter(application__student=request.user, feedback__isnull=True)
    notifications = Message.objects.filter(receiver=request.user, timestamp__gte=timezone.now() - timezone.timedelta(days=7))
    
    context = {
        'applications': applications[:5],
        'pending_reports': pending_reports[:3],
        'notifications': notifications[:5],
        'total_applications': applications.count(),
        'accepted_applications': applications.filter(status='accepted').count(),
        'pending_applications': applications.filter(status='pending').count(),
    }
    return render(request, 'recruitment/student_dashboard.html', context)

@login_required
def company_dashboard(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    applications = InternshipApplication.objects.filter(company=request.user).order_by('-applied_date')
    teams = Team.objects.filter(company=request.user)
    pending_leave_requests = LeaveRequest.objects.filter(
        application__company=request.user, 
        status='pending'
    )
    
    context = {
        'applications': applications[:5],
        'teams': teams,
        'pending_leave_requests': pending_leave_requests,
        'total_applications': applications.count(),
        'pending_applications': applications.filter(status='pending').count(),
        'accepted_applications': applications.filter(status='accepted').count(),
    }
    return render(request, 'recruitment/company_dashboard.html', context)

@login_required
def create_application(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    if request.method == 'POST':
        personal_info = request.POST.get('personal_info')
        academic_details = request.POST.get('academic_details')
        preferences = request.POST.get('preferences')
        company_id = request.POST.get('company')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        company = get_object_or_404(User, id=company_id, role='company')
        
        # Get university (could be based on student's profile or selection)
        university = User.objects.filter(role='university').first()
        
        application = InternshipApplication.objects.create(
            student=request.user,
            company=company,
            university=university,
            personal_info=personal_info,
            academic_details=academic_details,
            preferences=preferences
        )
        
        messages.success(request, 'Application submitted successfully!')
        return redirect('application_status')
    
    # Get list of companies for the dropdown
    from django.contrib.auth import get_user_model
    User = get_user_model()
    companies = User.objects.filter(role='company')
    
    return render(request, 'recruitment/create_application.html', {'companies': companies})

@login_required
def application_status(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    applications = InternshipApplication.objects.filter(student=request.user).order_by('-applied_date')
    
    # Pagination
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'recruitment/application_status.html', {'page_obj': page_obj})

@login_required
def manage_applications(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    applications = InternshipApplication.objects.filter(company=request.user).order_by('-applied_date')
    
    # Filtering
    status_filter = request.GET.get('status')
    date_filter = request.GET.get('date')
    major_filter = request.GET.get('major')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    if date_filter:
        applications = applications.filter(applied_date__date=date_filter)
    if major_filter:
        applications = applications.filter(academic_details__icontains=major_filter)
    
    # Pagination
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'recruitment/manage_applications.html', {'page_obj': page_obj})

@login_required
def update_application_status(request, application_id):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    application = get_object_or_404(InternshipApplication, id=application_id, company=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'accepted', 'rejected']:
            application.status = new_status
            application.save()
            
            # Send notification to student
            Message.objects.create(
                sender=request.user,
                receiver=application.student,
                content=f"Your application status has been updated to: {new_status}",
                timestamp=timezone.now()
            )
            
            messages.success(request, f'Application status updated to {new_status}')
        else:
            messages.error(request, 'Invalid status')
    
    return redirect('manage_applications')

@login_required
def submit_weekly_report(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    # Get student's accepted application
    application = InternshipApplication.objects.filter(student=request.user, status='accepted').first()
    if not application:
        messages.error(request, 'You need an accepted application to submit reports')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        week = request.POST.get('week')
        progress = request.POST.get('progress')
        challenges = request.POST.get('challenges')
        achievements = request.POST.get('achievements')
        
        # Check if report for this week already exists
        existing_report = Report.objects.filter(application=application, week=week).first()
        if existing_report:
            existing_report.progress = progress
            existing_report.challenges = challenges
            existing_report.achievements = achievements
            existing_report.save()
            messages.success(request, 'Report updated successfully!')
        else:
            Report.objects.create(
                application=application,
                week=week,
                progress=progress,
                challenges=challenges,
                achievements=achievements
            )
            messages.success(request, 'Report submitted successfully!')
        
        return redirect('report_history')
    
    return render(request, 'recruitment/submit_weekly_report.html', {'application': application})

@login_required
def report_history(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    application = InternshipApplication.objects.filter(student=request.user, status='accepted').first()
    if not application:
        messages.error(request, 'You need an accepted application to view reports')
        return redirect('student_dashboard')
    
    reports = Report.objects.filter(application=application).order_by('-week')
    
    return render(request, 'recruitment/report_history.html', {'reports': reports, 'application': application})

@login_required
def review_reports(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    reports = Report.objects.filter(application__company=request.user, feedback__isnull=True).order_by('-submitted_date')
    
    return render(request, 'recruitment/review_reports.html', {'reports': reports})

@login_required
def submit_feedback(request, report_id):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    report = get_object_or_404(Report, id=report_id, application__company=request.user)
    
    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        report.feedback = feedback
        report.save()
        
        # Send notification to student
        Message.objects.create(
            sender=request.user,
            receiver=report.application.student,
            content=f"You have received feedback on your week {report.week} report",
            timestamp=timezone.now()
        )
        
        messages.success(request, 'Feedback submitted successfully!')
        return redirect('review_reports')
    
    return render(request, 'recruitment/submit_feedback.html', {'report': report})

@login_required
def create_team(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    if request.method == 'POST':
        team_name = request.POST.get('team_name')
        mentor_id = request.POST.get('mentor')
        member_ids = request.POST.getlist('members')
        
        team = Team.objects.create(
            name=team_name,
            company=request.user
        )
        
        if mentor_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            mentor = get_object_or_404(User, id=mentor_id)
            team.mentor = mentor
        
        if member_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            members = User.objects.filter(id__in=member_ids, role='student')
            team.members.set(members)
        
        team.save()
        messages.success(request, 'Team created successfully!')
        return redirect('team_management')
    
    # Get available mentors and accepted students
    from django.contrib.auth import get_user_model
    User = get_user_model()
    mentors = User.objects.filter(role='company')
    accepted_students = User.objects.filter(
        role='student',
        applications__company=request.user,
        applications__status='accepted'
    ).distinct()
    
    return render(request, 'recruitment/create_team.html', {
        'mentors': mentors,
        'accepted_students': accepted_students
    })

@login_required
def team_management(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    teams = Team.objects.filter(company=request.user)
    
    return render(request, 'recruitment/team_management.html', {'teams': teams})

@login_required
def create_project(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        objectives = request.POST.get('objectives')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        team_id = request.POST.get('team')
        
        team = get_object_or_404(Team, id=team_id, company=request.user)
        
        Project.objects.create(
            title=title,
            objectives=objectives,
            start_date=start_date,
            end_date=end_date,
            team=team
        )
        
        messages.success(request, 'Project created successfully!')
        return redirect('project_management')
    
    teams = Team.objects.filter(company=request.user)
    
    return render(request, 'recruitment/create_project.html', {'teams': teams})

@login_required
def project_management(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    projects = Project.objects.filter(team__company=request.user)
    
    return render(request, 'recruitment/project_management.html', {'projects': projects})

@login_required
def messaging(request):
    if request.user.role not in ['student', 'company']:
        return redirect('dashboard')
    
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver')
        content = request.POST.get('content')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        receiver = get_object_or_404(User, id=receiver_id)
        
        Message.objects.create(
            sender=request.user,
            receiver=receiver,
            content=content,
            timestamp=timezone.now()
        )
        
        messages.success(request, 'Message sent successfully!')
        return redirect('messaging')
    
    # Get conversations
    sent_messages = Message.objects.filter(sender=request.user).order_by('-timestamp')
    received_messages = Message.objects.filter(receiver=request.user).order_by('-timestamp')
    
    # Get possible contacts
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if request.user.role == 'student':
        # Students can message companies and university staff
        contacts = User.objects.filter(
            Q(role='company') | Q(role='university'),
            applications__student=request.user
        ).distinct()
    else:
        # Companies can message their students
        contacts = User.objects.filter(
            role='student',
            applications__company=request.user,
            applications__status='accepted'
        ).distinct()
    
    context = {
        'sent_messages': sent_messages[:10],
        'received_messages': received_messages[:10],
        'contacts': contacts
    }
    
    return render(request, 'recruitment/messaging.html', context)

@login_required
def submit_leave_request(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    application = InternshipApplication.objects.filter(student=request.user, status='accepted').first()
    if not application:
        messages.error(request, 'You need an accepted application to request leave')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        leave_type = request.POST.get('leave_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')
        
        LeaveRequest.objects.create(
            student=request.user,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        
        messages.success(request, 'Leave request submitted successfully!')
        return redirect('leave_requests')
    
    return render(request, 'recruitment/submit_leave_request.html', {'application': application})

@login_required
def leave_requests(request):
    if request.user.role == 'student':
        requests = LeaveRequest.objects.filter(student=request.user).order_by('-start_date')
    elif request.user.role == 'company':
        requests = LeaveRequest.objects.filter(application__company=request.user).order_by('-start_date')
    else:
        return redirect('dashboard')
    
    return render(request, 'recruitment/leave_requests.html', {'requests': requests})

@login_required
def update_leave_status(request, leave_id):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    leave_request = get_object_or_404(LeaveRequest, id=leave_id, application__company=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'approved', 'rejected']:
            leave_request.status = new_status
            leave_request.save()
            
            # Send notification to student
            Message.objects.create(
                sender=request.user,
                receiver=leave_request.student,
                content=f"Your leave request has been {new_status}",
                timestamp=timezone.now()
            )
            
            messages.success(request, f'Leave request {new_status} successfully!')
        else:
            messages.error(request, 'Invalid status')
    
    return redirect('leave_requests')
