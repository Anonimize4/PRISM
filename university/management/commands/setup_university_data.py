from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from university.models import Supervisor, AttendanceRecord
from recruitment.models import InternshipApplication
from datetime import date, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup initial university data for productivity'

    def handle(self, *args, **options):
        self.stdout.write('Setting up university data...')
        
        # Create sample supervisors
        self.create_supervisors()
        
        # Generate attendance records for students
        self.generate_attendance_records()
        
        self.stdout.write(self.style.SUCCESS('University data setup completed!'))

    def create_supervisors(self):
        supervisors_data = [
            {'username': 'supervisor1', 'email': 'supervisor1@university.edu', 'department': 'Computer Science', 'title': 'Professor'},
            {'username': 'supervisor2', 'email': 'supervisor2@university.edu', 'department': 'Engineering', 'title': 'Associate Professor'},
            {'username': 'supervisor3', 'email': 'supervisor3@university.edu', 'department': 'Business', 'title': 'Assistant Professor'},
        ]
        
        for data in supervisors_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'role': 'supervisor',
                    'first_name': data['username'].title(),
                    'last_name': 'Supervisor'
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                
                Supervisor.objects.get_or_create(
                    user=user,
                    defaults={
                        'department': data['department'],
                        'title': data['title']
                    }
                )
                self.stdout.write(f'Created supervisor: {user.username}')

    def generate_attendance_records(self):
        students = User.objects.filter(role='student')
        
        for student in students:
            # Generate 30 days of attendance records
            start_date = date.today() - timedelta(days=30)
            
            for i in range(30):
                current_date = start_date + timedelta(days=i)
                
                # Skip weekends
                if current_date.weekday() >= 5:
                    continue
                
                # Random attendance with 85% present rate
                status = 'present' if random.random() < 0.85 else random.choice(['absent', 'late'])
                
                AttendanceRecord.objects.get_or_create(
                    student=student,
                    date=current_date,
                    defaults={'status': status}
                )
        
        self.stdout.write(f'Generated attendance records for {students.count()} students')