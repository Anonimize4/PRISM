from django.urls import path
from . import views

urlpatterns = [
    # Student Dashboard and Profile
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('create-profile/', views.create_profile, name='create_profile'),
    path('create-academic-info/', views.create_academic_info, name='create_academic_info'),
    path('view-profile/', views.view_profile, name='view_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('edit-academic-info/', views.edit_academic_info, name='edit_academic_info'),
    
    # Internship Preferences
    path('internship-preferences/', views.internship_preferences, name='internship_preferences'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    
    # Documents
    path('documents/', views.documents, name='documents'),
    path('delete-document/<int:document_id>/', views.delete_document, name='delete_document'),
    
    # Saved Applications
    path('saved-applications/', views.saved_applications, name='saved_applications'),
]
