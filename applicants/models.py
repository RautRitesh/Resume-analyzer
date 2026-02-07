from django.db import models
from django.conf import settings  # <--- IMPORT SETTINGS INSTEAD OF USER

class ResumeAnalysis(models.Model):
    # Use settings.AUTH_USER_MODEL to refer to your custom user safely
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resume_analysis')
    
    job_title = models.CharField(max_length=255)
    job_description = models.TextField()
    resume_file = models.FileField(upload_to='resume/pdf/')
    
    # Stores the clean JSON from the LLM (Skills, Experience, Projects)
    parsed_resume_data = models.JSONField(null=True, blank=True)

    # Dashboard Metrics
    overall_match_score = models.FloatField(default=0.0)
    section_match_score = models.JSONField(default=dict)
    retrieved_evidence = models.JSONField(default=dict)
    missing_keywords = models.JSONField(default=list)
    analysis_summary = models.TextField(blank=True, null=True)
    improved_suggestion = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # We use string formatting because self.user might be an email or username depending on your custom model
        return f"{self.user} - {self.job_title}"

class InterviewSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    analysis = models.ForeignKey(ResumeAnalysis, on_delete=models.CASCADE)
    
    chat_history = models.JSONField(default=list)
    current_stage = models.CharField(max_length=50, default="project_manager")
    
    interview_feedback = models.JSONField(null=True, blank=True)
    verdict = models.CharField(
        max_length=20, 
        choices=[('PENDING', 'Pending'), ('SELECTED', 'Selected'), ('REJECTED', 'Rejected')], 
        default='PENDING'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)