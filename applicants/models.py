from django.db import models
from django.conf import settings
from common.models import BaseModel

# Create your models here.
class ResumeAnalysis(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resume_analysis'
    )
    job_title=models.CharField(max_length=255,help_text="Target job Role")
    job_description=models.TextField(help_text="The raw requirements for the jobs")
    resume_file=models.FileField(upload_to='resume/pdf/')
    overall_match_score=models.FloatField(default=0.0)
    section_match_score=models.JSONField(default=dict)
    retrieved_evidence=models.JSONField(default=dict,blank=True)
    missing_keywords=models.JSONField(default=list,blank=True)
    analysis_summary=models.TextField(blank=True,help_text="AI generated summary for the resume")
    improved_suggestion=models.JSONField(default=list,blank=True)
    
    def __str__(self):
        return f"{self.user.username}|{self.job_title}"
    
    class Meta:
        ordering=['-created_at']
        verbose_name_plural="Resume Analyses"
        
    
    