from django import forms
from django.utils import timezone
from .models import Notification, NotificationTemplate, NotificationPreference

class NotificationForm(forms.ModelForm):
    """Form for creating notifications"""
    recipients = forms.CharField(
        widget=forms.Textarea,
        help_text="Enter user IDs, emails, or usernames separated by commas",
        required=False
    )
    
    scheduled_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Schedule notification for later delivery"
    )
    
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Notification will expire at this time"
    )
    
    class Meta:
        model = Notification
        fields = [
            'title', 'message', 'notification_type', 'is_priority', 
            'recipients', 'scheduled_time', 'expires_at', 'target_url',
            'action_required', 'data'
        ]
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter notification message...'}),
            'data': forms.Textarea(attrs={'rows': 3, 'placeholder': 'JSON data (optional)...'}),
        }
    
    def clean_data(self):
        """Validate JSON data field"""
        data = self.cleaned_data.get('data')
        if data:
            try:
                if isinstance(data, str):
                    import json
                    data = json.loads(data)
                # Validate it's a dictionary
                if not isinstance(data, dict):
                    raise forms.ValidationError('Data must be a JSON object')
            except json.JSONDecodeError:
                raise forms.ValidationError('Invalid JSON format')
        return data
    
    def clean_scheduled_time(self):
        """Validate scheduled time is in the future"""
        scheduled_time = self.cleaned_data.get('scheduled_time')
        if scheduled_time and scheduled_time <= timezone.now():
            raise forms.ValidationError('Scheduled time must be in the future')
        return scheduled_time
    
    def clean_expires_at(self):
        """Validate expiration time is after scheduled time"""
        expires_at = self.cleaned_data.get('expires_at')
        scheduled_time = self.cleaned_data.get('scheduled_time')
        
        if expires_at and scheduled_time:
            if expires_at <= scheduled_time:
                raise forms.ValidationError('Expiration time must be after scheduled time')
        elif expires_at and expires_at <= timezone.now():
            raise forms.ValidationError('Expiration time must be in the future')
        
        return expires_at

class NotificationPreferenceForm(forms.ModelForm):
    """Form for user notification preferences"""
    class Meta:
        model = NotificationPreference
        fields = [
            'email_notifications', 'email_frequency', 'push_notifications',
            'in_app_notifications', 'quiet_hours_enabled', 'quiet_start',
            'quiet_end', 'do_not_disturb', 'do_not_disturb_until'
        ]
        
        widgets = {
            'quiet_start': forms.TimeInput(attrs={'type': 'time'}),
            'quiet_end': forms.TimeInput(attrs={'type': 'time'}),
            'do_not_disturb_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'email_frequency': forms.Select(choices=[
                ('immediate', 'Immediate'),
                ('daily', 'Daily'),
                ('weekly', 'Weekly'),
                ('never', 'Never')
            ])
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add dynamic fields for notification type preferences
        notification_types = dict(Notification.NOTIFICATION_TYPES)
        
        # Email type preferences
        self.fields['email_types'] = forms.JSONField(
            label='Email Notification Types',
            help_text='Select notification types to send via email',
            initial={},
            widget=forms.widgets.CheckboxSelectMultiple(
                choices=[(key, value) for key, value in notification_types.items()]
            )
        )
        
        # Push type preferences
        self.fields['push_types'] = forms.JSONField(
            label='Push Notification Types',
            help_text='Select notification types to send via push',
            initial={},
            widget=forms.widgets.CheckboxSelectMultiple(
                choices=[(key, value) for key, value in notification_types.items()]
            )
        )
        
        # In-app type preferences
        self.fields['in_app_types'] = forms.JSONField(
            label='In-App Notification Types',
            help_text='Select notification types to show in-app',
            initial={},
            widget=forms.widgets.CheckboxSelectMultiple(
                choices=[(key, value) for key, value in notification_types.items()]
            )
        )
        
        # Set initial values based on existing instance
        if self.instance:
            # Initialize checkbox fields
            for field_name in ['email_types', 'push_types', 'in_app_types']:
                if hasattr(self.instance, field_name):
                    initial_value = getattr(self.instance, field_name)
                    if isinstance(initial_value, dict):
                        self.fields[field_name].initial = initial_value

class NotificationTemplateForm(forms.ModelForm):
    """Form for creating notification templates"""
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'title_template', 'message_template', 'notification_type',
            'template_variables', 'is_priority', 'default_target_url',
            'action_required'
        ]
        widgets = {
            'title_template': forms.TextInput(attrs={'placeholder': 'Use {variable_name} for template variables'}),
            'message_template': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Use {variable_name} for template variables'}),
            'template_variables': forms.Textarea(attrs={'rows': 3, 'placeholder': 'JSON format: {"variable_name": "Description"}'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Template description...'}),
        }
    
    def clean_template_variables(self):
        """Validate template variables JSON"""
        template_variables = self.cleaned_data.get('template_variables')
        if template_variables:
            try:
                if isinstance(template_variables, str):
                    import json
                    template_variables = json.loads(template_variables)
                # Validate it's a dictionary
                if not isinstance(template_variables, dict):
                    raise forms.ValidationError('Template variables must be a JSON object')
            except json.JSONDecodeError:
                raise forms.ValidationError('Invalid JSON format for template variables')
        return template_variables
    
    def clean(self):
        """Validate template contains variables"""
        cleaned_data = super().clean()
        title_template = cleaned_data.get('title_template')
        message_template = cleaned_data.get('message_template')
        template_variables = cleaned_data.get('template_variables')
        
        # Extract variables from template
        import re
        title_vars = set(re.findall(r'\{(\w+)\}', title_template))
        message_vars = set(re.findall(r'\{(\w+)\}', message_template))
        all_vars = title_vars.union(message_vars)
        
        if template_variables:
            template_vars = set(template_variables.keys())
            missing_vars = all_vars - template_vars
            if missing_vars:
                raise forms.ValidationError(
                    f'Template variables are missing for: {", ".join(missing_vars)}'
                )
        
        return cleaned_data

class NotificationBatchForm(forms.ModelForm):
    """Form for creating notification batches"""
    class Meta:
        model = NotificationBatch
        fields = ['name', 'description', 'template']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Batch name'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Batch description'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add custom fields for batch creation
        self.fields['user_ids'] = forms.CharField(
            widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'User IDs, emails, or usernames separated by commas'}),
            label='Recipients'
        )
        
        self.fields['context_data'] = forms.CharField(
            widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'JSON context data for template variables'}),
            label='Context Data',
            help_text='JSON format for template variables (optional)',
            required=False
        )
        
        # Set initial context data
        if self.instance and self.instance.context:
            import json
            self.fields['context_data'].initial = json.dumps(self.instance.context, indent=2)

class NotificationSearchForm(forms.Form):
    """Form for searching notifications"""
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search notifications...',
            'class': 'form-control'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + [
            ('unread', 'Unread'),
            ('read', 'Read'),
            ('archived', 'Archived')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    notification_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Notification.NOTIFICATION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text='Start date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text='End date'
    )
    
    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError('Start date must be before end date')
        
        return cleaned_data

class NotificationSettingsForm(forms.ModelForm):
    """Form for advanced notification settings"""
    class Meta:
        model = NotificationPreference
        fields = [
            'email_notifications', 'push_notifications', 'in_app_notifications',
            'email_frequency', 'quiet_hours_enabled', 'quiet_start',
            'quiet_end', 'do_not_disturb', 'do_not_disturb_until'
        ]
        
        widgets = {
            'quiet_start': forms.TimeInput(attrs={'type': 'time'}),
            'quiet_end': forms.TimeInput(attrs={'type': 'time'}),
            'do_not_disturb_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add notification type preferences as checkboxes
        notification_types = dict(Notification.NOTIFICATION_TYPES)
        
        for channel in ['email', 'push', 'in_app']:
            self.fields[f'{channel}_types'] = forms.MultipleChoiceField(
                label=f'{channel.title()} Notification Types',
                choices=notification_types.items(),
                widget=forms.CheckboxSelectMultiple,
                required=False
            )
            
            # Set initial values
            if self.instance and hasattr(self.instance, f'{channel}_types'):
                initial_value = getattr(self.instance, f'{channel}_types')
                if isinstance(initial_value, dict):
                    self.fields[f'{channel}_types'].initial = [
                        key for key, value in initial_value.items() if value
                    ]

class NotificationAnalyticsForm(forms.Form):
    """Form for filtering analytics data"""
    date_range = forms.ChoiceField(
        choices=[
            ('7', 'Last 7 days'),
            ('30', 'Last 30 days'),
            ('90', 'Last 90 days'),
            ('365', 'Last year'),
            ('custom', 'Custom range')
        ],
        initial='30',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    custom_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    custom_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    notification_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Notification.NOTIFICATION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    channel = forms.ChoiceField(
        choices=[('', 'All Channels'), ('email', 'Email'), ('push', 'Push'), ('in_app', 'In-App')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        """Validate custom date range if selected"""
        cleaned_data = super().clean()
        date_range = cleaned_data.get('date_range')
        
        if date_range == 'custom':
            custom_date_from = cleaned_data.get('custom_date_from')
            custom_date_to = cleaned_data.get('custom_date_to')
            
            if not custom_date_from or not custom_date_to:
                raise forms.ValidationError('Both start and end dates are required for custom range')
            
            if custom_date_from > custom_date_to:
                raise forms.ValidationError('Start date must be before end date')
        
        return cleaned_data
