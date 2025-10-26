from django.db import models
from django.conf import settings

class InternshipApplication(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    company = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_applications')
    university = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='university_applications')
    personal_info = models.TextField()
    academic_details = models.TextField()
    preferences = models.TextField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending')
    applied_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.company.username}"

class Report(models.Model):
    application = models.ForeignKey(InternshipApplication, on_delete=models.CASCADE, related_name='reports')
    week = models.IntegerField()
    progress = models.TextField()
    challenges = models.TextField()
    achievements = models.TextField()
    submitted_date = models.DateTimeField(auto_now_add=True)
    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Report for {self.application} - Week {self.week}"

class Team(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='teams')
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='mentored_teams')

    def __str__(self):
        return self.name

class Project(models.Model):
    title = models.CharField(max_length=200)
    objectives = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='projects')

    def __str__(self):
        return self.title

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"

class LeaveRequest(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=[('sick', 'Sick'), ('personal', 'Personal'), ('emergency', 'Emergency')])
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')

    def __str__(self):
        return f"{self.student.username} - {self.leave_type}"
