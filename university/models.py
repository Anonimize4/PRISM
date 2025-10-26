from django.db import models
from django.conf import settings

class Supervisor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    title = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class StudentSupervisorAssignment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supervisor_assignments')
    supervisor = models.ForeignKey(Supervisor, on_delete=models.CASCADE, related_name='student_assignments')
    assigned_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.supervisor.user.username}"

class PerformanceMetric(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='performance_metrics')
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    report_quality_score = models.DecimalField(max_digits=5, decimal_places=2)
    communication_score = models.DecimalField(max_digits=5, decimal_places=2)
    technical_skills_score = models.DecimalField(max_digits=5, decimal_places=2)
    evaluation_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Performance for {self.student.username} on {self.evaluation_date}"

class FinalEvaluation(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='final_evaluations')
    supervisor = models.ForeignKey(Supervisor, on_delete=models.CASCADE, related_name='final_evaluations')
    final_feedback = models.TextField()
    grade = models.CharField(max_length=2, choices=[
        ('A+', 'A+'), ('A', 'A'), ('A-', 'A-'),
        ('B+', 'B+'), ('B', 'B'), ('B-', 'B-'),
        ('C+', 'C+'), ('C', 'C'), ('C-', 'C-'),
        ('D', 'D'), ('F', 'F')
    ])
    evaluation_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Final Evaluation for {self.student.username} - Grade: {self.grade}"

class AttendanceRecord(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused')
    ])
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.student.username} - {self.date} - {self.status}"
