from django.shortcuts import render,redirect
from django.urls import reverse_lazy
from .models import User,PendingUser
from datetime import datetime, timezone
from django.contrib import messages,auth
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from common.task import send_email
# Create your views here.
def register(request):
    if request.method=="POST":
        email=request.POST.get("email")
        cleaned_email=email.lower()
        password= request.POST.get("password")
        username=request.POST.get("username")
        user = User.objects.filter(email=cleaned_email)
        if not user: 
            messages.error(request,"Email is already registered")
            return reverse_lazy('register')
        pendinguser,_=PendingUser.objects.update_or_create(
            email=cleaned_email,
            username=username,
            defaults={
                "password":make_password(password),
                "verification_code":get_random_string(10),
                "created_at":datetime.now(timezone.utc)
            }
        )
        email_data={
            "email":pendinguser.email,
            "verification_code":pendinguser.verification_code,
        }
        send_email("Verification code for Resume Analyzer app",[cleaned_email],
                   "emails/sent_verification_code.html",
                   context=email_data)
        messages.success(request,"Verification code sent sucessfully!")
        
        return render(request,"accounts/verify_code.html",{"email":cleaned_email})
    else:
        return render(request,"accounts/registration.html")
    
    
def verify_code(request):
    if request.method=="POST":
        email:str=request.POST.get("email")#from hidden field
        verification_code=request.POST.get("verification_code")
        user=PendingUser.objects.filter(email=email,verification_code=verification_code).first()
        if user and user.is_valid():
            real_user=User.obects.create(
                email=email,
                password=user.password,
                username=user.username
            )
            messages.success(request,"Verification done sucessfully")
            auth.login(request,real_user)
            user.delete()
            return redirect('home')  
        else:
            messages.error(request,"Expired Code")
            return render(request,"accounts/verify_code.html",{"email":email})
            
    else:
        return redirect('register')# we do not want the user to go through url to verify_code user must go through register only
        