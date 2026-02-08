from django.urls import path,include
from .views import dashboard, resumeanalysis
urlpatterns = [
    path('',dashboard,name='dashboard'),
    path('uploaddocument/',resumeanalysis,name='upload'),
]