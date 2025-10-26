from django.db import models
from django.conf import settings

class CompanyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100)
    description = models.TextField()
    website = models.URLField(blank=True, null=True)
    address = models.TextField()
    contact_person = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)

    def __str__(self):
        return self.company_name

class Mentor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='mentors')
    department = models.CharField(max_length=100)
    expertise = models.CharField(max_length=200)
    years_of_experience = models.IntegerField()

    def __str__(self):
        return f"{self.user.username} - {self.company.company_name}"

class Meeting(models.Model):
    title = models.CharField(max_length=200)
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='meetings')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='meetings')
    scheduled_date = models.DateTimeField()
    duration = models.IntegerField(help_text="Duration in minutes")
    meeting_link = models.URLField(blank=True, null=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='scheduled')

    def __str__(self):
        return f"{self.title} - {self.scheduled_date}"

class CompanyEvaluation(models.Model):
    application = models.ForeignKey('recruitment.InternshipApplication', on_delete=models.CASCADE, related_name='company_evaluations')
    evaluator = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='evaluations')
    performance_rating = models.DecimalField(max_digits=3, decimal_places=2)
    technical_skills = models.TextField()
    communication_skills = models.TextField()
    teamwork = models.TextField()
    problem_solving = models.TextField()
    overall_feedback = models.TextField()
    evaluation_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Evaluation for {self.application.student.username} by {self.evaluator.user.username}"

class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    deadline_reminders = models.BooleanField(default=True)
    meeting_reminders = models.BooleanField(default=True)
    feedback_notifications = models.BooleanField(default=True)

    def __str__(self):
        return f"Notification preferences for {self.user.username}"
