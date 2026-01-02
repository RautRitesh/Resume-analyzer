from django.db import models
from django.contrib.auth.models import PermissionsMixin, AbstractBaseUser
from .manager import CustomUserManager
from common.models import BaseModel
from datetime import timezone,datetime
# Create your models here.
class User(AbstractBaseUser,PermissionsMixin,BaseModel):
    username=models.CharField(max_length=255,unique=True)
    email = models.EmailField(unique=True)
    USERNAME_FIELD="email"
    REQUIRED_FIELDS=["username"]
    password = models.CharField(max_length=255)
    is_active= models.BooleanField(default=True)
    is_staff=models.BooleanField(default=False)
    objects=CustomUserManager()
    
    
class PendingUser(BaseModel):
    username=models.CharField(unique=True,max_length=255)
    email=models.EmailField(unique=True)
    password=models.CharField(max_length=255)
    verification_code = models.CharField(max_length=255)
    
    def is_valid(self)->bool:
        life_in_span=20*60
        now = datetime.now(timezone.utc)
        time_diff= now-self.created_at
        time_diff= time_diff.total_seconds()
        if time_diff>life_in_span:
            return False 
        return True
    
    
    