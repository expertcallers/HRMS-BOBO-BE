from django.core.validators import validate_email
from rest_framework import serializers

from po.models import SupplierAdministration, BillAdministration, BillItemDescription
from utils.utils import get_decrypted_name, validate_bnk_account_no


class ItemDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillItemDescription
        exclude = ["created_at"]


class ItemDescriptionInfoSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["bill_id"] = instance.bill.id
        data["bill_project"] = instance.bill.project
        return data

    class Meta:
        model = BillItemDescription
        exclude = ["created_by", "bill"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierAdministration
        fields = "__all__"


class UpdateSupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierAdministration
        exclude = ["contact_email", "account_number", "name", "pan_no", "gst"]


class SupplierInfoSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["pan_no"] = get_decrypted_name(instance.pan_no)
        data["gst"] = get_decrypted_name(instance.gst)
        data["acc_name"] = get_decrypted_name(instance.acc_name)
        data["account_number"] = get_decrypted_name(instance.account_number)
        data["bank_name"] = get_decrypted_name(instance.bank_name)
        data["ifsc"] = get_decrypted_name(instance.ifsc)
        data["cin_code"] = get_decrypted_name(instance.cin_code) if instance.cin_code else None
        return data

    class Meta:
        model = SupplierAdministration
        exclude = ["created_by", "pan_no", "gst", "acc_name", "account_number", "bank_name", "ifsc", "cin_code"]


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillAdministration
        exclude = ["created_at", "updated_at"]


class BillInfoSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        from po.views import get_all_item_by_po_id
        data = super().to_representation(instance)
        data["supplier"] = SupplierInfoSerializer(instance.supplier).data
        data["supplier_name"] = instance.supplier.name
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["pan"] = get_decrypted_name(instance.pan)
        data["gst"] = get_decrypted_name(instance.gst)
        all_items = get_all_item_by_po_id(instance.id)
        data["description"] = ItemDescriptionInfoSerializer(all_items, many=True).data
        return data

    class Meta:
        model = BillAdministration
        exclude = ["created_by", "supplier"]
