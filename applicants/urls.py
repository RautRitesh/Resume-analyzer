from django.urls import path,include
from .views import dashboard, resumeanalysis
urlpatterns = [
    path('dashboards/',dashboard,name='home'),
    path('uploaddocument/',resumeanalysis,name='upload'),
]