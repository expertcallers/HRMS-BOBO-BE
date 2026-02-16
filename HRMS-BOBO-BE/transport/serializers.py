from rest_framework.serializers import ModelSerializer

from transport.models import CabDetail
from utils.utils import get_column_names_only


class CabAddressDetailSerializer(ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        cnd = instance.candidate if instance.candidate else None
        data["emp_id"] = instance.employee.emp_id if instance.employee else None
        data["emp_name"] = cnd.full_name if cnd else None
        data[
            "approved_by_emp_id"] = cnd.transport_admin_app_rej_by.emp_id if cnd and cnd.transport_admin_app_rej_by else None
        data[
            "approved_by_name"] = cnd.transport_admin_app_rej_by.full_name if cnd and cnd.transport_admin_app_rej_by else None
        data["updated_by_emp_id"] = instance.updated_by.emp_id if instance.updated_by else None
        data["updated_by_name"] = instance.updated_by.full_name if instance.updated_by else None
        data["approved_status"] = instance.candidate.transport_approval_status if instance.candidate else None
        data["approved_comment"] = instance.candidate.transport_approval_comment if instance.candidate else None
        return data

    class Meta:
        model = CabDetail
        fields = "__all__"


class CabAddressDetailUpdateSerializer(ModelSerializer):
    class Meta:
        model = CabDetail
        fields = ['house_no', 'house_apartment_name', 'landmark', 'area', 'address_1', 'address_2', 'state', 'city', 'zip_code']
