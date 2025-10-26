from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.http import HttpResponse, JsonResponse
from .models import Supervisor, StudentSupervisorAssignment, PerformanceMetric, FinalEvaluation, AttendanceRecord
from recruitment.models import InternshipApplication, Report
from company.models import CompanyEvaluation
from .utils import get_university_analytics, generate_performance_alerts, get_student_performance_summary
import csv
import json

@login_required
def university_dashboard(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    # Get students accepted into internships
    accepted_students = InternshipApplication.objects.filter(
        university=request.user,
        status='accepted'
    ).select_related('student').order_by('-applied_date')
    
    # Get supervisors
    supervisors = Supervisor.objects.all()
    
    # Get recent evaluations
    recent_evaluations = FinalEvaluation.objects.filter(
        supervisor__user=request.user
    ).order_by('-evaluation_date')[:5]
    
    # Get pending supervisor assignments
    pending_assignments = InternshipApplication.objects.filter(
        university=request.user,
        status='accepted',
        student__supervisor_assignments__isnull=True
    )
    
    context = {
        'accepted_students': accepted_students[:5],
        'supervisors': supervisors,
        'recent_evaluations': recent_evaluations,
        'pending_assignments': pending_assignments,
        'total_students': accepted_students.count(),
        'total_supervisors': supervisors.count(),
    }
    return render(request, 'university/dashboard.html', context)

@login_required
def accepted_students(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    students = InternshipApplication.objects.filter(
        university=request.user,
        status='accepted'
    ).select_related('student', 'company')
    
    # Filtering
    company_filter = request.GET.get('company')
    major_filter = request.GET.get('major')
    status_filter = request.GET.get('status')
    
    if company_filter:
        students = students.filter(company__username__icontains=company_filter)
    if major_filter:
        students = students.filter(academic_details__icontains=major_filter)
    
    context = {
        'students': students,
    }
    return render(request, 'university/accepted_students.html', context)

@login_required
def assign_supervisor(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    if request.method == 'POST':
        student_id = request.POST.get('student')
        supervisor_id = request.POST.get('supervisor')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        student = get_object_or_404(User, id=student_id, role='student')
        supervisor = get_object_or_404(Supervisor, id=supervisor_id)
        
        # Check if assignment already exists
        existing_assignment = StudentSupervisorAssignment.objects.filter(
            student=student
        ).first()
        
        if existing_assignment:
            messages.error(request, 'This student already has a supervisor assigned')
        else:
            StudentSupervisorAssignment.objects.create(
                student=student,
                supervisor=supervisor
            )
            messages.success(request, 'Supervisor assigned successfully!')
        
        return redirect('assign_supervisor')
    
    # Get students without supervisors
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students_without_supervisors = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted',
        supervisor_assignments__isnull=True
    ).distinct()
    
    supervisors = Supervisor.objects.all()
    
    context = {
        'students': students_without_supervisors,
        'supervisors': supervisors,
    }
    return render(request, 'university/assign_supervisor.html', context)

@login_required
def supervisor_assignments(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    assignments = StudentSupervisorAssignment.objects.select_related('student', 'supervisor__user')
    
    return render(request, 'university/supervisor_assignments.html', {'assignments': assignments})

@login_required
def student_performance(request, student_id):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    student = get_object_or_404(User, id=student_id, role='student')
    
    # Get performance metrics
    performance_metrics = PerformanceMetric.objects.filter(student=student).order_by('-evaluation_date')
    
    # Get attendance records
    attendance_records = AttendanceRecord.objects.filter(student=student).order_by('-date')
    
    # Get reports
    reports = Report.objects.filter(application__student=student).order_by('-submitted_date')
    
    # Get company evaluations
    company_evaluations = CompanyEvaluation.objects.filter(
        application__student=student
    ).order_by('-evaluation_date')
    
    # Calculate attendance percentage
    total_days = attendance_records.count()
    present_days = attendance_records.filter(status='present').count()
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
    
    context = {
        'student': student,
        'performance_metrics': performance_metrics,
        'attendance_records': attendance_records,
        'reports': reports,
        'company_evaluations': company_evaluations,
        'attendance_percentage': attendance_percentage,
    }
    return render(request, 'university/student_performance.html', context)

@login_required
def performance_overview(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    # Get all students from this university
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students = User.objects.filter(
        role='student',
        applications__university=request.user
    ).distinct()
    
    student_data = []
    for student in students:
        # Get latest performance metrics
        latest_metrics = PerformanceMetric.objects.filter(student=student).order_by('-evaluation_date').first()
        
        # Calculate attendance
        attendance_records = AttendanceRecord.objects.filter(student=student)
        total_days = attendance_records.count()
        present_days = attendance_records.filter(status='present').count()
        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        
        # Get application status
        application = InternshipApplication.objects.filter(student=student).first()
        
        student_data.append({
            'student': student,
            'metrics': latest_metrics,
            'attendance_percentage': attendance_percentage,
            'application': application,
        })
    
    context = {
        'student_data': student_data,
    }
    return render(request, 'university/performance_overview.html', context)

@login_required
def company_evaluations(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    # Get company evaluations for university students
    evaluations = CompanyEvaluation.objects.filter(
        application__university=request.user
    ).select_related('application__student', 'application__company', 'evaluator__user').order_by('-evaluation_date')
    
    return render(request, 'university/company_evaluations.html', {'evaluations': evaluations})

@login_required
def final_evaluations(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    evaluations = FinalEvaluation.objects.select_related('student', 'supervisor__user').order_by('-evaluation_date')
    
    return render(request, 'university/final_evaluations.html', {'evaluations': evaluations})

@login_required
def create_final_evaluation(request, student_id):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    student = get_object_or_404(User, id=student_id, role='student')
    
    # Get student's supervisor
    assignment = StudentSupervisorAssignment.objects.filter(student=student).first()
    if not assignment:
        messages.error(request, 'No supervisor assigned to this student')
        return redirect('accepted_students')
    
    if request.method == 'POST':
        final_feedback = request.POST.get('final_feedback')
        grade = request.POST.get('grade')
        
        # Check if evaluation already exists
        existing_evaluation = FinalEvaluation.objects.filter(
            student=student,
            supervisor=assignment.supervisor
        ).first()
        
        if existing_evaluation:
            messages.error(request, 'Final evaluation already exists for this student')
        else:
            FinalEvaluation.objects.create(
                student=student,
                supervisor=assignment.supervisor,
                final_feedback=final_feedback,
                grade=grade,
                evaluation_date=timezone.now()
            )
            messages.success(request, 'Final evaluation created successfully!')
        
        return redirect('final_evaluations')
    
    context = {
        'student': student,
        'supervisor': assignment.supervisor,
    }
    return render(request, 'university/create_final_evaluation.html', context)

@login_required
def analytics_dashboard(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    # Get comprehensive analytics using utility function
    analytics_data = get_university_analytics(request.user)
    
    # Get performance alerts
    alerts = generate_performance_alerts(request.user)
    
    context = {
        'analytics': analytics_data,
        'alerts': alerts[:5],  # Show top 5 alerts
        'alerts_count': len(alerts),
    }
    return render(request, 'university/analytics_dashboard.html', context)

@login_required
def bulk_supervisor_assignment(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    if request.method == 'POST':
        assignments = request.POST.getlist('assignments')
        success_count = 0
        
        for assignment in assignments:
            student_id, supervisor_id = assignment.split('-')
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                student = User.objects.get(id=student_id, role='student')
                supervisor = Supervisor.objects.get(id=supervisor_id)
                
                if not StudentSupervisorAssignment.objects.filter(student=student).exists():
                    StudentSupervisorAssignment.objects.create(
                        student=student,
                        supervisor=supervisor
                    )
                    success_count += 1
            except (User.DoesNotExist, Supervisor.DoesNotExist):
                continue
        
        messages.success(request, f'Successfully assigned {success_count} supervisors')
        return redirect('supervisor_assignments')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students_without_supervisors = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted',
        supervisor_assignments__isnull=True
    ).distinct()
    
    supervisors = Supervisor.objects.all()
    
    context = {
        'students': students_without_supervisors,
        'supervisors': supervisors,
    }
    return render(request, 'university/bulk_supervisor_assignment.html', context)

@login_required
def attendance_management(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    if request.method == 'POST':
        student_id = request.POST.get('student')
        date = request.POST.get('date')
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        student = get_object_or_404(User, id=student_id, role='student')
        
        attendance, created = AttendanceRecord.objects.get_or_create(
            student=student,
            date=date,
            defaults={'status': status, 'notes': notes}
        )
        
        if not created:
            attendance.status = status
            attendance.notes = notes
            attendance.save()
        
        messages.success(request, 'Attendance record updated successfully')
        return redirect('attendance_management')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted'
    ).distinct()
    
    # Get recent attendance records
    recent_records = AttendanceRecord.objects.filter(
        student__in=students
    ).select_related('student').order_by('-date')[:20]
    
    context = {
        'students': students,
        'recent_records': recent_records,
    }
    return render(request, 'university/attendance_management.html', context)

@login_required
def performance_alerts(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    alerts = []
    students = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted'
    ).distinct()
    
    for student in students:
        # Low attendance alert
        attendance_records = AttendanceRecord.objects.filter(student=student)
        if attendance_records.exists():
            total_days = attendance_records.count()
            present_days = attendance_records.filter(status='present').count()
            attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
            
            if attendance_percentage < 75:
                alerts.append({
                    'type': 'attendance',
                    'student': student,
                    'message': f'Low attendance: {attendance_percentage:.1f}%',
                    'severity': 'high' if attendance_percentage < 50 else 'medium'
                })
        
        # Missing reports alert
        reports_count = Report.objects.filter(application__student=student).count()
        if reports_count == 0:
            alerts.append({
                'type': 'reports',
                'student': student,
                'message': 'No reports submitted',
                'severity': 'medium'
            })
        
        # No supervisor assigned
        if not StudentSupervisorAssignment.objects.filter(student=student).exists():
            alerts.append({
                'type': 'supervisor',
                'student': student,
                'message': 'No supervisor assigned',
                'severity': 'high'
            })
    
    context = {
        'alerts': alerts,
    }
    return render(request, 'university/performance_alerts.html', context)

@login_required
def export_student_data(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student Name', 'Email', 'Company', 'Supervisor', 
        'Attendance %', 'Latest Grade', 'Reports Count', 'Status'
    ])
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted'
    ).distinct()
    
    for student in students:
        application = InternshipApplication.objects.filter(student=student).first()
        assignment = StudentSupervisorAssignment.objects.filter(student=student).first()
        
        # Calculate attendance
        attendance_records = AttendanceRecord.objects.filter(student=student)
        total_days = attendance_records.count()
        present_days = attendance_records.filter(status='present').count()
        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        
        # Get latest evaluation and reports count
        latest_evaluation = FinalEvaluation.objects.filter(student=student).order_by('-evaluation_date').first()
        reports_count = Report.objects.filter(application__student=student).count()
        
        writer.writerow([
            student.get_full_name(),
            student.email,
            application.company.username if application else 'N/A',
            assignment.supervisor.user.get_full_name() if assignment else 'Unassigned',
            f'{attendance_percentage:.1f}%',
            latest_evaluation.grade if latest_evaluation else 'N/A',
            reports_count,
            'Active' if student.is_active else 'Inactive'
        ])
    
    return response

@login_required
def student_reports(request, student_id):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    student = get_object_or_404(User, id=student_id, role='student')
    
    reports = Report.objects.filter(
        application__student=student
    ).order_by('-week')
    
    context = {
        'student': student,
        'reports': reports,
    }
    return render(request, 'university/student_reports.html', context)

@login_required
def supervisor_workload(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    supervisors = Supervisor.objects.annotate(
        student_count=Count('student_assignments')
    ).order_by('-student_count')
    
    context = {
        'supervisors': supervisors,
    }
    return render(request, 'university/supervisor_workload.html', context)
        existing_evaluation = FinalEvaluation.objects.filter(
            student=student,
            supervisor=assignment.supervisor
        ).first()
        
        if existing_evaluation:
            messages.error(request, 'Final evaluation already exists for this student')
        else:
            FinalEvaluation.objects.create(
                student=student,
                supervisor=assignment.supervisor,
                final_feedback=final_feedback,
                grade=grade,
                evaluation_date=timezone.now()
            )
            messages.success(request, 'Final evaluation created successfully!')
        
        return redirect('final_evaluations')
    
    context = {
        'student': student,
        'supervisor': assignment.supervisor,
    }
    return render(request, 'university/create_final_evaluation.html', context)

@login_required
def export_student_data(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Email', 'Company', 'Supervisor', 'Attendance %', 'Latest Grade'])
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted'
    ).distinct()
    
    for student in students:
        application = InternshipApplication.objects.filter(student=student).first()
        assignment = StudentSupervisorAssignment.objects.filter(student=student).first()
        
        # Calculate attendance
        attendance_records = AttendanceRecord.objects.filter(student=student)
        total_days = attendance_records.count()
        present_days = attendance_records.filter(status='present').count()
        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        
        # Get latest evaluation
        latest_evaluation = FinalEvaluation.objects.filter(student=student).order_by('-evaluation_date').first()
        
        writer.writerow([
            student.get_full_name(),
            student.email,
            application.company.username if application else 'N/A',
            assignment.supervisor.user.get_full_name() if assignment else 'N/A',
            f'{attendance_percentage:.1f}%',
            latest_evaluation.grade if latest_evaluation else 'N/A'
        ])
    
    return response
        existing_evaluation = FinalEvaluation.objects.filter(
            student=student,
            supervisor=assignment.supervisor
        ).first()
        
        if existing_evaluation:
            messages.error(request, 'Final evaluation already exists for this student')
        else:
            FinalEvaluation.objects.create(
                student=student,
                supervisor=assignment.supervisor,
                final_feedback=final_feedback,
                grade=grade,
                evaluation_date=timezone.now()
            )
            messages.success(request, 'Final evaluation created successfully!')
        
        return redirect('final_evaluations')
    
    context = {
        'student': student,
        'supervisor': assignment.supervisor,
    }
    return render(request, 'university/create_final_evaluation.html', context)

@login_required
def export_student_data(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Email', 'Company', 'Supervisor', 'Attendance %', 'Latest Grade'])
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted'
    ).distinct()
    
    for student in students:
        application = InternshipApplication.objects.filter(student=student).first()
        assignment = StudentSupervisorAssignment.objects.filter(student=student).first()
        
        # Calculate attendance
        attendance_records = AttendanceRecord.objects.filter(student=student)
        total_days = attendance_records.count()
        present_days = attendance_records.filter(status='present').count()
        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        
        # Get latest evaluation
        latest_evaluation = FinalEvaluation.objects.filter(student=student).order_by('-evaluation_date').first()
        
        writer.writerow([
            student.get_full_name(),
            student.email,
            application.company.username if application else 'N/A',
            assignment.supervisor.user.get_full_name() if assignment else 'N/A',
            f'{attendance_percentage:.1f}%',
            latest_evaluation.grade if latest_evaluation else 'N/A'
        ])
    
    return response
        existing_evaluation = FinalEvaluation.objects.filter(
            student=student,
            supervisor=assignment.supervisor
        ).first()
        
        if existing_evaluation:
            messages.error(request, 'Final evaluation already exists for this student')
        else:
            FinalEvaluation.objects.create(
                student=student,
                supervisor=assignment.supervisor,
                final_feedback=final_feedback,
                grade=grade,
                evaluation_date=timezone.now()
            )
            messages.success(request, 'Final evaluation created successfully!')
        
        return redirect('final_evaluations')
    
    context = {
        'student': student,
        'supervisor': assignment.supervisor,
    }
    return render(request, 'university/create_final_evaluation.html', context)

@login_required
def export_student_data(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Email', 'Company', 'Supervisor', 'Attendance %', 'Latest Grade'])
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted'
    ).distinct()
    
    for student in students:
        application = InternshipApplication.objects.filter(student=student).first()
        assignment = StudentSupervisorAssignment.objects.filter(student=student).first()
        
        # Calculate attendance
        attendance_records = AttendanceRecord.objects.filter(student=student)
        total_days = attendance_records.count()
        present_days = attendance_records.filter(status='present').count()
        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        
        # Get latest evaluation
        latest_evaluation = FinalEvaluation.objects.filter(student=student).order_by('-evaluation_date').first()
        
        writer.writerow([
            student.get_full_name(),
            student.email,
            application.company.username if application else 'N/A',
            assignment.supervisor.user.get_full_name() if assignment else 'N/A',
            f'{attendance_percentage:.1f}%',
            latest_evaluation.grade if latest_evaluation else 'N/A'
        ])
    
    return response
        existing_evaluation = FinalEvaluation.objects.filter(
            student=student,
            supervisor=assignment.supervisor
        ).first()
        
        if existing_evaluation:
            messages.error(request, 'Final evaluation already exists for this student')
        else:
            FinalEvaluation.objects.create(
                student=student,
                supervisor=assignment.supervisor,
                final_feedback=final_feedback,
                grade=grade,
                evaluation_date=timezone.now()
            )
            messages.success(request, 'Final evaluation created successfully!')
        
        return redirect('final_evaluations')
    
    context = {
        'student': student,
        'supervisor': assignment.supervisor,
    }
    return render(request, 'university/create_final_evaluation.html', context)

@login_required
def export_student_data(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Email', 'Company', 'Supervisor', 'Attendance %', 'Latest Grade'])
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted'
    ).distinct()
    
    for student in students:
        application = InternshipApplication.objects.filter(student=student).first()
        assignment = StudentSupervisorAssignment.objects.filter(student=student).first()
        
        # Calculate attendance
        attendance_records = AttendanceRecord.objects.filter(student=student)
        total_days = attendance_records.count()
        present_days = attendance_records.filter(status='present').count()
        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        
        # Get latest evaluation
        latest_evaluation = FinalEvaluation.objects.filter(student=student).order_by('-evaluation_date').first()
        
        writer.writerow([
            student.get_full_name(),
            student.email,
            application.company.username if application else 'N/A',
            assignment.supervisor.user.get_full_name() if assignment else 'N/A',
            f'{attendance_percentage:.1f}%',
            latest_evaluation.grade if latest_evaluation else 'N/A'
        ])
    
    return response
        existing_evaluation = FinalEvaluation.objects.filter(student=student).first()
        if existing_evaluation:
            existing_evaluation.final_feedback = final_feedback
            existing_evaluation.grade = grade
            existing_evaluation.save()
            messages.success(request, 'Final evaluation updated successfully!')
        else:
            FinalEvaluation.objects.create(
                student=student,
                supervisor=assignment.supervisor,
                final_feedback=final_feedback,
                grade=grade
            )
            messages.success(request, 'Final evaluation submitted successfully!')
        
        return redirect('final_evaluations')
    
    return render(request, 'university/create_final_evaluation.html', {
        'student': student,
        'supervisor': assignment.supervisor
    })

@login_required
def export_performance_data(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="performance_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Student ID', 'Company', 'Attendance %', 
                     'Report Quality Score', 'Communication Score', 'Technical Skills Score', 
                     'Final Grade', 'Evaluation Date'])
    
    # Get all students with performance data
    from django.contrib.auth import get_user_model
    User = get_user_model()
    students = User.objects.filter(role='student', applications__university=request.user).distinct()
    
    for student in students:
        # Get latest performance metrics
        metrics = PerformanceMetric.objects.filter(student=student).order_by('-evaluation_date').first()
        final_eval = FinalEvaluation.objects.filter(student=student).first()
        application = InternshipApplication.objects.filter(student=student).first()
        
        if metrics:
            writer.writerow([
                student.get_full_name() or student.username,
                student.username,
                application.company.username if application else 'N/A',
                f"{metrics.attendance_percentage}%",
                metrics.report_quality_score,
                metrics.communication_score,
                metrics.technical_skills_score,
                final_eval.grade if final_eval else 'N/A',
                metrics.evaluation_date.strftime('%Y-%m-%d') if metrics else 'N/A'
            ])
    
    return response

@login_required
def attendance_calendar(request, student_id=None):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    if student_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        student = get_object_or_404(User, id=student_id, role='student')
        attendance_records = AttendanceRecord.objects.filter(student=student).order_by('-date')
    else:
        # Show all university students
        attendance_records = AttendanceRecord.objects.filter(
            student__applications__university=request.user
        ).select_related('student').order_by('-date')
    
    context = {
        'attendance_records': attendance_records,
        'selected_student': student_id,
    }
    return render(request, 'university/attendance_calendar.html', context)

@login_required
def manage_supervisors(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    if request.method == 'POST':
        user_id = request.POST.get('user')
        department = request.POST.get('department')
        title = request.POST.get('title')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = get_object_or_404(User, id=user_id, role='university')
        
        Supervisor.objects.create(
            user=user,
            department=department,
            title=title
        )
        
        messages.success(request, 'Supervisor created successfully!')
        return redirect('manage_supervisors')
    
    supervisors = Supervisor.objects.select_related('user').all()
    
    # Get available university users who are not already supervisors
    from django.contrib.auth import get_user_model
    User = get_user_model()
    available_users = User.objects.filter(role='university').exclude(
        id__in=supervisors.values_list('user_id', flat=True)
    )
    
    context = {
        'supervisors': supervisors,
        'available_users': available_users,
    }
    return render(request, 'university/manage_supervisors.html', context)

@login_required
def analytics_dashboard(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    # Get analytics data
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    total_students = User.objects.filter(role='student', applications__university=request.user).distinct().count()
    total_supervisors = Supervisor.objects.count()
    
    # Application statistics
    total_applications = InternshipApplication.objects.filter(university=request.user).count()
    accepted_applications = InternshipApplication.objects.filter(university=request.user, status='accepted').count()
    rejected_applications = InternshipApplication.objects.filter(university=request.user, status='rejected').count()
    
    # Performance statistics
    avg_attendance = PerformanceMetric.objects.aggregate(Avg('attendance_percentage'))['attendance_percentage__avg'] or 0
    avg_report_quality = PerformanceMetric.objects.aggregate(Avg('report_quality_score'))['report_quality_score__avg'] or 0
    
    # Grade distribution
    grade_distribution = FinalEvaluation.objects.values('grade').annotate(count=Count('grade')).order_by('-count')
    
    context = {
        'total_students': total_students,
        'total_supervisors': total_supervisors,
        'total_applications': total_applications,
        'accepted_applications': accepted_applications,
        'rejected_applications': rejected_applications,
        'avg_attendance': avg_attendance,
        'avg_report_quality': avg_report_quality,
        'grade_distribution': grade_distribution,
    }
    
    return render(request, 'university/analytics_dashboard.html', context)
@login_required
def attendance_calendar(request, student_id=None):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if student_id:
        student = get_object_or_404(User, id=student_id, role='student')
        attendance_records = AttendanceRecord.objects.filter(student=student).order_by('-date')
        context = {'student': student, 'attendance_records': attendance_records}
    else:
        students = User.objects.filter(
            role='student',
            applications__university=request.user,
            applications__status='accepted'
        ).distinct()
        context = {'students': students}
    
    return render(request, 'university/attendance_calendar.html', context)

@login_required
def manage_supervisors(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            username = request.POST.get('username')
            email = request.POST.get('email')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            password = request.POST.get('password')
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    role='supervisor'
                )
                
                Supervisor.objects.create(
                    user=user,
                    department=request.POST.get('department', ''),
                    specialization=request.POST.get('specialization', '')
                )
                
                messages.success(request, 'Supervisor created successfully!')
    
    supervisors = Supervisor.objects.all()
    return render(request, 'university/manage_supervisors.html', {'supervisors': supervisors})

@login_required
def analytics_dashboard(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    total_students = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted'
    ).distinct().count()
    
    evaluations = FinalEvaluation.objects.filter(
        student__applications__university=request.user
    )
    
    grade_distribution = {}
    for evaluation in evaluations:
        grade = evaluation.grade
        grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
    
    attendance_stats = []
    students = User.objects.filter(
        role='student',
        applications__university=request.user,
        applications__status='accepted'
    ).distinct()
    
    for student in students:
        records = AttendanceRecord.objects.filter(student=student)
        total = records.count()
        present = records.filter(status='present').count()
        percentage = (present / total * 100) if total > 0 else 0
        attendance_stats.append({
            'student': student,
            'percentage': percentage
        })
    
    context = {
        'total_students': total_students,
        'grade_distribution': grade_distribution,
        'attendance_stats': attendance_stats,
    }
    return render(request, 'university/analytics_dashboard.html', context)

@login_required
def export_performance_data(request):
    if request.user.role != 'university':
        return redirect('dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="performance_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Company', 'Supervisor', 'Grade', 'Attendance %', 'Evaluation Date'])
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    evaluations = FinalEvaluation.objects.filter(
        student__applications__university=request.user
    ).select_related('student', 'supervisor__user')
    
    for evaluation in evaluations:
        records = AttendanceRecord.objects.filter(student=evaluation.student)
        total = records.count()
        present = records.filter(status='present').count()
        attendance_percentage = (present / total * 100) if total > 0 else 0
        
        application = InternshipApplication.objects.filter(student=evaluation.student).first()
        
        writer.writerow([
            evaluation.student.get_full_name(),
            application.company.username if application else 'N/A',
            evaluation.supervisor.user.get_full_name(),
            evaluation.grade,
            f'{attendance_percentage:.1f}%',
            evaluation.evaluation_date.strftime('%Y-%m-%d')
        ])
    
    return response