from django.urls import path,include
from .views import register, home, login, logout, forgot_password, verify_code, verify_password_reset_link, set_new_password

urlpatterns = [
    path('',home,name='home'),
    path('accounts/register/',register ,name='register'),
    path('accounts/login/',login,name='login'),
    path('accounts/forgot_password/',forgot_password,name='forgot-password'),
    path('accounts/verify_code/',verify_code,name='verify-code'),
    path('accounts/verify_password_reset_link/',verify_password_reset_link,name='verify-password-reset-link'),
    path('accounts/set_new_password',set_new_password,name='set-new-password'),
    path('accounts/logout',logout,name='logout')
    
]