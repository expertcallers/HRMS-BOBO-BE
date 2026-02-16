import json

from utils.utils import get_formatted_name, get_process
from .models import *
from rest_framework import serializers


def get_cur_process(cur_proc):
    return ",".join(proc.name for proc in cur_proc.all()) if cur_proc.count() > 0 else None


class CreateIJPSerializer(serializers.ModelSerializer):
    class Meta:
        model = IJP
        exclude = ["created_by", "closed_by", "is_ijp_open", "created_at", "updated_at","selection_process","selection_criteria"]


class OpenIJPSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['designation'] = instance.designation.name
        data['department'] = instance.department.name if instance.department else None
        data['process'] = instance.process.name
        return data

    class Meta:
        model = IJP
        fields = ["contact_profile", "last_date_to_apply", "id"]


class ViewIJPSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['designation'] = instance.designation.name
        data['department'] = instance.department.name if instance.department else None
        data['process'] = instance.process.name
        data['created_by'] = instance.created_by.full_name if instance.created_by else None
        data['closed_by_emp_id'] = instance.closed_by.emp_id if instance.closed_by else None
        data['closed_by_name'] = instance.closed_by.full_name if instance.closed_by else None
        applied_ijp_candidates = IJPCandidate.objects.filter(ijp_applied=instance.id)
        data["no_of_applications"] = applied_ijp_candidates.count() if applied_ijp_candidates else None
        data["selection_criteria"]=json.loads(instance.selection_criteria)
        data["selection_process"]=json.loads(instance.selection_process)
        return data

    class Meta:
        model = IJP
        exclude = ["closed_by"]


class ViewIJPCandidateSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["profile"] = instance.profile.full_name
        data["current_designation"] = instance.profile.designation.name
        data["current_process"] = instance.current_process.name
        data["designation_applied"] = instance.ijp_applied.designation.name
        data["process_applied"] = instance.ijp_applied.process.name
        data["ijp_applied"] = instance.ijp_applied.designation.name + " - " + instance.ijp_applied.process.name
        return data

    class Meta:
        model = IJPCandidate
        fields = '__all__'


class ApplyIJPSerializer(serializers.ModelSerializer):
    class Meta:
        model = IJPCandidate
        fields = ["profile", "ijp_applied", "current_process", "contact_number", "alternate_contact_number", "id"]


class ViewAllApplicationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_name"] = instance.profile.full_name
        data["emp_id"] = instance.profile.emp_id
        data["ijp_applied"] = instance.ijp_applied.designation.name + " - " + instance.ijp_applied.process.name
        data["designation"] = instance.profile.designation.name if instance.profile.designation else None
        data[
            "department"] = instance.profile.designation.department.name if instance.profile.designation.department else None
        data["current_process"] = instance.current_process.name
        return data

    class Meta:
        model = IJPCandidate
        exclude = ["profile", "disciplinary_status", "attendance_count", "current_round", "applied_at",
                   "updated_at"]


class ApprovalStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = IJP
        fields = ["id", "approval_status"]


class ChangeCandidateStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = IJPCandidate
        fields = ["status", "comments", "id"]
