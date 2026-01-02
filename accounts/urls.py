from django.urls import path,include
from .views import register

urlpatterns = [
    path('accounts/register',register ,name='register'),
]