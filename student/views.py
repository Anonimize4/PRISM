from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import StudentProfile, AcademicInformation, InternshipPreference, StudentNotification, Document
from recruitment.models import InternshipApplication, Report, LeaveRequest

@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    try:
        profile = StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        return redirect('create_profile')
    
    applications = InternshipApplication.objects.filter(student=request.user).order_by('-applied_date')
    pending_reports = Report.objects.filter(application__student=request.user, feedback__isnull=True)
    notifications = StudentNotification.objects.filter(student=profile, is_read=False).order_by('-created_at')
    upcoming_deadlines = LeaveRequest.objects.filter(student=request.user, start_date__gte=timezone.now().date())
    
    context = {
        'profile': profile,
        'applications': applications[:5],
        'pending_reports': pending_reports[:3],
        'notifications': notifications[:5],
        'upcoming_deadlines': upcoming_deadlines[:3],
        'unread_count': notifications.count(),
    }
    return render(request, 'student/dashboard.html', context)

@login_required
def create_profile(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    try:
        profile = StudentProfile.objects.get(user=request.user)
        return redirect('student_dashboard')
    except StudentProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        phone_number = request.POST.get('phone_number')
        date_of_birth = request.POST.get('date_of_birth')
        address = request.POST.get('address')
        emergency_contact_name = request.POST.get('emergency_contact_name')
        emergency_contact_phone = request.POST.get('emergency_contact_phone')
        emergency_contact_relationship = request.POST.get('emergency_contact_relationship')
        
        profile = StudentProfile.objects.create(
            user=request.user,
            student_id=student_id,
            phone_number=phone_number,
            date_of_birth=date_of_birth,
            address=address,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone,
            emergency_contact_relationship=emergency_contact_relationship
        )
        
        messages.success(request, 'Profile created successfully!')
        return redirect('create_academic_info')
    
    return render(request, 'student/create_profile.html')

@login_required
def create_academic_info(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    try:
        profile = StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        return redirect('create_profile')
    
    try:
        academic_info = AcademicInformation.objects.get(student=profile)
        return redirect('student_dashboard')
    except AcademicInformation.DoesNotExist:
        pass
    
    if request.method == 'POST':
        university = request.POST.get('university')
        major = request.POST.get('major')
        year_of_study = request.POST.get('year_of_study')
        gpa = request.POST.get('gpa')
        expected_graduation = request.POST.get('expected_graduation')
        skills = request.POST.get('skills')
        certifications = request.POST.get('certifications')
        
        AcademicInformation.objects.create(
            student=profile,
            university=university,
            major=major,
            year_of_study=year_of_study,
            gpa=gpa,
            expected_graduation=expected_graduation,
            skills=skills,
            certifications=certifications
        )
        
        messages.success(request, 'Academic information saved successfully!')
        return redirect('student_dashboard')
    
    return render(request, 'student/create_academic_info.html')

@login_required
def view_profile(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    try:
        academic_info = AcademicInformation.objects.get(student=profile)
    except AcademicInformation.DoesNotExist:
        academic_info = None
    
    context = {
        'profile': profile,
        'academic_info': academic_info,
    }
    return render(request, 'student/view_profile.html', context)

@login_required
def edit_profile(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    if request.method == 'POST':
        profile.phone_number = request.POST.get('phone_number')
        profile.address = request.POST.get('address')
        profile.emergency_contact_name = request.POST.get('emergency_contact_name')
        profile.emergency_contact_phone = request.POST.get('emergency_contact_phone')
        profile.emergency_contact_relationship = request.POST.get('emergency_contact_relationship')
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('view_profile')
    
    return render(request, 'student/edit_profile.html', {'profile': profile})

@login_required
def edit_academic_info(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    academic_info = get_object_or_404(AcademicInformation, student=profile)
    
    if request.method == 'POST':
        academic_info.university = request.POST.get('university')
        academic_info.major = request.POST.get('major')
        academic_info.year_of_study = request.POST.get('year_of_study')
        academic_info.gpa = request.POST.get('gpa')
        academic_info.expected_graduation = request.POST.get('expected_graduation')
        academic_info.skills = request.POST.get('skills')
        academic_info.certifications = request.POST.get('certifications')
        academic_info.save()
        
        messages.success(request, 'Academic information updated successfully!')
        return redirect('view_profile')
    
    return render(request, 'student/edit_academic_info.html', {'academic_info': academic_info})

@login_required
def internship_preferences(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    try:
        preferences = InternshipPreference.objects.get(student=profile)
    except InternshipPreference.DoesNotExist:
        preferences = None
    
    if request.method == 'POST':
        preferred_companies = request.POST.get('preferred_companies')
        preferred_industries = request.POST.get('preferred_industries')
        preferred_start_date = request.POST.get('preferred_start_date')
        duration_weeks = request.POST.get('duration_weeks')
        work_mode = request.POST.get('work_mode')
        
        if preferences:
            preferences.preferred_companies = preferred_companies
            preferences.preferred_industries = preferred_industries
            preferences.preferred_start_date = preferred_start_date
            preferences.duration_weeks = duration_weeks
            preferences.work_mode = work_mode
            preferences.save()
        else:
            InternshipPreference.objects.create(
                student=profile,
                preferred_companies=preferred_companies,
                preferred_industries=preferred_industries,
                preferred_start_date=preferred_start_date,
                duration_weeks=duration_weeks,
                work_mode=work_mode
            )
        
        messages.success(request, 'Internship preferences saved successfully!')
        return redirect('student_dashboard')
    
    return render(request, 'student/internship_preferences.html', {'preferences': preferences})

@login_required
def notifications(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    notifications = StudentNotification.objects.filter(student=profile).order_by('-created_at')
    
    # Mark all as read
    notifications.update(is_read=True)
    
    return render(request, 'student/notifications.html', {'notifications': notifications})

@login_required
def documents(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    documents = Document.objects.filter(student=profile).order_by('-uploaded_at')
    
    if request.method == 'POST':
        document_type = request.POST.get('document_type')
        description = request.POST.get('description')
        file = request.FILES.get('file')
        
        if file:
            Document.objects.create(
                student=profile,
                document_type=document_type,
                file=file,
                description=description
            )
            messages.success(request, 'Document uploaded successfully!')
            return redirect('documents')
        else:
            messages.error(request, 'Please select a file to upload.')
    
    return render(request, 'student/documents.html', {'documents': documents})

@login_required
def delete_document(request, document_id):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    document = get_object_or_404(Document, id=document_id, student=profile)
    
    if request.method == 'POST':
        document.file.delete()
        document.delete()
        messages.success(request, 'Document deleted successfully!')
        return redirect('documents')
    
    return render(request, 'student/delete_document.html', {'document': document})

@login_required
def saved_applications(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    # This would need to be implemented in models
    # saved_apps = SavedApplication.objects.filter(student=profile)
    
    return render(request, 'student/saved_applications.html')  # , {'saved_apps': saved_apps})
