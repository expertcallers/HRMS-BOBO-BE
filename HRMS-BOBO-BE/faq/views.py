import json

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin

from faq.models import FAQ, GenericRichTextData
from faq.serializers import GetALLFAQSerializer


# Create your views here.
class GetAllFAQ(GenericAPIView, ListModelMixin):
    serializer_class = GetALLFAQSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        self.queryset = FAQ.objects.all().order_by("id")
        return self.list(request, *args, **kwargs)


@api_view(["GET"])
def get_all_faq(request):
    faqs = list(FAQ.objects.all().values("question", "answer").order_by("updated_at"))
    return HttpResponse(json.dumps({"results": faqs}))


@api_view(["GET"])
def get_user_manual(request):
    manual = GenericRichTextData.objects.filter(title="ecpl_user_guidelines").last()
    if manual is None:
        return HttpResponse(json.dumps({"results": "HRMS Policy guidelines are not available as of now"}))
    return HttpResponse(json.dumps({"results": manual.content}))
