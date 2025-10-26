from django.db import models
from django.conf import settings

class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    address = models.TextField()
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=20)
    emergency_contact_relationship = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.user.username} - {self.student_id}"

class AcademicInformation(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='academic_info')
    university = models.CharField(max_length=200)
    major = models.CharField(max_length=100)
    year_of_study = models.IntegerField(choices=[
        (1, 'First Year'),
        (2, 'Second Year'),
        (3, 'Third Year'),
        (4, 'Fourth Year'),
        (5, 'Fifth Year or Higher')
    ])
    gpa = models.DecimalField(max_digits=3, decimal_places=2)
    expected_graduation = models.DateField()
    skills = models.TextField(help_text="List of technical and soft skills")
    certifications = models.TextField(blank=True, null=True, help_text="Relevant certifications")

    def __str__(self):
        return f"Academic info for {self.student.user.username}"

class InternshipPreference(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='preferences')
    preferred_companies = models.TextField(help_text="Comma-separated list of preferred companies")
    preferred_industries = models.TextField(help_text="Comma-separated list of preferred industries")
    preferred_start_date = models.DateField()
    duration_weeks = models.IntegerField(help_text="Preferred internship duration in weeks")
    work_mode = models.CharField(max_length=20, choices=[
        ('remote', 'Remote'),
        ('onsite', 'On-site'),
        ('hybrid', 'Hybrid')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.student.user.username}"

class SavedApplication(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='saved_applications')
    personal_info = models.TextField()
    academic_details = models.TextField()
    preferences = models.TextField()
    saved_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Saved application for {self.student.user.username}"

class StudentNotification(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('deadline', 'Deadline'),
        ('feedback', 'Feedback'),
        ('meeting', 'Meeting'),
        ('application_status', 'Application Status'),
        ('general', 'General')
    ])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.student.user.username}"

class Document(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=[
        ('resume', 'Resume'),
        ('transcript', 'Transcript'),
        ('cover_letter', 'Cover Letter'),
        ('certificate', 'Certificate'),
        ('other', 'Other')
    ])
    file = models.FileField(upload_to='student_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.document_type} for {self.student.user.username}"
