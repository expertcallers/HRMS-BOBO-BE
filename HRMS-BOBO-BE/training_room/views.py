import json
from rest_framework import status, authentication, permissions
from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated

from utils.util_classes import CustomTokenAuthentication
from .models import *
from .serializers import *
from utils.utils import return_error_response, update_request


def get_training_room_by_id(room_id):
    if not str(room_id).isnumeric() or room_id is None:
        raise ValueError('{0} is invalid, Please provide a Valid ID'.format(room_id))
    try:
        training_room = TrainingRoom.objects.get(id=room_id)
    except Exception as e:
        raise ValueError('IJP record not found')
    return training_room


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def book_training_room(request):
    try:
        data = update_request(request.data, booked_by=request.user.id)
        serializer = BookSlotSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        room = serializer.validated_data["training_room"]
        all_booked_session = BookSlot.objects.filter(training_room=room.id)
        new_start = serializer.validated_data["start_datetime"]
        new_end = serializer.validated_data["end_datetime"]
        for i in all_booked_session:
            if (new_start >= i.start_datetime and new_start < i.end_datetime) or (
                    new_start <= i.start_datetime and new_end >= i.end_datetime) or (
                    new_end > i.start_datetime and new_end <= i.end_datetime):
                raise ValueError(
                    "Room '{2}' is occupied for the Slot {0} - {1}".format(i.start_datetime, i.end_datetime, room))
        book_room = serializer.create(serializer.validated_data)
        book_room = ViewBookedSlotSerializer(book_room).data
        return HttpResponse(json.dumps({"room": book_room}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_training_room(request):
    try:
        existing_room = TrainingRoom.objects.filter(name=request.data.get("name"))
        if existing_room:
            raise ValueError("Training Room with this name is already Available.")
        is_projector_available = request.data.get("is_projector_available", None)
        is_screen_available = request.data.get("is_screen_available", None)
        is_white_board_available = request.data.get("is_white_board_available", None)
        data = update_request(request.data, is_projector_available=is_projector_available,
                              is_screen_available=is_screen_available,
                              is_white_board_available=is_white_board_available)
        serializer = CreateTrainingRoomSerializer(data=data)

        if not serializer.is_valid():
            return return_error_response(serializer)
        training_room = serializer.create(serializer.validated_data)
        training_room = CreateTrainingRoomSerializer(training_room).data
        return HttpResponse(json.dumps({"training_room": training_room}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def view_all_booked_slots(request, room_id):
    try:
        training_room = get_training_room_by_id(room_id)
        booked_slots = BookSlot.objects.filter(training_room=training_room)
        booked_slots = ViewBookedSlotSerializer(booked_slots, many=True).data
        return HttpResponse(json.dumps({"booked_slots": booked_slots}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)