from rest_framework import serializers

from erf.models import ERF, ERFHistory
from utils.utils import get_formatted_name


def return_erf_response(data, instance):
    data['created_by_emp_id'] = instance.created_by.emp_id if instance.created_by else None
    data['created_by_name'] = instance.created_by.full_name if instance.created_by else None
    data['process'] = instance.process.name if instance.process else None
    data["department"] = instance.designation.department.name if instance.designation else None
    data["designation"] = instance.designation.name if instance.designation else None
    data["closed_by_emp_id"] = instance.closed_by.emp_id if instance.closed_by else None
    data["closed_by_name"] = instance.closed_by.full_name if instance.closed_by else None
    data['approved_or_rejected_by'] = \
        instance.approved_or_rejected_by.emp_id if instance.approved_or_rejected_by else None
    return data


class ERFSerializer(serializers.ModelSerializer):
    class Meta:
        model = ERF
        exclude = (
            ['approved_or_rejected_by', 'approval_status', "no_of_rounds", 'requisition_date', 'created_by', 'profiles',
             'closed_by', 'closure_date', 'created_at', 'updated_at', 'is_erf_open', 'test'])


class GetAllERFSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super(GetAllERFSerializer, self).to_representation(instance)
        data['current_hc_req'] = instance.profiles.count()
        data["has_test"] = True if instance.test.all().count() > 0 else False
        return return_erf_response(data, instance)

    class Meta:
        model = ERF
        fields = ['requisition_date', 'hc_req', 'salary_range_frm', 'salary_range_to', 'requisition_type', 'deadline',
                  'approval_status', 'id', 'closure_date', "is_erf_open", "years_of_experience"]


class ErfApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ERF
        fields = ["approval_status", "id"]


class GetERFSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super(GetERFSerializer, self).to_representation(instance)
        data['current_hc_req'] = instance.profiles.count()
        data["tests"] = "; ".join(i.test_name for i in instance.test.all())
        return return_erf_response(data, instance)

    class Meta:
        model = ERF
        exclude = ["profiles"]


class OpenERFSerializer(serializers.ModelSerializer):

    def to_representation(self, obj):
        return [obj.id, str(obj.id) + "-" + str(obj.designation.name) + "-" + str(obj.process.name) + "-" + " (" + str(
            obj.designation.department.name) + ")"]

    class Meta:
        model = ERF
        fields = ['designation']


class GetErfHistorySerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['emp_id'] = instance.profile.emp_id
        data["emp_name"] = instance.profile.full_name
        data["added_or_removed_by_emp_id"] = instance.added_or_removed_by.emp_id
        data["added_or_removed_by_name"] = instance.added_or_removed_by.full_name
        return data

    class Meta:
        model = ERFHistory
        exclude = ('profile', 'added_or_removed_by', 'erf')
