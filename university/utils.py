from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import AttendanceRecord, PerformanceMetric, FinalEvaluation
from recruitment.models import Report, InternshipApplication
from company.models import CompanyEvaluation

def calculate_student_attendance(student, days=30):
    """Calculate attendance percentage for a student"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    records = AttendanceRecord.objects.filter(
        student=student,
        date__range=[start_date, end_date]
    )
    
    total_days = records.count()
    present_days = records.filter(status='present').count()
    
    return (present_days / total_days * 100) if total_days > 0 else 0

def get_student_performance_summary(student):
    """Get comprehensive performance summary for a student"""
    # Attendance
    attendance_percentage = calculate_student_attendance(student)
    
    # Latest performance metrics
    latest_metrics = PerformanceMetric.objects.filter(
        student=student
    ).order_by('-evaluation_date').first()
    
    # Reports count
    reports_count = Report.objects.filter(
        application__student=student
    ).count()
    
    # Company evaluations
    company_eval = CompanyEvaluation.objects.filter(
        application__student=student
    ).order_by('-evaluation_date').first()
    
    # Final evaluation
    final_eval = FinalEvaluation.objects.filter(
        student=student
    ).order_by('-evaluation_date').first()
    
    return {
        'attendance_percentage': attendance_percentage,
        'latest_metrics': latest_metrics,
        'reports_count': reports_count,
        'company_evaluation': company_eval,
        'final_evaluation': final_eval,
        'performance_score': calculate_overall_performance_score(
            attendance_percentage, latest_metrics, company_eval
        )
    }

def calculate_overall_performance_score(attendance, metrics, company_eval):
    """Calculate overall performance score (0-100)"""
    score = 0
    weight_sum = 0
    
    # Attendance (30% weight)
    if attendance is not None:
        score += attendance * 0.3
        weight_sum += 0.3
    
    # Performance metrics (40% weight)
    if metrics:
        avg_score = (
            float(metrics.report_quality_score) +
            float(metrics.communication_score) +
            float(metrics.technical_skills_score)
        ) / 3
        score += avg_score * 0.4
        weight_sum += 0.4
    
    # Company evaluation (30% weight)
    if company_eval:
        score += float(company_eval.performance_rating) * 10 * 0.3  # Assuming rating is 0-10
        weight_sum += 0.3
    
    return score / weight_sum if weight_sum > 0 else 0

def get_university_analytics(university_user):
    """Get comprehensive analytics for university dashboard"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    students = User.objects.filter(
        role='student',
        applications__university=university_user,
        applications__status='accepted'
    ).distinct()
    
    # Grade distribution
    grade_distribution = FinalEvaluation.objects.filter(
        student__in=students
    ).values('grade').annotate(count=Count('grade'))
    
    # Attendance statistics
    low_attendance_count = 0
    for student in students:
        if calculate_student_attendance(student) < 75:
            low_attendance_count += 1
    
    # Company performance
    company_stats = InternshipApplication.objects.filter(
        university=university_user,
        status='accepted'
    ).values('company__username').annotate(
        student_count=Count('student'),
        avg_performance=Avg('company_evaluations__performance_rating')
    )
    
    # Reports submission rate
    total_expected_reports = students.count() * 12  # Assuming 12 weeks
    actual_reports = Report.objects.filter(
        application__student__in=students
    ).count()
    
    report_submission_rate = (actual_reports / total_expected_reports * 100) if total_expected_reports > 0 else 0
    
    return {
        'total_students': students.count(),
        'grade_distribution': list(grade_distribution),
        'low_attendance_count': low_attendance_count,
        'company_stats': list(company_stats),
        'report_submission_rate': report_submission_rate,
        'students_without_supervisors': students.filter(
            supervisor_assignments__isnull=True
        ).count()
    }

def generate_performance_alerts(university_user):
    """Generate performance alerts for university dashboard"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    alerts = []
    students = User.objects.filter(
        role='student',
        applications__university=university_user,
        applications__status='accepted'
    ).distinct()
    
    for student in students:
        # Check attendance
        attendance = calculate_student_attendance(student)
        if attendance < 50:
            alerts.append({
                'type': 'critical_attendance',
                'student': student,
                'message': f'Critical: Attendance {attendance:.1f}%',
                'severity': 'critical'
            })
        elif attendance < 75:
            alerts.append({
                'type': 'low_attendance',
                'student': student,
                'message': f'Low attendance: {attendance:.1f}%',
                'severity': 'warning'
            })
        
        # Check missing reports
        expected_reports = 12  # Assuming 12 weeks
        actual_reports = Report.objects.filter(
            application__student=student
        ).count()
        
        if actual_reports < expected_reports * 0.5:
            alerts.append({
                'type': 'missing_reports',
                'student': student,
                'message': f'Missing reports: {actual_reports}/{expected_reports}',
                'severity': 'warning'
            })
        
        # Check supervisor assignment
        from .models import StudentSupervisorAssignment
        if not StudentSupervisorAssignment.objects.filter(student=student).exists():
            alerts.append({
                'type': 'no_supervisor',
                'student': student,
                'message': 'No supervisor assigned',
                'severity': 'critical'
            })
    
    return alerts