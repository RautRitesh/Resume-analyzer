from django.shortcuts import render,redirect
from django.urls import reverse_lazy
from .models import User,PendingUser, Token
from datetime import datetime, timezone
from django.contrib import messages,auth
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from common.task import send_email
from .decorators import redirect_authenticated_user
from django.contrib.auth.decorators import login_required
# Create your views here.
#small update
@login_required(login_url='login')
def home(request):
    return render(request,"accounts/home.html")


@redirect_authenticated_user
def register(request):
    if request.method=="POST":
        email=request.POST.get("email")
        cleaned_email=email.lower()
        password= request.POST.get("password")
        username=request.POST.get("username")
        user = User.objects.filter(email=cleaned_email)
        if user.exists(): 
            messages.error(request,"Email is already registered")
            return redirect('register')
        pendinguser,_=PendingUser.objects.update_or_create(
            email=cleaned_email,
            defaults={
                "username":username,
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
    
@redirect_authenticated_user  
def verify_code(request):
    if request.method=="POST":
        email:str=request.POST.get("email")#from hidden field
        verification_code=request.POST.get("verification_code")
        user=PendingUser.objects.filter(email=email,verification_code=verification_code).first()
        if user and user.is_valid():
            real_user=User.objects.create(
                email=email,
                password=user.password,
                username=user.username
            )
            messages.success(request,"Verification done sucessfully")
            auth.login(request,real_user)
            user.delete()
            return redirect('dashboard')  
        else:
            messages.error(request,"Expired Code")
            return render(request,"accounts/verify_code.html",{"email":email})
            
    else:
        return redirect('register')# we do not want the user to go through url to verify_code user must go through register only
        
@redirect_authenticated_user       
def login(request):
    if request.method=="POST":
        email:str=request.POST.get("email","")
        password:str=request.POST.get("password","")
        user=auth.authenticate(request,email=email.lower(),password=password)
        if user is not None:
            messages.success(request,"Login sucessfull")
            auth.login(request,user)
            return redirect('dashboard')
        else:
            messages.error(request,"Invalid Email or Password")
            return redirect('login')
        
    else: 
        return render(request,"accounts/login.html")
    
@login_required(login_url='login')   
def logout(request):
    messages.success(request,"Logout sucessfull")
    auth.logout(request)
    return redirect('login')

@redirect_authenticated_user
def forgot_password(request):
    if request.method=="POST":
        email:str = request.POST.get("email","")
        user:User=User.objects.filter(email=email).first()
        if user:
           access_token=get_random_string(20)
           token,_=Token.objects.update_or_create(
               user=user,
               defaults={
                   "access_token":access_token,
                   "created_at":datetime.now(timezone.utc)
               }
           )
           email_data={
               "access_token":access_token,
               "email":email.lower()
           }
           send_email(
               "Password reset link for Resume Analyzer app",
               [email.lower()],
               "emails/password_reset_link.html",
               email_data   
           )
           messages.success(request,"Link sent sucessfully")
           return redirect('login')
        else:
            messages.error(request,"This is not correct Email")
            return redirect('login')
    else:
        return render(request,"accounts/forgot_password.html")
    
    
@redirect_authenticated_user    
def verify_password_reset_link(request):
    email= request.GET.get("email","")
    access_token=request.GET.get("access_token","")
    token=Token.objects.filter(user__email=email,access_token=access_token).first()
    if not token or  not token.is_valid():
        messages.error(request,"Expired Token")
        return redirect('login')
    else:
        messages.success(request,"Token verification sucessfull")
        return render(request,"accounts/set_new_password.html",{"email":email,"access_token":access_token})
    
@redirect_authenticated_user    
def set_new_password(request):
    if request.method=="POST":
        password1=request.POST.get("password1")
        password2=request.POST.get("password2")
        email=request.POST.get("email") # from hidden fields
        access_token=request.POST.get("access_token")
        if password1 != password2:
            return render(request,"accounts/set_new_password.html",{"email":email,"access_token":access_token})
        else:
            token=Token.objects.filter(user__email=email,access_token=access_token).first()
            if  token or  token.is_valid():
                token.change_password(password1)
                messages.success(request,"Password changed sucessfully")
                token.delete()
                return redirect('login')
            else: 
                messages.error(request,"Expired Token")
                return redirect('login')
    else: 
        return redirect('home')
        
    
    