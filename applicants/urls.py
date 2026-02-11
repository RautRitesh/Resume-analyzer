from django.urls import path,include
from .views import dashboard, resumeanalysis, chat_api, interview_room
urlpatterns = [
    path('',dashboard,name='dashboard'),
    path('uploaddocument/',resumeanalysis,name='upload'),
    path('interview/api/<int:analysis_id>/',chat_api, name='chat_api'),
    path('interview/<int:analysis_id>/', interview_room, name='interview_room'),
]