from django.urls import path
from .views import *

urlpatterns = [
    path('book_training_room', book_training_room),
    path('create_training_room', create_training_room),
    path('view_all_booked_slots/<int:room_id>', view_all_booked_slots),
]