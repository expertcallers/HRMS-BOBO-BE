from rest_framework import serializers
from .models import Asset, AssetCategory, AssetHistory, AssetAllocation, Document
from utils.utils import get_formatted_name, form_module_url


def form_document_url(doc_id):
    return form_module_url(doc_id, "asset")


def get_path_and_name_dict(obj):
    if not obj:
        return None
    return {"path": form_document_url(obj.id), "name": obj.file.name.split("/")[::-1][0]}


class AssetSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_emp_id"] = instance.created_by.emp_id
        data["created_by_name"] = instance.created_by.full_name
        data["asset_category"] = instance.asset_category.name
        assigned = AssetAllocation.objects.filter(asset=instance.id, status="Issued").last()
        data["assigned_to_name"] = assigned.assigned_to.full_name if assigned else None
        data["assigned_to_emp_id"] = assigned.assigned_to.emp_id if assigned else None
        return data

    class Meta:
        model = Asset
        fields = '__all__'


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ["name"]


class UpdateAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        exclude = ["asset_category", "status"]


class AssetHistorySerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_emp_id"] = instance.created_by.emp_id
        data["created_by_name"] = instance.created_by.full_name
        return data

    class Meta:
        model = AssetHistory
        fields = '__all__'


class AssetAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAllocation
        exclude = ["status", "docs"]


class DocumentSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["path"] = form_document_url(instance.id)
        data["name"] = instance.file.name.split("/")[::-1][0]
        return data

    class Meta:
        model = Document
        exclude = ("field", "asset_allocation_id", "file")


class ViewAssetAllocationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["assigned_by_emp_id"] = instance.assigned_by.emp_id
        data["assigned_by_name"] = instance.assigned_by.full_name
        data["assigned_to_emp_id"] = instance.assigned_to.emp_id
        data["assigned_to_name"] = instance.assigned_to.full_name
        data["docs"] = DocumentSerializer(instance.docs.all(), many=True).data
        data["asset_category"] = instance.asset.asset_category.name
        data["serial_number"] = instance.asset.serial_number
        return data

    class Meta:
        model = AssetAllocation
        fields = '__all__'


class UpdateAssetStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["status"]
