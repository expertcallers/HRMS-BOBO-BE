from rest_framework import serializers

from ams.models import Attendance
from ijp.serializers import get_process
from mapping.models import Profile
from payroll.models import Payroll, Deduction, VariablePay, Salary

from datetime import date, datetime, timedelta

from utils.utils import get_formatted_name, get_decrypted_name, get_decrypted_value, decrypt_obj, \
    format_partial_salary_information


class CreatePayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = "__all__"


class AddDeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deduction
        fields = "__all__"


class AddVariablePaySerializer(serializers.ModelSerializer):
    class Meta:
        model = VariablePay
        exclude = ("attendance_bonus", "status")


class GetEcplPayrollSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):

        data = super().to_representation(instance)
        int_cols = ["fixed_gross", "new_basic_salary", "new_da", "new_oa", "new_ta",
                    "basic", "da", "new_qa", "ta", "b_plus_d", "total_fixed_gross",
                    "pay_check", "present", "wo", "el", "sl", "cl", "ml", "trng", "hd", "nh", "absent", "att",
                    "na", "total_days", "calendar_days", "paid_days", "lop_days", "el_accrual", "pf_gross",
                    "statutory_bonus", "variable_pay", "process_incentive",
                    "client_incentive", "bb_rent", "overtime", "night_shift_allowance", "referral", "arrears",
                    "attendance_bonus", "total_gross_salary", "pf_emp", "pf_emr", "esi", "pt", "tds",
                    "cab_deduction", "other_deduction", "notice_period_recovery", "total_ded", "net_salary"]
        for key in data:
            if key in int_cols:
                data[key] = int(data[key])

        return data

    class Meta:
        model = Payroll
        exclude = ("profile",)


class GetPayrollSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        profile = instance.profile
        onboard = profile.onboard if profile.onboard else None
        salary = onboard.salary if onboard else None
        data["status"] = profile.status
        data["gender"] = onboard.candidate.gender if onboard and onboard.candidate else None
        data["doj"] = profile.date_of_joining
        data["branch"] = onboard.branch if onboard else None
        data["process"] = profile.team.base_team.name if profile.team else None
        data["designation"] = profile.designation.name if profile.designation else None
        data["department"] = profile.designation.department.name if profile.designation else None
        data["lwd"] = profile.last_working_day
        data = format_partial_salary_information(data, salary, profile)
        return data

    class Meta:
        model = Payroll
        exclude = ("profile",)


class GetDeductionSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_id"] = instance.profile.emp_id
        data["emp_name"] = instance.profile.full_name
        data["created_by_emp_id"] = instance.created_by.emp_id
        data["created_by_name"] = instance.created_by.full_name
        data["updated_by_emp_id"] = instance.updated_by.emp_id if instance.updated_by else None
        data["updated_by_name"] = instance.updated_by.full_name if instance.updated_by else None
        return data

    class Meta:
        model = Deduction
        exclude = ("profile",)


class GetVariablePaySerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_name"] = instance.profile.full_name if instance.profile else None
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["updated_by_emp_id"] = instance.updated_by.emp_id if instance.updated_by else None
        data["updated_by_name"] = instance.updated_by.full_name if instance.updated_by else None
        data["app_or_reg_by_emp_id"] = instance.app_or_reg_by.emp_id if instance.app_or_reg_by else None
        data["app_or_reg_by_name"] = instance.app_or_reg_by.full_name if instance.app_or_reg_by else None
        return data

    class Meta:
        model = VariablePay
        exclude = ("profile",)


class UploadPayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        exclude = ['created_at', 'updated_at', 'profile']


class GetSalarySerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data = format_partial_salary_information(data, instance, instance.profile)
        updated_by = instance.updated_by
        data['updated_by_emp_id'] = updated_by.emp_id if updated_by else None
        data['updated_by_name'] = updated_by.full_name if updated_by else None
        data = decrypt_obj(Salary, data, instance)
        data["emp_status"] = instance.profile.status if instance.profile else None
        return data

    class Meta:
        model = Salary
        fields = "__all__"


class UpdateSalarySerializer(serializers.ModelSerializer):
    opting_for_pf = serializers.BooleanField(required=True,
                                             error_messages={"null": "Please provide 0 or 1 for opting_for_pf"})

    class Meta:
        model = Salary
        exclude = ["account_number", "created_at", "updated_at"]
