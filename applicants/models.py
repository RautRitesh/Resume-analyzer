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
    