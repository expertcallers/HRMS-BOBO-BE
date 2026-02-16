from rest_framework.serializers import ModelSerializer

from powerbi.models import SOP, SOPSourceData


class CreateSOPSerializer(ModelSerializer):
    class Meta:
        model = SOP
        fields = "__all__"


class GetSOPSerializer(ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["campaign"] = instance.campaign.name if instance.campaign else None
        data["sop_source_data"] = GetSOPSourceDataSerializer(SOPSourceData.objects.filter(sop=instance), many=True).data
        return data

    class Meta:
        model = SOP
        exclude = ("created_by",)


class GetAllSOPSerializer(ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["campaign"] = instance.campaign.name if instance.campaign else None
        return data

    class Meta:
        model = SOP
        fields = ["campaign_type", "status", "campaign_type_other", "process_type_one", "process_type_two",
                  "process_type_three", "created_at", "updated_at", "id"]


class CreateSOPSourceDataSerializer(ModelSerializer):
    class Meta:
        model = SOPSourceData
        exclude = ("sop",)


class GetSOPSourceDataSerializer(ModelSerializer):
    class Meta:
        model = SOPSourceData
        exclude = ("sop",)
