from django.apps import apps
from rest_framework import serializers

from report.models import *


class GetAllReportsFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportFile
        fields = "__all__"


class CreateSLASerializer(serializers.ModelSerializer):
    class Meta:
        model = SLA
        fields = "__all__"


class CreateTASerializer(serializers.ModelSerializer):
    class Meta:
        model = TA
        fields = "__all__"


class GbmDialerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GbmDialer
        fields = "__all__"


class GbmLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = GbmLead
        fields = "__all__"


class GbmEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = GbmEmail
        fields = "__all__"


class GbmCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = GbmCall
        fields = "__all__"


class AadyaSolutionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AadyaSolutions
        fields = "__all__"


class InsalvageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insalvage
        fields = "__all__"


class MedicareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicare
        fields = "__all__"


class SapphireMedicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SapphireMedical
        fields = "__all__"


class CapgeminiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Capgemini
        fields = "__all__"


class BBMSerializer(serializers.ModelSerializer):
    class Meta:
        model = BBM
        fields = "__all__"
# def create_serializer_class(model_class):
#     # model_class = apps.get_model(app_label="report", model_name=model_name)
#
#     class Meta:
#         model = model_class
#         fields = "__all__"
#
#     serializer_class = type(f"Create{model_class.__name__}Serializer", (serializers.ModelSerializer,), {'Meta': Meta})
#     return serializer_class
