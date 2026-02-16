import json

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated

from utils.util_classes import CustomTokenAuthentication
from utils.utils import chat_gpt_completion_api


@api_view(["POST"])
# @authentication_classes([CustomTokenAuthentication])
# @permission_classes([IsAuthenticated])
def ask_emma(request):
    emma_request = request.data.get("emma_request")
    if emma_request is None or emma_request == "":
        return HttpResponse(json.dumps({"message": ""}))
    return HttpResponse(json.dumps({"message": chat_gpt_completion_api(emma_request)}))
