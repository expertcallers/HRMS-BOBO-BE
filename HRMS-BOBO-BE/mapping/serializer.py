from django.conf import settings
from rest_framework import serializers
from datetime import datetime

from ams.models import LeaveBalance
from mapping.models import Profile, HrmsPermissionGroup, EmployeeReferral, Designation, Mapping, LoginOtp, Department, \
    Category
from team.models import Process, Team
from utils.utils import get_formatted_name, get_decrypted_name, form_module_url, hash_value, get_formatted_date, \
    format_partial_salary_information
import logging

logger = logging.getLogger(__name__)


def form_document_url(doc_id):
    return form_module_url(doc_id, "onboard")


def get_path_and_name_dict(obj):
    if not obj:
        return None
    return {"path": form_document_url(obj.id), "name": obj.file.name.split("/")[::-1][0]}


class LoginOtpSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginOtp
        fields = "__all__"


class CreateProfileSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['team'] = instance.team.name
        data['base_team'] = instance.team.base_team.name
        return data

    class Meta:
        model = Profile
        fields = ['first_name', 'middle_name', 'last_name', 'designation', 'emp_id',
                  'username', 'email', 'team', "date_of_joining", "dob", "full_name"]

        extra_kwargs = {
            'department': {'error_messages': {'required': 'Please provide the department info'}},
            'designation': {'error_messages': {'required': 'Please provide the designation info'}},
        }


class UpdateEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["first_name", "middle_name", "last_name", "status", "designation", "full_name"]


class GetBirthdaySerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["department"] = instance.designation.department.name
        data["designation"] = instance.designation.name
        data['base_team'] = instance.team.base_team.name if instance.team and instance.team.base_team else None
        return data

    class Meta:
        model = Profile
        fields = ["full_name", "dob", "emp_id"]


class GetAllProfileSerializer(serializers.ModelSerializer):

    def combine_add(self, onboard):
        if onboard and (onboard.prmnt_address_1 or onboard.prmnt_address_2):
            return onboard.prmnt_address_1 or "" + " " + onboard.prmnt_address_2 or "" + " " + onboard.prmnt_city or "" + " " + onboard.prmnt_state or "" + " " + onboard.prmnt_zip_code or ""
        return None

    def to_representation(self, obj):
        data = super(GetAllProfileSerializer, self).to_representation(obj)
        ob = obj.onboard
        cd = ob.candidate if ob else None
        data['image'] = settings.MEDIA_URL + str(obj.image) if str(obj.image) else ""
        data['team'] = obj.team.name if obj.team else None
        data['base_team'] = obj.team.base_team.name if obj.team and obj.team.base_team else None
        data["onboard_id"] = ob.id if ob else None
        data["candidate_id"] = hash_value(cd.id, 'cd') if cd else None
        desi = obj.designation
        data["department"] = desi.department.name if desi and desi.department else None
        data["designation"] = desi.name if desi else None
        data["dob_month"] = obj.dob.month if obj.dob else None
        data["gender"] = ob.gender if ob else None
        data[
            "erf_id"] = cd.current_application.position_applied.id if cd and cd.current_application and cd.current_application.position_applied else None
        data["contact_no"] = cd.mobile if cd else None
        data["address"] = ob.permanent_address if ob and ob.permanent_address else self.combine_add(ob)
        data["aadhaar_no"] = get_decrypted_name(ob.aadhaar_no) if ob else None
        data["pan_no"] = get_decrypted_name(ob.pan_no) if ob else None
        rm1 = obj.team.manager if obj.team and obj.team.manager else None
        rm2 = rm1.team.manager if rm1 and rm1.team and rm1.team.manager else None
        rm3 = rm2.team.manager if rm2 and rm2.team and rm2.team.manager else None
        data["rm1_full_name"] = rm1.full_name if rm1 else None
        data["rm1_id"] = rm1.emp_id if rm1 else None
        data["rm2_full_name"] = rm2.full_name if rm2 else None
        data["rm2_id"] = rm2.emp_id if rm2 else None
        data["rm3_full_name"] = rm3.full_name if rm3 else None
        data["rm3_id"] = rm3.emp_id if rm3 else None
        leave_balance = LeaveBalance.objects.filter(profile=obj).last()
        data["sl_balance"] = leave_balance.sick_leaves if leave_balance else 0
        data["pl_balance"] = leave_balance.paid_leaves if leave_balance else 0
        data["total_leave_balance"] = leave_balance.total if leave_balance else 0
        data["highest_qualification"] = cd.highest_qualification if cd else None
        data["languages"] = cd.languages if cd else None
        data["marital_status"] = ob.marital_status if ob else None
        data["emergency_contact_name"] = ob.emergency_contact_name if ob else None
        data["emergency_contact_relation"] = ob.emergency_contact_relation if ob else None
        data["emergency_contact_1"] = ob.emergency_contact_1 if ob else None
        data["emergency_contact_2"] = ob.emergency_contact_2 if ob else None
        data["blood_group"] = ob.blood_group if ob else None
        return data

    class Meta:
        model = Profile
        fields = ['first_name', "middle_name", "last_name", 'emp_id', 'email', "status", "last_working_day",
                  "date_of_joining", "full_name", "dob"]


class GetMyTeamSerializer(serializers.ModelSerializer):

    def to_representation(self, obj):
        data = super(GetMyTeamSerializer, self).to_representation(obj)
        data['team'] = obj.team.name if obj.team else None
        data['base_team'] = obj.team.base_team.name if obj.team and obj.team.base_team else None
        mapping_exist = Mapping.objects.filter(employee=obj, status="Pending")
        data["mapping_in_progress"] = True if mapping_exist else False
        return data

    class Meta:
        model = Profile
        fields = ['first_name', "middle_name", "last_name", "full_name", 'emp_id', 'email']


def get_onboard_details(data, onboard):
    onboard_fields = ["marital_status", "emergency_contact_1",
                      "emergency_contact_relation", "emergency_contact_name", "permanent_address", "temporary_address",
                      "blood_group", "father_name", "mother_name", "spouse_name", "uan", "esic_no", "pf_no", "branch",
                      "pan_no", "prmnt_address_1", "prmnt_address_2", "prmnt_state", "prmnt_city", "prmnt_zip_code",
                      "tmp_address_1", "tmp_address_2", "tmp_state", "tmp_city", "tmp_zip_code"]
    if onboard:
        for field in onboard_fields:
            try:
                data[field] = getattr(onboard, field)
            except Exception as e:
                logger.info("field doesn't exist {0} in onboard".format(field))
        data["pan_no"] = get_decrypted_name(data.get("pan_no"))
    return data


def get_candidate_details(data, onboard):
    candidate = onboard.candidate if onboard else None
    dob = onboard.candidate.dob if onboard and onboard.candidate else None
    data["highest_qualification"] = candidate.highest_qualification if candidate else None
    data["fields_of_experience"] = candidate.fields_of_experience if candidate else None
    data["gender"] = candidate.gender if candidate else None
    data["mobile"] = candidate.mobile if candidate else None
    data["mobile_alt"] = candidate.mobile_alt if candidate else None
    data["languages"] = candidate.languages if candidate else None
    data["aadhaar_no"] = get_decrypted_name(candidate.aadhaar_no) if candidate else None
    data['dob'] = str(dob) if dob else None

    return data


class GetProfileSerializer(serializers.ModelSerializer):
    def to_representation(self, obj):
        data = super(GetProfileSerializer, self).to_representation(obj)
        data['image'] = settings.MEDIA_URL + str(obj.image) if str(obj.image) else ""
        data['team'] = obj.team.name
        data["manager"] = obj.team.manager.full_name
        data["department"] = obj.designation.department.name
        data["process"] = obj.team.base_team.name if obj.team and obj.team.base_team else None
        data["designation"] = obj.designation.name
        data["health_card"] = get_path_and_name_dict(
            obj.onboard.health_card) if obj.onboard and obj.onboard.health_card else None
        data = get_onboard_details(data, obj.onboard)
        data = get_candidate_details(data, obj.onboard)
        salary = obj.onboard.salary if obj.onboard and obj.onboard.salary else None
        if salary:
            data = format_partial_salary_information(data, salary, obj)
        # data['date_of_joining'] = "{0}-{1}-{2}".format(date_of_joining.year, date_of_joining.month,
        #                                                date_of_joining.day) if date_of_joining else None

        return data

    class Meta:
        model = Profile
        fields = ["first_name", "middle_name", "last_name", 'emp_id', "email", "status", "erf", "date_of_joining",
                  "full_name", "dob"]


class HrmsGroupSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = HrmsPermissionGroup
        fields = ['permissions']

    def get_permissions(self, obj):
        return [i.url_name for i in obj.permissions.all()]


class CreateEmployeeReferral(serializers.ModelSerializer):
    class Meta:
        model = EmployeeReferral
        fields = ['name', 'email', 'phone_no', 'referred_by_emp']


class GetEmployeeReferralSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['referred_by_emp'] = instance.referred_by_emp.emp_id
        data['referred_emp'] = instance.referred_emp.emp_id if instance.referred_emp else None
        data['referred_by_emp_name'] = instance.referred_by_emp.full_name if instance.referred_by_emp else None
        data['referred_emp_name'] = instance.referred_emp.full_name if instance.referred_emp else None
        return data

    class Meta:
        model = EmployeeReferral
        exclude = ('updated_by',)


class UpdateEmployeeReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeReferral
        fields = ['comment', 'is_open', "amount"]


class EmployeeRefListSerializer(UpdateEmployeeReferralSerializer):
    def to_representation(self, instance):
        return [instance.id, str(instance.referred_by_emp.emp_id) + " - " + str(instance.email)]


class CreateDesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ["name", "department", "category"]


class CreateProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Process
        fields = ["name", "department"]


class CreateMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mapping
        fields = ["employee", "from_team", "to_team", "is_open", "created_by"]


class GetAllMappingSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["from_team"] = instance.from_team.name
        data["to_team"] = instance.to_team.name
        data["to_team_manager_emp_id"] = instance.to_team.manager.emp_id
        data["to_team_manager_name"] = instance.to_team.manager.full_name
        data["employee_emp_id"] = instance.employee.emp_id
        data["employee_name"] = instance.employee.full_name
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        data["approved_by_emp_id"] = instance.approved_by.emp_id if instance.approved_by else None
        data["approved_by_name"] = instance.approved_by.full_name if instance.approved_by else None
        return data

    class Meta:
        model = Mapping
        exclude = ("employee", "approved_by")


class ApproveMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mapping
        fields = ["status", "approved_by", "is_open"]


class QMSProfileSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["emp_name"] = instance.full_name if instance.full_name else None
        data["emp_desi"] = instance.designation.name

        data["emp_rm1"] = instance.team.manager.full_name if instance.team.manager else None
        data["emp_rm1_id"] = instance.team.manager.emp_id if instance.team.manager else None
        data[
            "emp_rm2"] = instance.team.manager.team.manager.full_name if instance.team.manager and instance.team.manager.team.manager else None
        data[
            "emp_rm2_id"] = instance.team.manager.team.manager.emp_id if instance.team.manager and instance.team.manager.team.manager else None
        data[
            "emp_rm3"] = instance.team.manager.team.manager.team.manager.full_name if instance.team.manager and instance.team.manager.team.manager and instance.team.manager.team.manager.team.manager else None
        data[
            "emp_rm3_id"] = instance.team.manager.team.manager.team.manager.emp_id if instance.team.manager and instance.team.manager.team.manager and instance.team.manager.team.manager.team.manager else None
        data["agent_status"] = instance.status
        data["emp_email"] = instance.email if instance.email else None
        data["doj"] = get_formatted_date(instance.date_of_joining) if instance.date_of_joining else None
        data["emp_process"] = instance.team.base_team.name if instance.team else None
        data["emp_process_id"] = instance.team.base_team.id if instance.team else None
        return data

    class Meta:
        model = Profile
        fields = ['emp_id', 'last_working_day']


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model=Department
        exclude=["created_at","updated_at"]
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model=Category
        fields="__all__"

class DesignationSerializer(serializers.ModelSerializer):

    class Meta:
        model=Designation
        exclude=["created_at","updated_at"]


class ProcessSerializer(serializers.ModelSerializer):


    class Meta:
        model=Process
        exclude=["created_at","updated_at","has_report"]

class TeamSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["process"]=instance.base_team.id
        return data

    class Meta:
        model=Team
        exclude=["created_at","updated_at","base_team"]

class QMS3ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        fields=['id','dob','first_name','middle_name','last_name','full_name','email','date_of_joining','location',
                'designation','emp_id','status','my_team','team','sudo_team','last_working_day','username','updated_by','is_active']
