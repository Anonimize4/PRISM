from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import CompanyProfile, Mentor, Meeting, CompanyEvaluation, NotificationPreference
from recruitment.models import InternshipApplication, Team, Project, LeaveRequest

@login_required
def company_dashboard(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    try:
        profile = CompanyProfile.objects.get(user=request.user)
    except CompanyProfile.DoesNotExist:
        return redirect('create_company_profile')
    
    applications = InternshipApplication.objects.filter(company=request.user).order_by('-applied_date')
    teams = Team.objects.filter(company=request.user)
    pending_leave_requests = LeaveRequest.objects.filter(
        application__company=request.user, 
        status='pending'
    )
    upcoming_meetings = Meeting.objects.filter(
        company=profile, 
        scheduled_date__gte=timezone.now(),
        status='scheduled'
    )
    
    context = {
        'profile': profile,
        'applications': applications[:5],
        'teams': teams,
        'pending_leave_requests': pending_leave_requests[:3],
        'upcoming_meetings': upcoming_meetings[:3],
        'total_applications': applications.count(),
        'pending_applications': applications.filter(status='pending').count(),
    }
    return render(request, 'company/dashboard.html', context)

@login_required
def create_company_profile(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    try:
        profile = CompanyProfile.objects.get(user=request.user)
        return redirect('company_dashboard')
    except CompanyProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        industry = request.POST.get('industry')
        description = request.POST.get('description')
        website = request.POST.get('website')
        address = request.POST.get('address')
        contact_person = request.POST.get('contact_person')
        contact_email = request.POST.get('contact_email')
        contact_phone = request.POST.get('contact_phone')
        
        CompanyProfile.objects.create(
            user=request.user,
            company_name=company_name,
            industry=industry,
            description=description,
            website=website,
            address=address,
            contact_person=contact_person,
            contact_email=contact_email,
            contact_phone=contact_phone
        )
        
        messages.success(request, 'Company profile created successfully!')
        return redirect('company_dashboard')
    
    return render(request, 'company/create_company_profile.html')

@login_required
def view_company_profile(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    profile = get_object_or_404(CompanyProfile, user=request.user)
    mentors = Mentor.objects.filter(company=profile)
    
    context = {
        'profile': profile,
        'mentors': mentors,
    }
    return render(request, 'company/view_company_profile.html', context)

@login_required
def edit_company_profile(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    profile = get_object_or_404(CompanyProfile, user=request.user)
    
    if request.method == 'POST':
        profile.company_name = request.POST.get('company_name')
        profile.industry = request.POST.get('industry')
        profile.description = request.POST.get('description')
        profile.website = request.POST.get('website')
        profile.address = request.POST.get('address')
        profile.contact_person = request.POST.get('contact_person')
        profile.contact_email = request.POST.get('contact_email')
        profile.contact_phone = request.POST.get('contact_phone')
        profile.save()
        
        messages.success(request, 'Company profile updated successfully!')
        return redirect('view_company_profile')
    
    return render(request, 'company/edit_company_profile.html', {'profile': profile})

@login_required
def manage_mentors(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    profile = get_object_or_404(CompanyProfile, user=request.user)
    mentors = Mentor.objects.filter(company=profile)
    
    if request.method == 'POST':
        user_id = request.POST.get('user')
        department = request.POST.get('department')
        expertise = request.POST.get('expertise')
        years_of_experience = request.POST.get('years_of_experience')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = get_object_or_404(User, id=user_id)
        
        Mentor.objects.create(
            user=user,
            company=profile,
            department=department,
            expertise=expertise,
            years_of_experience=years_of_experience
        )
        
        messages.success(request, 'Mentor added successfully!')
        return redirect('manage_mentors')
    
    # Get available company users who are not already mentors
    from django.contrib.auth import get_user_model
    User = get_user_model()
    available_users = User.objects.filter(role='company').exclude(
        id__in=mentors.values_list('user_id', flat=True)
    )
    
    context = {
        'mentors': mentors,
        'available_users': available_users,
    }
    return render(request, 'company/manage_mentors.html', context)

@login_required
def schedule_meeting(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    profile = get_object_or_404(CompanyProfile, user=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        scheduled_date = request.POST.get('scheduled_date')
        duration = request.POST.get('duration')
        meeting_link = request.POST.get('meeting_link')
        description = request.POST.get('description')
        participant_ids = request.POST.getlist('participants')
        
        meeting = Meeting.objects.create(
            title=title,
            company=profile,
            scheduled_date=scheduled_date,
            duration=duration,
            meeting_link=meeting_link,
            description=description
        )
        
        if participant_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            participants = User.objects.filter(id__in=participant_ids)
            meeting.participants.set(participants)
        
        meeting.save()
        messages.success(request, 'Meeting scheduled successfully!')
        return redirect('meetings')
    
    # Get possible participants (accepted students and company staff)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    participants = User.objects.filter(
        Q(role='student', applications__company=request.user, applications__status='accepted') |
        Q(role='company')
    ).distinct()
    
    return render(request, 'company/schedule_meeting.html', {'participants': participants})

@login_required
def meetings(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    profile = get_object_or_404(CompanyProfile, user=request.user)
    meetings = Meeting.objects.filter(company=profile).order_by('-scheduled_date')
    
    return render(request, 'company/meetings.html', {'meetings': meetings})

@login_required
def meeting_detail(request, meeting_id):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    profile = get_object_or_404(CompanyProfile, user=request.user)
    meeting = get_object_or_404(Meeting, id=meeting_id, company=profile)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['scheduled', 'in_progress', 'completed', 'cancelled']:
            meeting.status = new_status
            meeting.save()
            messages.success(request, f'Meeting status updated to {new_status}')
        else:
            messages.error(request, 'Invalid status')
        return redirect('meeting_detail', meeting_id=meeting_id)
    
    return render(request, 'company/meeting_detail.html', {'meeting': meeting})

@login_required
def student_evaluations(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    evaluations = CompanyEvaluation.objects.filter(
        evaluator__company__user=request.user
    ).order_by('-evaluation_date')
    
    return render(request, 'company/student_evaluations.html', {'evaluations': evaluations})

@login_required
def create_evaluation(request, application_id):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    application = get_object_or_404(InternshipApplication, id=application_id, company=request.user)
    profile = get_object_or_404(CompanyProfile, user=request.user)
    mentor = Mentor.objects.filter(company=profile).first()
    
    if not mentor:
        messages.error(request, 'No mentor available for evaluation')
        return redirect('manage_applications')
    
    if request.method == 'POST':
        performance_rating = request.POST.get('performance_rating')
        technical_skills = request.POST.get('technical_skills')
        communication_skills = request.POST.get('communication_skills')
        teamwork = request.POST.get('teamwork')
        problem_solving = request.POST.get('problem_solving')
        overall_feedback = request.POST.get('overall_feedback')
        
        CompanyEvaluation.objects.create(
            application=application,
            evaluator=mentor,
            performance_rating=performance_rating,
            technical_skills=technical_skills,
            communication_skills=communication_skills,
            teamwork=teamwork,
            problem_solving=problem_solving,
            overall_feedback=overall_feedback
        )
        
        messages.success(request, 'Evaluation submitted successfully!')
        return redirect('student_evaluations')
    
    return render(request, 'company/create_evaluation.html', {
        'application': application,
        'mentor': mentor
    })

@login_required
def notification_settings(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    try:
        preferences = NotificationPreference.objects.get(user=request.user)
    except NotificationPreference.DoesNotExist:
        preferences = NotificationPreference.objects.create(user=request.user)
    
    if request.method == 'POST':
        preferences.email_notifications = request.POST.get('email_notifications') == 'on'
        preferences.sms_notifications = request.POST.get('sms_notifications') == 'on'
        preferences.push_notifications = request.POST.get('push_notifications') == 'on'
        preferences.deadline_reminders = request.POST.get('deadline_reminders') == 'on'
        preferences.meeting_reminders = request.POST.get('meeting_reminders') == 'on'
        preferences.feedback_notifications = request.POST.get('feedback_notifications') == 'on'
        preferences.save()
        
        messages.success(request, 'Notification settings updated successfully!')
        return redirect('notification_settings')
    
    return render(request, 'company/notification_settings.html', {'preferences': preferences})

@login_required
def reports_analytics(request):
    if request.user.role != 'company':
        return redirect('dashboard')
    
    profile = get_object_or_404(CompanyProfile, user=request.user)
    
    # Get analytics data
    total_applications = InternshipApplication.objects.filter(company=request.user).count()
    accepted_applications = InternshipApplication.objects.filter(company=request.user, status='accepted').count()
    rejected_applications = InternshipApplication.objects.filter(company=request.user, status='rejected').count()
    
    total_teams = Team.objects.filter(company=request.user).count()
    total_projects = Project.objects.filter(team__company=request.user).count()
    
    recent_evaluations = CompanyEvaluation.objects.filter(
        evaluator__company=profile
    ).order_by('-evaluation_date')[:10]
    
    context = {
        'total_applications': total_applications,
        'accepted_applications': accepted_applications,
        'rejected_applications': rejected_applications,
        'total_teams': total_teams,
        'total_projects': total_projects,
        'recent_evaluations': recent_evaluations,
    }
    
    return render(request, 'company/reports_analytics.html', context)
