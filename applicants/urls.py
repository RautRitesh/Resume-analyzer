from django.urls import path,include
from .models import dashboard
urlpatterns = [
    path('dashboards/',dashboard,name='home'),
]