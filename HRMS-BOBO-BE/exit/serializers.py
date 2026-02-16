from rest_framework import serializers
from .models import Resignation, ResignationHistory, ExitFeedbackInterview, ExitChecklist, FinalApprovalChecklist
from utils.utils import get_formatted_name, get_formatted_date


class CreateResignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resignation
        fields = ['resignation_message', 'applied_by', 'start_date']


class ViewResignationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["applied_by_emp_id"] = instance.applied_by.emp_id
        data["applied_by_name"] = instance.applied_by.full_name
        data["applied_by_designation"] = instance.applied_by.designation.name
        data["applied_by_process"] = instance.applied_by.team.base_team.name
        data[
            "accepted_or_rejected_by_emp_id"] = instance.accepted_or_rejected_by.emp_id \
            if instance.accepted_or_rejected_by else None
        data[
            "accepted_or_rejected_by_name"] = instance.accepted_or_rejected_by.full_name if instance.accepted_or_rejected_by else None
        data[
            "hr_accepted_or_rejected_by_emp_id"] = instance.hr_accepted_or_rejected_by.emp_id \
            if instance.hr_accepted_or_rejected_by else None
        data[
            "hr_accepted_or_rejected_by_name"] = instance.hr_accepted_or_rejected_by.full_name if instance.hr_accepted_or_rejected_by else None
        exit_feedback = ExitFeedbackInterview.objects.filter(resignation=instance.id).last()
        data["exit_interview_attempted"] = True if exit_feedback else False
        return data

    class Meta:
        model = Resignation
        exclude = ['notice_period_extended_or_reduced_by', 'notice_period_extended_or_reduced_comments',
                   'notice_period_extended_or_reduced_at', 'applied_by', 'accepted_or_rejected_by',
                   'is_notice_period_reduced', 'withdrawal_comments', 'hr_accepted_or_rejected_by']


class ResignationStatusSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["applied_by_emp_id"] = instance.applied_by.emp_id
        data["applied_by_name"] = instance.applied_by.full_name
        data[
            "accepted_or_rejected_by_emp_id"] = instance.accepted_or_rejected_by.emp_id \
            if instance.accepted_or_rejected_by else None
        data[
            "accepted_or_rejected_by_name"] = instance.accepted_or_rejected_by.full_name if instance.accepted_or_rejected_by else None
        data[
            "hr_accepted_or_rejected_by_emp_id"] = instance.hr_accepted_or_rejected_by.emp_id \
            if instance.hr_accepted_or_rejected_by else None
        data[
            "hr_accepted_or_rejected_by_name"] = instance.hr_accepted_or_rejected_by.full_name if instance.hr_accepted_or_rejected_by else None
        exit_feedback = ExitFeedbackInterview.objects.filter(resignation=instance.id).last()
        data["exit_interview_attempted"] = True if exit_feedback else False
        return data

    class Meta:
        model = Resignation
        fields = ['id', 'resignation_status', 'applied_at', 'notice_period_in_days', 'start_date', 'exit_date',
                  'it_team_approval', 'it_team_comments', 'hr_team_approval', 'hr_team_comments', 'admin_team_approval',
                  'admin_team_comments', 'knowledge_transfer', 'withdrawal_comments', 'dept_approval',
                  'dept_approval_comments', 'accepted_or_rejected_comment', 'accepted_or_rejected_at',
                  'hr_accepted_or_rejected_comment', 'hr_accepted_or_rejected_at', 'resignation_message', 'updated_at']


class ApproveResignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resignation
        fields = ['resignation_status', 'accepted_or_rejected_by', 'accepted_or_rejected_comment']


class HRApproveResignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resignation
        fields = ['resignation_status', 'hr_accepted_or_rejected_by', 'hr_accepted_or_rejected_comment']


class UpdateNoticePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resignation
        fields = ['notice_period_extended_or_reduced_by', 'notice_period_extended_or_reduced_comments', 'exit_date']


class ResignationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResignationHistory
        fields = '__all__'


class SubmitExitFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitFeedbackInterview
        fields = '__all__'


class ViewExitFeedbackSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["name"] = instance.resignation.applied_by.full_name
        data["department"] = instance.resignation.applied_by.designation.department.name
        data["designation"] = instance.resignation.applied_by.designation.name
        data["exit_date"] = get_formatted_date(instance.resignation.exit_date)
        return data

    class Meta:
        model = ExitFeedbackInterview
        fields = '__all__'


class ExitChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitChecklist
        fields = '__all__'


class FinalApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinalApprovalChecklist
        fields = '__all__'


class ViewApprovalSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        resign_id = self.context.get('resign_id')
        resign_obj = Resignation.objects.filter(id=resign_id).last()
        due_status_obj = FinalApprovalChecklist.objects.filter(resignation=resign_id, checklist=instance.id).last()
        data["dept"] = instance.dept.id if instance.dept else resign_obj.applied_by.designation.department.id
        data["dept_ques"] = False if instance.dept else True
        data["due_status"] = due_status_obj.due_status if due_status_obj else "Not Attempted"
        data["approved_by_emp_id"] = due_status_obj.approved_by.emp_id if due_status_obj else None
        data["approved_by_name"] = due_status_obj.approved_by.full_name if due_status_obj else None
        return data

    class Meta:
        model = ExitChecklist
        exclude = ["dept"]
