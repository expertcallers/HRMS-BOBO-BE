import json
import traceback
from datetime import datetime, timedelta
import logging

from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import authentication_classes, api_view, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from datetime import datetime, date
from ams.models import Attendance
from hrms import settings
from mapping.models import Profile, EmployeeReferral
from mapping.views import HasUrlPermission
from onboarding.views import get_onboard_by_id
from payroll.models import Payroll, Deduction, VariablePay, UpdateSalaryHistory, PayGrade, Salary
from payroll.serializers import CreatePayrollSerializer, GetPayrollSerializer, AddDeductionSerializer, \
    AddVariablePaySerializer, GetVariablePaySerializer, GetDeductionSerializer, GetEcplPayrollSerializer, \
    UploadPayrollSerializer, UpdateSalarySerializer, GetSalarySerializer
from utils.util_classes import CustomTokenAuthentication
from utils.utils import update_request, return_error_response, get_sort_and_filter_by_cols, read_file_format_output, tz, \
    get_team_ids, get_selected_emp_under_team, is_management, get_column_names_with_foreign_keys_separate, \
    parse_boolean_value, calc_pf, calc_esi, get_decrypted_value, update_salary_history

logger = logging.getLogger(__name__)


def get_emp_by_emp_id(emp_id):
    try:
        emp = Profile.objects.get(emp_id=emp_id)
    except Exception as e:
        raise ValueError("employee doesn't exist with emp_id {0}".format(emp_id))
    return emp


def get_prev_month_attendance_info(data, profile):
    # today = datetime.today()

    prev_month_last_day = datetime.today().replace(day=1) - timedelta(days=1)
    start_day = prev_month_last_day.replace(day=1)
    attendance = Attendance.objects.filter(profile=profile, date__gte=start_day.date(),
                                           date__lte=prev_month_last_day.date()).order_by('date')

    last_month_reverse = Attendance.objects.filter(profile=profile, date__gte=start_day - timedelta(days=31),
                                                   date__lte=start_day).order_by("-date")
    last_prev_absent = False

    for prev_day in last_month_reverse:
        if prev_day.status == "Absent":
            last_prev_absent = True
            break
        elif prev_day.status == "Week Off":
            continue
        else:
            break
    sandwich_days = set()
    for attend in attendance:
        if attend.status == "Absent":
            last_prev_absent = True
        elif attend.status == "Week Off" and last_prev_absent:
            sandwich_days.add(str(attend.date))
        else:
            last_prev_absent = False
    last_prev_absent = False
    for attend in attendance.order_by('-date'):
        if attend.status == "Absent":
            last_prev_absent = True
            # print("date", attend.date)
        elif attend.status == "Week Off" and last_prev_absent:
            sandwich_days.add(str(attend.date))
        else:
            last_prev_absent = False
    sandwich_days = list(sandwich_days)
    sandwich_days.sort()

    attendance = Attendance.objects.filter(profile=profile, date__gte=start_day.date(),
                                           date__lte=prev_month_last_day.date())
    data["sandwich_count"] = len(sandwich_days)
    data["sandwich_dates"] = ", ".join(str(i) for i in sandwich_days)

    data["year"] = prev_month_last_day.year
    data["month_number"] = prev_month_last_day.month
    data["month"] = prev_month_last_day.strftime("%b")
    data['el'] = attendance.filter(status="PL").count()
    data['sl'] = attendance.filter(status="SL").count()
    data['wo'] = attendance.filter(status="Week Off").count()
    if len(sandwich_days) > 0:
        data['wo'] = data['wo'] - len(sandwich_days)
    data["present"] = attendance.filter(status="Present").count()
    data["cl"] = attendance.filter(status="Client Off").count()
    data['co'] = attendance.filter(status="Comp Off").count()
    data['ml'] = attendance.filter(status="ML").count()
    data["trng"] = attendance.filter(status="Training").count()
    data["hd"] = attendance.filter(status="Half Day").count()
    data["nh"] = attendance.filter(status="NH").count()
    data["absent"] = attendance.filter(status="Absent").count() + len(sandwich_days)
    data["att"] = attendance.filter(status="Attrition").count()
    data["paid_days"] = data["present"] + data['el'] + data['sl'] + data['wo'] + data["co"] + data['cl'] + data[
        "trng"] + (data["hd"] / 2) + data["nh"] + data["ml"]  # TODO verify ML
    data["calender_days"] = prev_month_last_day.day
    data["total_days"] = data["paid_days"] + data["att"] + data["absent"]
    data["lop_days"] = data['calender_days'] - data["paid_days"]
    return data, attendance.filter(date__in=sandwich_days)


def as_per_month(val):
    return round(val / 12, 0)


def calculate_as_per_att(value, data):
    return value / data['calender_days'] * data['paid_days']


def get_emp_by_emp_id(emp_id):
    try:
        profile = Profile.objects.get(emp_id=emp_id)
    except Exception as e:
        raise ValueError("Profile for the given emp_id does not exist")
    return profile


def get_emp_ids(request):
    emp_ids = request.data.get('emp_ids')
    if emp_ids is None or emp_ids == "":
        return None
    return emp_ids.split(",")


def handle_year_month(usr, data, create_objs, update_list, profile, obj, ObjSerializer, v_or_d_type):
    year = datetime.today().year
    month = datetime.today().month
    record = obj.objects.filter(profile=profile, is_active=True, year=year, month=month).last()
    if record:
        raise ValueError("{0} already exists for emp-id {1}, please select updating it".format(
            v_or_d_type.replace("_", " ").capitalize(), profile.emp_id))

        # update_request(data, updated_by=usr.id)
        # serializer = ObjSerializer(data=data, partial=True)
        # if not serializer.is_valid():
        #     return_error_response(serializer, raise_exception=True)
        # for key, value in serializer.validated_data.items():
        #     setattr(record, key, value)
        # if v_or_d_type == "variable_pay":
        #     record = update_variable_pay_total(record)
        #
        # update_list.append(record)
    else:
        update_request(data, year=year, month=month)
        serializer = ObjSerializer(data=data)
        if not serializer.is_valid():
            return_error_response(serializer, raise_exception=True)
        if v_or_d_type == "variable_pay":
            serializer = update_variable_pay_total(serializer)

        create_objs.append(obj(**serializer.validated_data))
    return create_objs, update_list


def handle_create_update_list(request, Obj, ObjSerializer, v_or_d_type):
    usr = request.user
    team = request.data.get('team')
    emp_ids = request.data.get("emp_ids")
    profiles = get_selected_emp_under_team(usr, team, emp_ids)
    create_objs = []
    update_list = []
    model_fields = Obj._meta.get_fields()
    column_names = [field.name for field in model_fields if field.concrete]
    column_names.remove("id")

    for profile in profiles:
        data = update_request(request.data, profile=profile.id, emp_id=profile.emp_id, created_by=usr.id,
                              is_active=True)
        create_objs, update_list = handle_year_month(usr, data, create_objs, update_list, profile, Obj,
                                                     ObjSerializer, v_or_d_type)
    if len(create_objs) > 0:
        Obj.objects.bulk_create(create_objs)
    if len(update_list) > 0:
        Obj.objects.bulk_update(update_list, column_names)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def add_deduction(request):
    try:
        handle_create_update_list(request, Deduction, AddDeductionSerializer, "deduction")
        return HttpResponse(json.dumps({"message": "added deduction info successfully"}))
    except Exception as e:
        logger.info("exception at add_deduction {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def add_variable_pay(request):
    try:
        check_if_variable_pay_accepted()
        handle_create_update_list(request, VariablePay, AddVariablePaySerializer, "variable_pay")
        return HttpResponse(json.dumps({"message": "added Variable pay info successfully"}))
    except Exception as e:
        logger.info("exception at add_variable_pay {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def update_variable_pay_total(variable_pay):
    if isinstance(variable_pay, ModelSerializer):
        variable_pay.validated_data["total"] = int(
            variable_pay.validated_data.get("process_incentive", 0) + variable_pay.validated_data.get(
                "client_incentive", 0) +
            variable_pay.validated_data.get(
                "bb_rent", 0) + variable_pay.validated_data.get("overtime", 0) + variable_pay.validated_data.get(
                "night_shift_allowance", 0) + variable_pay.validated_data.get("arrears",
                                                                              0) + variable_pay.validated_data.get(
                "attendance_bonus", 0))
        return variable_pay
    else:
        variable_pay.total = int(
            variable_pay.process_incentive + variable_pay.client_incentive + variable_pay.bb_rent + variable_pay.overtime + variable_pay.night_shift_allowance + variable_pay.arrears + variable_pay.attendance_bonus)
    return variable_pay


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_variable_pay(request, vid):
    try:
        check_if_variable_pay_accepted()
        usr = request.user
        variable_pay = VariablePay.objects.filter(id=vid).last()
        if variable_pay is None:
            raise ValueError("Invalid variable pay id")
        today = datetime.today()
        if variable_pay.month != today.month:
            raise ValueError("you can update current month variable pay only")
        # if variable_pay.status != "Pending":
        #     raise ValueError(
        #         f"You cannot edit, Variable pay for {variable_pay.profile.emp_id} is already {variable_pay.status}")
        data = update_request(request.data, updated_by=usr.id)
        serializer = AddVariablePaySerializer(data=data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.update(variable_pay, serializer.validated_data)
        variable_pay = update_variable_pay_total(variable_pay)
        variable_pay.save()
        return HttpResponse(json.dumps({"message": "updated Variable pay info successfully"}))
    except Exception as e:
        logger.info("exception at add_variable_pay {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def handle_multi_records(data_list):
    val = 0
    for i in data_list:
        val += i
    return val


def calculate_referral(profile):
    start_day_of_past_3month = datetime.today().date() - timedelta(days=90)
    referred_list = EmployeeReferral.objects.filter(referred_by_emp=profile, is_open=True, status="Employee")
    emp_list = []
    referral_amount = 0
    for emp in referred_list:
        if emp.referred_emp.date_of_joining <= start_day_of_past_3month and emp.amount > 0:
            emp_list.append(emp)
            referral_amount += emp.amount
    return emp_list, referral_amount


def check_and_add_variable_pay_data(profile, data):
    pre_month_last_day = datetime.today().replace(day=1) - timedelta(days=1)
    variable_pay = VariablePay.objects.filter(profile=profile, year=pre_month_last_day.year,
                                              month=pre_month_last_day.month)

    data["process_incentive"] = handle_multi_records(list(variable_pay.values_list("process_incentive", flat=True)))
    data["client_incentive"] = handle_multi_records(list(variable_pay.values_list("client_incentive", flat=True)))
    data["bb_rent"] = handle_multi_records(list(variable_pay.values_list("bb_rent", flat=True)))
    data["overtime"] = handle_multi_records(list(variable_pay.values_list("overtime", flat=True)))
    data["night_shift_allowance"] = handle_multi_records(
        list(variable_pay.values_list("night_shift_allowance", flat=True)))
    referral_emp_list, referred_amount = calculate_referral(profile)
    data["referral"] = referred_amount
    data["arrears"] = handle_multi_records(list(variable_pay.values_list("arrears", flat=True)))
    data["attendance_bonus"] = handle_multi_records(list(variable_pay.values_list("attendance_bonus", flat=True)))
    data["variable_pay"] = data["process_incentive"] + data["client_incentive"] + data["bb_rent"] + data[
        "overtime"] + data["night_shift_allowance"] + data["referral"] + data["arrears"] + data["attendance_bonus"]

    one_time_variable_pay = variable_pay.filter(year=pre_month_last_day.year, month=pre_month_last_day.month)
    return data, referral_emp_list, one_time_variable_pay


def check_and_add_deductions(profile, data):
    pre_month_last_day = datetime.today().replace(day=1) - timedelta(days=1)
    deductions = Deduction.objects.filter(profile=profile, is_active=True).filter(
        Q(is_always=True) | Q(year=pre_month_last_day.year, month=pre_month_last_day.month))

    data["tds"] = handle_multi_records(list(deductions.values_list("tds", flat=True)))
    data["sodexo_deduction"] = handle_multi_records(list(deductions.values_list("sodexo_deduction", flat=True)))
    data["cab_deduction"] = handle_multi_records(list(deductions.values_list("cab_deduction", flat=True)))
    data["other_deduction"] = handle_multi_records(list(deductions.values_list("other_deduction", flat=True)))
    data["notice_period_recovery"] = handle_multi_records(
        list(deductions.values_list("notice_period_recovery", flat=True)))
    data["total_ded"] = round(
        data["pf_emp"] + data['pf_emr'] + data["esi"] + data["tds"] + data["sodexo_deduction"] +
        data["cab_deduction"] + data["other_deduction"] + data["notice_period_recovery"], 0)

    one_time_deductions = deductions.filter(year=pre_month_last_day.year, month=pre_month_last_day.month)
    return data, one_time_deductions


def compute_payroll(salary, profile):
    pay_grade_calc = PayGrade.objects.get(level=salary.pay_grade)
    cols = ["basic", "ta", "oa", "total_fixed_gross", "hra", "tel_allowance", "medical_allowance",
            "health_insurance_deduction", "pt"]
    data = {"profile": profile.id, "emp_id": profile.emp_id, "esic_no": salary.esic_no, "pf_no": salary.pf_no,
            "uan": salary.uan}
    for col in cols:
        data[col] = float(get_decrypted_value(getattr(salary, col)))

    data["b_plus_d"] = data["basic"]
    data, sandwich_days = get_prev_month_attendance_info(data, profile)
    data["el_accrual"] = round(calculate_as_per_att(1.5, data), 2)

    data["new_basic_salary"] = round(calculate_as_per_att(data['basic'], data), 0)
    data["new_hra"] = round(calculate_as_per_att(data["hra"], data), 0)  # TODO get clarified
    data["new_oa"] = round(calculate_as_per_att(data['oa'], data), 0)
    data["new_ta"] = round(calculate_as_per_att(data['ta'], data), 0)
    data["new_medical_a"] = round(calculate_as_per_att(data["medical_allowance"], data), 0)

    data["pf_gross"] = data['new_basic_salary'] + data["new_oa"] + data["new_ta"] + data[
        "new_medical_a"] + data["new_hra"]  # clarified by hemanth
    if data['paid_days'] > 0:
        data["pf_gross"] += data["tel_allowance"]
    data["statutory_bonus"] = 0
    data, referral_emp_list, one_time_variable_pay = check_and_add_variable_pay_data(profile, data)
    data["total_gross_salary"] = data['pf_gross'] + data["tel_allowance"] + data["statutory_bonus"] + data[
        "variable_pay"]
    data["pf_emp"] = 0
    data["pf_emr"] = 0
    if salary.opting_for_pf:
        data["pf_emp"] = round(data["pf_gross"] * (pay_grade_calc.pf_emp_perc / 100), 0) if \
            data["pf_gross"] <= settings.PF_GROSS_LIMIT else settings.PF_FIXED_DEDUCTION_AMOUNT
        data["pf_emr"] = round(data["pf_gross"] * (pay_grade_calc.pf_emr_perc / 100), 0) if \
            data["pf_gross"] <= settings.PF_GROSS_LIMIT else settings.PF_FIXED_DEDUCTION_AMOUNT
    data["esi"] = round(data["total_gross_salary"] * (0.75 / 100), 0) \
        if data["total_fixed_gross"] <= settings.ESI_LIMIT else 0
    data, one_time_deductions = check_and_add_deductions(profile, data)
    data["total_ded"] += data['pt'] if data["total_gross_salary"] >= settings.PF_GROSS_LIMIT else 0
    data["net_salary"] = round(data["total_gross_salary"] - data["total_ded"], 0)

    return data, referral_emp_list, one_time_variable_pay, one_time_deductions, sandwich_days


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def calculate_payroll(request):
    try:
        today = datetime.today().date()
        prev_mon = today.replace(day=1) - timedelta(days=1)
        profiles = Profile.objects.filter(status="Active", is_active=True, date_of_joining__lte=prev_mon)

        for profile in profiles:
            payroll = Payroll.objects.filter(profile=profile, month_number=prev_mon.month, year=prev_mon.year).last()
            if payroll:
                continue
            salary = Salary.objects.filter(profile=profile).first()
            if salary is None:
                continue
            data, referral_emp_list, one_time_variable_pay, one_time_deductions, sandwich_days = compute_payroll(salary,
                                                                                                                 profile)

            serializer = CreatePayrollSerializer(data=data)
            if not serializer.is_valid():
                return return_error_response(serializer)
            _ = serializer.create(serializer.validated_data)
            # one_time_deductions.update(is_active=False)
            # one_time_variable_pay.update(is_active=False)
            for emp in referral_emp_list:
                emp.is_open = False
                emp.is_ref_bonus_paid = True
                emp.closing_date = tz.localize(datetime.now())
                emp.save()
            sandwich_days.update(is_sandwich=True, status="Absent")
        return HttpResponse(json.dumps({"message": "payroll created successfully"}))
    except Exception as e:
        logger.info("exception at add_variable_pay {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetECPLPayroll(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetEcplPayrollSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET)
        self.queryset = Payroll.objects.filter(search_query).filter(**filter_by).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


class GetMyECPLPayroll(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetEcplPayrollSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET)
        self.queryset = Payroll.objects.filter(profile=request.user).filter(search_query).filter(
            **filter_by).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


class GetAllPayroll(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetEcplPayrollSerializer  # GetPayrollSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        fields_look_up = {"first_name": "profile__first_name", "middle_name": "profile__middle_name",
                          "last_name": "profile__last_name", "email": "profile__email",
                          "designation": "profile__designation__name", "department": "profile__department__name",
                          "pay_grade": "profile__onboard__salary__pay_grade",
                          "gender": "profile__onboard__candidate__gender",
                          "branch": "profile__onboard__branch", "emp_id": "profile__emp_id",
                          "lwd": "profile__last_working_day", "emp_name": "profile__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = Payroll.objects.filter(search_query).filter(**filter_by).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


class GetAllDeductions(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetDeductionSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        fields_look_up = {"emp_id": "profile__emp_id", "created_by_emp_id": "created_by__emp_id",
                          "updated_by_emp_id": "updated_by__emp_id", "emp_name": "profile__full_name",
                          "created_by_name": "created_by__full_name",
                          "updated_by_name": "updated_by__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = Deduction.objects.filter(search_query).filter(**filter_by).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


class GetAllVariablePay(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetVariablePaySerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        emp = request.user
        my_team = get_team_ids(emp)
        if my_team is None:
            self.queryset = []
            return self.list(request, *args, **kwargs)
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=variable_pay_look_up_columns)
        if is_management(emp) or emp.designation.department.dept_id == "hr":
            self.queryset = VariablePay.objects.filter(search_query).filter(**filter_by).order_by(*order_by_cols)
        else:
            self.queryset = VariablePay.objects.filter(profile__team__id__in=my_team).filter(search_query).filter(
                **filter_by).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


variable_pay_look_up_columns = {"emp_id": "profile__emp_id", "created_by_emp_id": "created_by__emp_id",
                                "updated_by_emp_id": "updated_by__emp_id", "emp_name": "profile__full_name",
                                "app_or_reg_by_emp_id": "app_or_reg_by__emp_id",
                                "app_or_reg_by_name": "app_or_reg_by__full_name",
                                "created_by_name": "created_by__full_name",
                                "updated_by_name": "updated_by__full_name"}


class GetAllVariablePayToBeApproved(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetVariablePaySerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        emp = request.user
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=variable_pay_look_up_columns)
        my_teams = get_team_ids(emp)
        if not my_teams:
            self.queryset = []
        else:
            self.queryset = VariablePay.objects.filter(status="Pending", created_by__team__in=my_teams).filter(
                search_query).filter(**filter_by).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_variable_pay_approve_count(request):
    try:
        usr = request.user
        my_teams = get_team_ids(usr)
        if my_teams is None:
            my_teams = []
        vpay_count = VariablePay.objects.filter(status="Pending", created_by__team__in=my_teams).count()
        return Response({"Pending_Variable_Pay": vpay_count})
    except Exception as e:
        logger.info("exception at upload_payroll {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_variable_pay_status(request):
    try:
        ids = request.data.get("vpay_ids")
        if type(ids) != list:
            raise ValueError("provide list of variable pay ids")
        vpay_status = request.data.get("status")
        vpay_status_list = [i[0] for i in settings.ERF_APPROVAL_STATUS]
        if vpay_status not in vpay_status_list:
            raise ValueError("Invalid variable pay status is provided")
        vpays = VariablePay.objects.filter(id__in=ids)
        vpays.update(status=vpay_status, app_or_reg_by=request.user, app_or_reg_at=tz.localize(datetime.now()))
        return Response({"message": "Variable pay status updated successfully"})
    except Exception as e:
        logger.info("exception at upload_payroll {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def upload_payroll(request):
    try:
        map_columns = {
    "emp_id": "EID",
    "emp_name": "NAME",
    "doj": "DOJ",
    "lwd": "LWD",
    "status": "STATUS",
    "process": "PROCESS",
    "designation": "AMS DESIGNATION",
    "department": "DEPARTMENT",
    "bank_name": "BANK NAME",
    "name_as_per_bank_acc": "NAME AS PER BANK ACCOUNT",
    "account_number": "ACCOUNT NUMBER",
    "ifsc_code": "IFSC Code",
    "fixed_gross": "FIXED SALARY",
    "basic": "BASIC",
    "hra": "HRA",
    "statutory_bonus": "STATUTORY BONUS",
    "medical_allowance": "MEDICAL ALLOWANCE",
    "other_allowances": "OTHER ALLOWANCE",
    "total_gross_salary": "GROSS",
    "pf_emp": "EMPLOYEE PF",
    "esi": "EMPLOYEE ESI",
    "pt": "PROFESSIONAL TAX",
    "tds": "TDS",
    "net_salary": "NET PAY",
    "pf_emr": "EMPLOYER PF",
    "ctc": "CTC",
    "is_check": "CHECK",
    "trng": "TRNG",
    "p":"P",
    "hd":"HD",
    "lop": "LOP",
    "absent": "AB",
    "ncns": "NCNS",
    "off": "OFF",
    "nh": "NH",
    "total_days": "Total Days",
    "calendar_days": "Cal Days",
    "paid_days": "Paid Days",
    "lop_days": "LOP Days",
    "year":"YEAR",
    "month_number":"MONTH NUMBER",
    "arrears": "Arrears",
    "hold_salary": "Hold Salary",
    "second_slot": "2nd Slot",
}
        xl_file = request.data.get("payroll_file")
        if not xl_file:
            raise ValueError("Please upload payroll file")
        xl_data = read_file_format_output(xl_file)
        if xl_data:
            sample_key = list(xl_data.keys())[0]
            first_value = xl_data[sample_key][0] if xl_data.get(sample_key) else None

        model_fields = Payroll._meta.get_fields()
        column_names = [field.name for field in model_fields if field.concrete]
        column_names.remove("id")
        i = 0
        obj_list = []
        print("DEBUG - xl_data keys:", list(xl_data.keys())[:10])
        emp_id_list = xl_data.get('EID')
        print(emp_id_list)
        if not emp_id_list or emp_id_list == ():
            raise ValueError("Please add valid EMP-IDs to the file uploaded.")
        payroll_cr_list = {}
        while emp_id_list and i < len(emp_id_list):
            emp_id = emp_id_list[i]
            if not emp_id:
                i += 1
                continue
            try:
                employee = Profile.objects.get(emp_id=emp_id)
            except Exception as e:
                raise ValueError("employee with emp_id {0} doesn't exist".format(emp_id))
            if emp_id is None:
                break
            obj_data = {}
            for col_name in column_names:
                map_name = map_columns.get(col_name, col_name)
                xl_col = xl_data.get(map_name)
                if xl_col is None:
                    continue
                value = xl_col[i]
                obj_data[col_name] = value
            doj = obj_data.get('doj')
            if isinstance(doj, datetime):
                obj_data['doj'] = doj.date()
            serializer = UploadPayrollSerializer(data=obj_data)
            if not serializer.is_valid():
                return_error_response(serializer, raise_exception=True)

            pay_obj = Payroll.objects.filter(emp_id=emp_id, month_number=obj_data['month_number'],
                                             year=obj_data["year"]).last()
            if pay_obj:
                for key, value in serializer.validated_data.items():
                    setattr(pay_obj, key, value)
                pay_obj.save()
                logger.info("updated {0}".format(emp_id))
            else:
                serializer.validated_data["profile"] = employee
                payroll_cr_list[emp_id] = Payroll(**serializer.validated_data)

            i += 1
        if len(payroll_cr_list) > 0:
            Payroll.objects.bulk_create(list(payroll_cr_list.values()))
        return HttpResponse(json.dumps({"message": "uploaded successfully"}))
    except Exception as e:
        logger.info("exception at upload_payroll {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def check_if_variable_pay_accepted():
    date_25th = datetime.today().date().replace(day=25)
    if not datetime.today().date() >= date_25th:
        raise ValueError("Variable pay changes are accepted from 25th to till the end of the month")


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def upload_variable_pay(request):
    try:
        check_if_variable_pay_accepted()
        usr = request.user
        my_teams = get_team_ids(usr)
        xl_file = request.data.get("variable_pay_file")
        if not xl_file:
            raise ValueError("Please upload variable pay excel file")
        xl_data = read_file_format_output(xl_file)
        model_fields = VariablePay._meta.get_fields()
        column_names = [field.name for field in model_fields if field.concrete]
        column_names.remove("id")
        i = 0
        emp_id_list = xl_data.get('emp_id')
        if not emp_id_list or emp_id_list == ():
            raise ValueError("please add column emp_id with valid emp_ids.")
        if my_teams is None:
            raise ValueError("There are no teams under you")
        variable_pay_updates = []
        variable_cr_objs = {}
        variable_upd_objs = {}
        while emp_id_list and i < len(emp_id_list):
            emp_id = emp_id_list[i]
            if emp_id in variable_cr_objs.keys() or emp_id in variable_upd_objs.keys():
                raise ValueError("Duplicates not allowed. emp_id {0}".format(emp_id))
            if not emp_id:
                i += 1
                continue
            try:
                employee = Profile.objects.get(emp_id=emp_id)
            except Exception as e:
                raise ValueError("employee with emp_id {0} doesn't exist or is no longer Active.".format(emp_id))
            if employee.team.id not in my_teams:
                raise ValueError("Employee '{0}' is not under your team.".format(emp_id))
            if emp_id is None:
                break
            obj_data = {}
            for col_name in column_names:
                # map_name = map_columns.get(col_name, col_name)
                xl_col = xl_data.get(col_name)
                if xl_col is None:
                    continue
                value = xl_col[i]
                obj_data[col_name] = value
            obj_data["month"] = datetime.today().month
            obj_data["year"] = datetime.today().year

            obj_data["created_by"] = usr.id
            serializer = AddVariablePaySerializer(data=obj_data, partial=True)
            if not serializer.is_valid():
                return_error_response(serializer, raise_exception=True)

            pay_obj = VariablePay.objects.filter(emp_id=emp_id, month=obj_data['month'],
                                                 year=obj_data["year"]).last()
            if pay_obj:
                for key, value in serializer.validated_data.items():
                    if key not in ["created_by"]:
                        setattr(pay_obj, key, value)
                    pay_obj.updated_by = usr
                    pay_obj.updated_at = datetime.now()
                    pay_obj = update_variable_pay_total(pay_obj)
                variable_upd_objs[emp_id] = pay_obj

            else:
                serializer.validated_data["profile"] = employee
                serializer = update_variable_pay_total(serializer)
                variable_cr_objs[emp_id] = VariablePay(**serializer.validated_data)

            i += 1
        if len(variable_cr_objs) > 0:
            VariablePay.objects.bulk_create(list(variable_cr_objs.values()))
        if len(variable_upd_objs) > 0:
            VariablePay.objects.bulk_update(list(variable_upd_objs.values()), column_names)
        return HttpResponse(json.dumps({"message": "uploaded successfully"}))
    except Exception as e:
        logger.info("exception at upload_payroll {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def calculate_salary_structure(level, gross, opting_for_pf):
    gross = float(gross)
    pay_grade_calc = PayGrade.objects.get(level=level)
    sal_calc = {"basic": round(gross * (pay_grade_calc.basic_perc / 100), 0)}
    sal_calc["hra"] = round(sal_calc["basic"] * (pay_grade_calc.hra_basic_perc / 100), 0)
    rem = gross - sal_calc["basic"] - sal_calc["hra"]
    sal_calc["tds"] = 0  # round(sal_calc["basic"] * (pay_grade_calc.tds_perc / 100), 0) # TODO
    sal_calc["pf_emp"] = 0
    sal_calc["pf_emr"] = 0
    sal_calc["medical_allowance"] = pay_grade_calc.medical_allow
    sal_calc["health_insurance_deduction"] = pay_grade_calc.health_insurance
    sal_calc["ta"] = pay_grade_calc.travel_allow
    sal_calc["tel_allowance"] = pay_grade_calc.telephone_allow
    sal_calc["pt"] = pay_grade_calc.pt if gross >= settings.PROF_TAX_LIMIT else 0
    # pf_gross =  gross - sal_calc["hra"] - sal_calc["tel_allowance"]
    # if opting_for_pf:
    #     sal_calc["pf_emp"] = round(pf_gross * (pay_grade_calc.pf_emp_perc / 100), 0) \
    #         if round(pf_gross, 0) <= settings.PF_GROSS_LIMIT else settings.PF_FIXED_DEDUCTION_AMOUNT
    #     sal_calc["pf_emr"] = round(pf_gross * (pay_grade_calc.pf_emr_perc / 100), 0) \
    #         if round(pf_gross, 0) <= settings.PF_GROSS_LIMIT else settings.PF_FIXED_DEDUCTION_AMOUNT
    if opting_for_pf:
        sal_calc["pf_emp"], sal_calc["pf_emr"] = calc_pf(sal_calc["basic"], pay_grade_calc)
    sal_calc["esi"], sal_calc["esi_emr"] = calc_esi(gross)
    tot_deductions = sal_calc["tds"] + sal_calc["pf_emp"] + sal_calc["pf_emr"] + sal_calc[
        "health_insurance_deduction"] + sal_calc["pt"] + sal_calc["esi"]
    sal_calc["total_deductions"] = tot_deductions
    sal_calc["oa"] = rem - sal_calc["ta"] - sal_calc["medical_allowance"] - sal_calc["tel_allowance"]
    # sal_calc["total_fixed_gross"] = sal_calc["basic"] + sal_calc["hra"] + sal_calc["oa"] + sal_calc["medical_allowance"] + \
    #                                 sal_calc["ta"] + sal_calc["tel_allowance"]
    sal_calc["total_fixed_gross"] = gross
    sal_calc["ctc"] = (gross + sal_calc["pf_emr"] + sal_calc["esi_emr"]) * 12

    sal_calc["net_salary"] = sal_calc["total_fixed_gross"] - tot_deductions
    sal_calc["total_deductions"] = tot_deductions - sal_calc["pf_emr"]  # ECPL specific

    for key, value in sal_calc.items():
        sal_calc[key] = int(value)

    # print("ctc", ctc)
    # print(sal_calc)
    return sal_calc


@api_view(["POST"])
def get_salary_structure(request):
    try:
        # serializer = GetSalaryStructureSerializer(data=request.data)
        # if not serializer.is_valid():
        #     return return_error_response(serializer)
        ctc = request.data.get('total_fixed_gross')
        level = request.data.get('pay_grade')
        if level not in [i[0] for i in settings.PAY_GRADE_LEVELS]:
            raise ValueError("Invalid pay-grade is provided")
        opting_for_pf = parse_boolean_value(request.data.get("opting_for_pf"))
        sal_calc = calculate_salary_structure(level, ctc, opting_for_pf)
        return HttpResponse(json.dumps(sal_calc))

    except Exception as e:
        logger.info("exception at get_salary_structure {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_salary_obj(sal_id):
    salary = Salary.objects.filter(id=sal_id).first()
    if salary is None:
        raise ValueError("Invalid salary-id is provided")
    return salary


def handle_salary_account_number(obj_data, emp_id):
    account_number = obj_data.get("account_number")
    if account_number is None:
        return None
    sal_num_obj = Salary.objects.exclude(profile__emp_id=emp_id).filter(
        account_number=account_number).first()
    if sal_num_obj:
        raise ValueError(f"record with account number {account_number} already exist")
    return account_number


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def upload_salary(request):
    try:
        usr = request.user
        upload_reason = request.data.get("upload_reason")
        comment = request.data.get("comment")
        xl_file = request.data.get("salary_file")
        if not xl_file:
            raise ValueError("Please upload payroll file")
        xl_data = read_file_format_output(xl_file)
        column_names, _, _ = get_column_names_with_foreign_keys_separate(Salary)
        # TODO check what to do with tds
        for col in ["id", "created_at", "updated_at", "last_update_reason", "tds", "esi",
                    "esi_emr", "auto_calculated", "opting_for_pf", "total_deductions"]:
            column_names.remove(col)
        for col in ["ctc"]:
            if col not in xl_data.keys():
                column_names.remove(col)

        i = 0
        cols_to_be_added = []
        for col in column_names:
            if col not in xl_data.keys():
                cols_to_be_added.append(col)
        if len(cols_to_be_added) > 0:
            cols_text = ", ".join(i for i in cols_to_be_added)
            raise ValueError(f'the following columns are not present in the upload file - "{cols_text}"')

        emp_id_list = xl_data.get('emp_id')
        salary_cr_list = {}
        serializer_val_data_objs = {}
        update_salary_history_objs = []
        if len(emp_id_list) == 0:
            raise ValueError("There are no emp_ids in the emp_id column")
        while emp_id_list and i < len(emp_id_list):
            emp_id = emp_id_list[i]
            if not emp_id:
                i += 1
                continue
            try:
                employee = Profile.objects.get(emp_id=emp_id)
            except Exception as e:
                raise ValueError("employee with emp_id {0} doesn't exist".format(emp_id))
            obj_data = {}
            for col_name in column_names:
                # map_name = map_columns.get(col_name, col_name)
                xl_col = xl_data.get(col_name)
                if xl_col is None:
                    continue
                value = xl_col[i]
                if (value is None or str(value).strip() == ""):
                    obj_data[col_name] = None
                else:
                    obj_data[col_name] = str(value).strip()
                if col_name == "ifsc_code" and value and len(obj_data[col_name]) != 11:
                    logger.info(f"{value},{len(value)},{len(obj_data[col_name])}")
            obj_data['last_update_reason'] = upload_reason
            obj_data["auto_calculated"] = False
            obj_data["pf_emp"] = obj_data.get("pf_emp", 0)
            obj_data["pf_emr"] = obj_data.get("pf_emr", 0)
            pf_emp = obj_data.get("pf_emp")
            obj_data["opting_for_pf"] = True if pf_emp and str(pf_emp).isnumeric() else False
            obj_data["esi"], obj_data["esi_emr"] = calc_esi(float(obj_data["total_fixed_gross"]))
            if "ctc" not in obj_data:
                obj_data["ctc"] = round((float(obj_data["pf_emr"]) + float(obj_data["esi_emr"]) + float(
                    obj_data["total_fixed_gross"])) * 12, 0)
            serializer = UpdateSalarySerializer(data=obj_data)
            if not serializer.is_valid():
                return_error_response(serializer, raise_exception=True)
            sal_obj = Salary.objects.filter(profile__emp_id=emp_id).first()
            if sal_obj and upload_reason == "Onboard":
                i += 1
                continue
                # raise ValueError(f"Salary onboard information already exists for emp-id {emp_id}")
            account_number = handle_salary_account_number(obj_data, emp_id)
            serializer.validated_data["account_number"] = account_number
            serializer_val_data_objs[emp_id] = {"serializer_data": serializer.validated_data, "profile": employee,
                                                "salary": sal_obj}
            i += 1
        for emp_id in serializer_val_data_objs.keys():
            serializer_val_data = serializer_val_data_objs[emp_id].get("serializer_data")
            sal_obj = serializer_val_data_objs[emp_id].get("salary")
            if sal_obj:
                update_sal_obj = update_salary_history(sal_obj, request, serializer_val_data, usr, comment)
                if update_sal_obj:
                    update_salary_history_objs.append(update_sal_obj)
            else:
                serializer_val_data["profile"] = serializer_val_data_objs[emp_id].get("profile")
                serializer_val_data["updated_by"] = usr
                salary_cr_list[emp_id] = Salary(**serializer_val_data)
        message = "No changes made"
        if len(salary_cr_list) > 0:
            message = "Uploaded details successfully"
            Salary.objects.bulk_create(list(salary_cr_list.values()))
        if len(update_salary_history_objs) > 0:
            message = "Updated details successfully"
            UpdateSalaryHistory.objects.bulk_create(update_salary_history_objs)
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at upload_payroll {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_salary(request, sal_id):
    try:
        usr = request.user
        salary = get_salary_obj(sal_id)
        data = request.data
        comment = request.data.get("comment")
        if comment is None or comment == "":
            raise ValueError("comment is required")
        account_number = request.data.get("account_number")
        if not account_number and str(account_number).strip() == "":
            account_number = None

        serializer = UpdateSalarySerializer(data=data, account_number=account_number)
        if not serializer.is_valid():
            return_error_response(serializer)
        update_sal = update_salary_history(salary, request, serializer.validated_data, usr, comment)
        if update_sal:
            UpdateSalaryHistory.objects.bulk_create([update_sal])

        serializer.update(salary, serializer.validated_data)
        return HttpResponse(json.dumps({"message": "salary updated successfully"}))
    except Exception as e:
        logger.info("exception at get_salary_structure {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllSalary(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetSalarySerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        fields_look_up = {"emp_id": "profile__emp_id", "updated_by_emp_id": "updated_by__emp_id",
                          "emp_name": "profile__full_name", "updated_by_name": "updated_by__full_name",
                          "emp_status": "profile__status"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)
        self.queryset = Salary.objects.filter(search_query).filter(**filter_by).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)
