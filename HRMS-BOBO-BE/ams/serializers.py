import logging
from datetime import datetime

from rest_framework import serializers

from ams.models import Attendance, Leave, LeaveBalanceHistory, AttendanceCorrectionHistory, Schedule, LeaveBalance, \
    Break, AttendanceLog
from hrms import settings
from mapping.models import Profile
from utils.utils import hash_value, get_formatted_name, tz, convert_seconds, get_hour_min_second_format
from django.utils import timezone

logger = logging.getLogger(__name__)


class ApproveAttendanceSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super(ApproveAttendanceSerializer, self).to_representation(instance)
        data['id'] = hash_value(instance.id, 'attendance')
        data["emp_id"] = instance.profile.emp_id
        return data

    class Meta:
        model = Attendance
        fields = ["date"]


class AttendanceSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super(AttendanceSerializer, self).to_representation(instance)
        data['id'] = hash_value(instance.id, 'attendance')
        data["emp_id"] = instance.profile.emp_id
        return data

    class Meta:
        model = Attendance
        fields = ["date", "status"]


class GetAttendanceScheduleSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super(GetAttendanceScheduleSerializer, self).to_representation(instance)
        profile = instance.profile
        data['id'] = hash_value(instance.id, 'attendance')
        data['emp_name'] = profile.full_name
        data["emp_id"] = profile.emp_id
        data["manager_emp_id"] = profile.team.manager.emp_id if profile.team and profile.team.manager else None
        data["manager_name"] = profile.team.manager.full_name if profile.team and profile.team.manager else None
        data["team"] = profile.team.name if profile.team else None
        data["base_team"] = profile.team.base_team.name if profile.team else None
        data["sch_upd_by_emp_id"] = instance.sch_upd_by.emp_id if instance.sch_upd_by else None
        data["sch_upd_by_name"] = instance.sch_upd_by.full_name if instance.sch_upd_by else None
        data["approved_by_name"] = instance.approved_by.full_name if instance.approved_by else None
        data["approved_by_emp_id"] = instance.approved_by.emp_id if instance.approved_by else None
        return data

    class Meta:
        model = Attendance
        exclude = ("profile", "sch_upd_by", "logged_in_ip", "logged_out_by")


class CreateLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leave
        fields = ["start_date", "end_date", "reason", "leave_type", "profile"]


class LeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leave
        fields = ["id", "start_date", "end_date", "applied_on", "no_of_days", "reason", "leave_type",
                  "manager_status", "manager_comments", "tl_status", "tl_comments",
                  "status"]


class ApproveLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leave
        fields = ["status"]


class GetAllAppliedLeaveSerializer(LeaveSerializer):
    def to_representation(self, instance):
        data = super(GetAllAppliedLeaveSerializer, self).to_representation(instance)
        data["emp_name"] = instance.profile.full_name
        data["emp_id"] = instance.profile.emp_id
        rm1 = instance.profile.team.manager if instance.profile.team else None
        data["tl_name"] = rm1.full_name if rm1 else None
        data["tl_emp_id"] = rm1.emp_id if rm1 else None
        data["manager_name"] = rm1.team.manager.full_name if rm1 and rm1.team.manager else None
        data["manager_emp_id"] = rm1.team.manager.emp_id if rm1 and rm1.team.manager else None
        return data


class GetAllLeaveBalanceHistorySerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_id"] = instance.profile.emp_id
        data["emp_name"] = instance.profile.full_name
        data["sl_balance"] = round(instance.sl_balance, 2) if instance.sl_balance else 0
        data["pl_balance"] = round(instance.pl_balance, 2) if instance.pl_balance else 0
        data["no_of_days"] = round(instance.no_of_days, 2) if instance.no_of_days else 0
        data["total"] = round(instance.total, 2) if instance.total else 0
        return data

    class Meta:
        model = LeaveBalanceHistory
        fields = "__all__"


class CreateAttendanceScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["start_time", "end_time"]


class RequestForAttendanceCorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["date", "status", "is_training"]


class GetAllAttCorRequestSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        attendance = instance.attendance
        data["emp_id"] = attendance.profile.emp_id
        data["emp_name"] = attendance.profile.full_name
        data["date"] = attendance.date
        data["current_status"] = attendance.status

        data["att_cor_req_by_emp_id"] = instance.att_cor_req_by.emp_id
        data["att_cor_req_by_name"] = instance.att_cor_req_by.full_name
        to_be_approved_by = instance.att_cor_req_by.team.manager if instance.att_cor_req_by.team and instance.att_cor_req_by.team.manager else None
        data["to_be_approved_by_name"] = to_be_approved_by.full_name if to_be_approved_by else None
        data["to_be_approved_by_emp_id"] = to_be_approved_by.emp_id if to_be_approved_by else None
        data["approved_by_emp_id"] = instance.approved_by.emp_id if instance.approved_by else None
        data["approved_by_name"] = instance.approved_by.full_name if instance.approved_by else None
        return data

    class Meta:
        model = AttendanceCorrectionHistory
        exclude = ("attendance", "approved_by", "att_cor_req_by")


class ApproveAttendanceCorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceCorrectionHistory
        fields = ["id", "approved_comment", "correction_status"]


class RequestForScheduleCorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["status", "comment", "date", "start_time", "end_time", 'is_training']


class GetAllLeaveBalanceSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['emp_name'] = instance.profile.full_name
        data["emp_id"] = instance.profile.emp_id
        return data

    class Meta:
        model = LeaveBalance
        exclude = ("profile",)


class GetLeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ["sick_leaves", "paid_leaves", "total"]


class BreakSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_name"] = instance.profile.full_name
        data["emp_id"] = instance.profile.emp_id
        return data

    class Meta:
        model = Break
        fields = '__all__'


class CheckInCheckOutSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_id"] = instance.profile.emp_id
        data["process"] = instance.profile.team.base_team.name
        # data["emp_start_time"] = str(instance.emp_start_time) if instance.emp_start_time else None
        # data["emp_end_time"] = str(instance.emp_end_time) if instance.emp_end_time else None

        return data

    class Meta:
        model = Attendance
        fields = ["emp_start_time", "emp_end_time", "date"]


class ConsolidatedBreakSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = {}
        for key in instance:
            value = instance[key]
            if str(key).endswith("start_time") or str(key).endswith("end_time"):
                # dt_value = timezone.make_aware(value, settings.TIME_ZONE)
                data[key] = timezone.localtime(value, timezone.get_current_timezone()).isoformat() if value else None
            elif str(key).endswith("comment"):
                data[key] = value
        data["break_1"] = convert_seconds(
            (instance["break1_end_time"] - instance["break1_start_time"]).total_seconds()) if instance[
            "break1_end_time"] else None
        data["break_2"] = convert_seconds(
            (instance["break2_end_time"] - instance["break2_start_time"]).total_seconds()) if instance[
            "break2_end_time"] else None
        data["break_3"] = convert_seconds(
            (instance["break3_end_time"] - instance["break3_start_time"]).total_seconds()) if instance[
            "break3_end_time"] else None
        data["total_break_time"] = convert_seconds(instance["total_break_time"].total_seconds())
        data["bio"] = convert_seconds(instance["bio"].total_seconds())
        data["team_huddle"] = convert_seconds(instance["team_huddle"].total_seconds())
        data["other"] = convert_seconds(instance["other"].total_seconds())
        data["emp_id"] = instance["profile__emp_id"]
        data["emp_name"] = instance["profile__full_name"]
        data["date"] = instance["attendance__date"]
        data["rm1_name"] = instance["profile__team__manager__full_name"]
        data["rm1_emp_id"] = instance["profile__team__manager__emp_id"]
        data["process"] = instance["profile__team__base_team__name"]

        return data

    class Meta:
        model = Break
        fields = ["id"]



class AttendanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model=AttendanceLog
        exclude=['id']

# To create Checkin Checkout
class BulkRangeAttendanceUpdateSerializer(serializers.Serializer):
    emp_ids = serializers.ListField(
        child=serializers.CharField(),  # assuming emp_id is string
        allow_empty=False
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
