from django.db import models
from mapping.models import Profile
from django.core.exceptions import ValidationError


class TrainingRoom(models.Model):
    name = models.CharField(max_length=100)
    is_projector_available = models.BooleanField()
    is_screen_available = models.BooleanField()
    is_white_board_available = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BookSlot(models.Model):
    training_room = models.ForeignKey(TrainingRoom, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    booked_at = models.DateTimeField(auto_now_add=True)
    booked_by = models.ForeignKey(Profile, on_delete=models.CASCADE)
