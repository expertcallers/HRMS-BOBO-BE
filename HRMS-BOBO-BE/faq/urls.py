from django.urls import path

from faq import views

urlpatterns = [
    path('get_all_faq', views.get_all_faq),
    path('get_user_manual', views.get_user_manual)
]
