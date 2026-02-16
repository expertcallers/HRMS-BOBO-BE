from django.urls import path
from ask_emma import views

urlpatterns = [
    path("ask_emma", views.ask_emma, name="ask_emma")
]
