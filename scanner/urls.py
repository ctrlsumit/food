# scanner/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Frontend render
    path('', views.index, name='index'),
    
    # API endpoints
    path('api/analyze/', views.analyze_food, name='analyze_food'),
    path('api/feedback/', views.submit_feedback, name='submit_feedback'),
    path('api/feedback/stats/', views.feedback_stats, name='feedback_stats'),
]
