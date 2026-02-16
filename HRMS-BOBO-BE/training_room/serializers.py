from rest_framework import serializers
from .models import *


class BookSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookSlot
        exclude = ["booked_at"]


class ViewBookedSlotSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["booked_by"] = instance.booked_by.first_name + " " + instance.booked_by.last_name
        return data

    class Meta:
        model = BookSlot
        fields = '__all__'


class CreateTrainingRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRoom
        fields = '__all__'

