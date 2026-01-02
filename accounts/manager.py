from django.contrib.auth.base_user import BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self,email,password,**extra_field):
        if not email:
            raise ValueError("Email is always required")
        user=self.model(email=email,**extra_field)
        user.set_password(password)
        user.save()
        return user
    
    def create_superuser(self,email,password,**extra_field):
        extra_field.setdefault("is_staff",True)
        extra_field.setdefault("is_active",True)
        extra_field.setdefault("is_superuser",True)
        if  extra_field.get("is_staff") is not True:
            raise ValueError("Super user must be staff")
        if extra_field.get("is_superuser") is not True:
            raise ValueError("Superuser must be superuser ")
        user=self.create_user(email,password, **extra_field)
        return user 
        