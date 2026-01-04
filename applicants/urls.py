from django.urls import path,include
from .views import dashboard, resumeanalysis
urlpatterns = [
    path('',dashboard,name='home'),
    path('uploaddocument/',resumeanalysis,name='upload'),
]