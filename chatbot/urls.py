from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('api/ask/', views.api_ask, name='api_ask'),
    path('api/suggest/', views.api_suggest, name='api_suggest'),   # NEW
    path('api/feedback/', views.api_feedback, name='api_feedback'),
    path('api/faq/<int:faq_id>/', views.api_faq_detail, name='api_faq_detail'),
    path('api/reset/', views.api_reset, name='api_reset'),
]