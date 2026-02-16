from rest_framework import serializers

from appraisal.models import *


class SearchParameterSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        return [instance.id, instance.name]

    class Meta:
        model = Parameter
        fields = ["id", "name", "score"]


class GetAllEmpAppraisalSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["process"] = instance.employee.team.base_team.name
        data["emp_id"] = instance.employee.emp_id
        data["emp_name"] = instance.employee.full_name
        data["designation"] = instance.employee.designation.name
        return data

    class Meta:
        model = EmpAppraisal
        exclude = ["employee"]


class GetAllEligibleAppraisalListSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["process"] = instance.team.base_team.name
        data["emp_name"] = instance.full_name
        data["designation"] = instance.designation.name
        appraisal = EmpAppraisal.objects.filter(employee=instance, year=datetime.now().year).first()
        data["status"] = "Parameters not added" if appraisal is None else appraisal.status
        return data

    class Meta:
        model = Profile
        fields = ["emp_id"]


class CreatePartDAppraiseeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartD_Appraisee
        exclude = ["appraisee_roles", "appraisee_skills_required", "appraisee_timeframe_from", "appraisee_timeframe_to",
                   "appraisee_comments_feedback", "emp_agree_disagree", "is_emp_agreed"]


class UpdatePartDAppraiseeSerializer(serializers.ModelSerializer):
    appraisee_roles = serializers.CharField(required=True)
    appraisee_skills_required = serializers.CharField(required=True)
    appraisee_timeframe_from = serializers.CharField(required=True)
    appraisee_timeframe_to = serializers.CharField(required=True)
    appraisee_comments_feedback = serializers.CharField(required=True)
    is_emp_agreed = serializers.BooleanField(required=True)
    emp_agree_disagree = serializers.CharField(required=True)

    class Meta:
        model = PartD_Appraisee
        fields = ["appraisee_roles", "appraisee_skills_required", "appraisee_timeframe_from", "appraisee_timeframe_to",
                  "appraisee_comments_feedback", "emp_agree_disagree", "is_emp_agreed"]


class DevtActionRespSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevActResDes
        exclude = ["partd_appraisee", "employee"]


class TrainingTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingTime
        exclude = ["partd_appraisee", "employee"]


class GetPartDAppraiseeSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_name"] = instance.emp_appraisal.employee.full_name
        data["emp_id"] = instance.emp_appraisal.employee.emp_id
        data["dev_act_dev_res"] = DevtActionRespSerializer(DevActResDes.objects.filter(partd_appraisee=instance),
                                                           many=True).data
        data["training_time"] = TrainingTimeSerializer(TrainingTime.objects.filter(partd_appraisee=instance),
                                                       many=True).data

        return data

    class Meta:
        model = PartD_Appraisee
        fields = "__all__"
