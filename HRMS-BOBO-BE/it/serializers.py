from rest_framework import serializers

from it.models import ChangeMgmt


class CreateChangeMgmtSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeMgmt
        fields = "__all__"


class UpdateChangeMgmtSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeMgmt
        exclude = ["change_approved_date", "change_approved_by", "reviewed_by", "reviewed_date", "rejected_by",
                   "rejected_date", "change_status"]


class GetAllChangeMgmtSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["initiated_by_emp_id"] = instance.initiated_by.emp_id if instance.initiated_by else None
        data["initiated_by_name"] = instance.initiated_by.full_name if instance.initiated_by else None
        data["implemented_by_emp_id"] = instance.implemented_by.emp_id if instance.implemented_by else None
        data["implemented_by_name"] = instance.implemented_by.full_name if instance.implemented_by else None
        data["change_approved_by_emp_id"] = instance.change_approved_by.emp_id if instance.change_approved_by else None
        data["change_approved_by_name"] = instance.change_approved_by.full_name if instance.change_approved_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["reviewed_by_emp_id"] = instance.reviewed_by.emp_id if instance.reviewed_by else None
        data["reviewed_by_name"] = instance.reviewed_by.full_name if instance.reviewed_by else None
        data["rejected_by_emp_id"] = instance.rejected_by.emp_id if instance.rejected_by else None
        data["rejected_by_name"] = instance.rejected_by.full_name if instance.rejected_by else None
        return data

    class Meta:
        model = ChangeMgmt
        exclude = ["initiated_by", "implemented_by", "change_approved_by"]
