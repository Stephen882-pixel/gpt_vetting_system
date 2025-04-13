from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('home/', views.home, name='home'),
    path('skill/create/', views.skill_create, name='skill_create'),
    path('interview/start/', views.interview, name='interview'),
    path('interview/results/', views.interview_results, name='interview_results'),
]
