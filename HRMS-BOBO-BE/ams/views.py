import csv
import io
import json
import pytz
import logging
import traceback

from django.contrib.postgres.aggregates import StringAgg
from django.core.paginator import Paginator
from django.db.models.expressions import RawSQL

from hrms import settings
from datetime import datetime, timedelta, date, time

from django.db.models import Sum, F, ExpressionWrapper, fields, Q, Value, Min, Max, TextField
from django.db.models.functions import Coalesce, Cast
from django.db import connection

from django.db.models import Q, Count
from django.http import HttpResponse
from rest_framework import status, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import calendar
from ams.models import Attendance, Leave, LeaveBalance, LeaveBalanceHistory, AttendanceCorrectionHistory, Break, \
    Schedule, MonthlyLeaveBalance, SuspiciousLoginActivity
from ams.serializers import AttendanceSerializer, CreateLeaveSerializer, LeaveSerializer, GetAllAppliedLeaveSerializer, \
    ApproveLeaveSerializer, GetAllLeaveBalanceHistorySerializer, CreateAttendanceScheduleSerializer, \
    GetAttendanceScheduleSerializer, ApproveAttendanceSerializer, RequestForAttendanceCorrectionSerializer, \
    GetAllAttCorRequestSerializer, ApproveAttendanceCorrectionSerializer, RequestForScheduleCorrectionSerializer, \
    GetAllLeaveBalanceSerializer, BreakSerializer, CheckInCheckOutSerializer, ConsolidatedBreakSerializer, \
    AttendanceLogSerializer
from mapping.models import Profile, Miscellaneous, MiscellaneousMiniFields
from mapping.views import HasUrlPermission
from team.models import Team
from utils.util_classes import CustomTokenAuthentication
from utils.utils import return_error_response, get_sort_and_filter_by_cols, update_request, validate_input_date, \
    get_dates_range, get_team_ids, get_emp_by_emp_id, get_formatted_date, read_file_format_output, \
    add_hour_minute_to_time, reduce_hour_minute_to_time, get_diff_hours_minutes, is_management, \
    get_start_date_end_date_week_offs_start_end_time, update_schedule, update_leave_balance, \
    create_att_list_upd_list_sch_list, get_selected_emp_under_team, format_hour_min_second, get_all_managers, \
    check_if_date_gte_25, get_25th_date, validate_team_and_rm1_rm2_rm3, get_1st_date, split_week_off_and_return, \
    check_if_date_is_excepted, get_excluded_dates, parse_boolean_value, check_for_60th_day, tz, \
    check_if_user_is_inactive, get_limited_breaks, get_ip_address, get_group_concat_query_part, is_hr, is_cc

logger = logging.getLogger(__name__)
from django.utils.timezone import localtime

from rest_framework.views import APIView
from .models import Attendance
from .serializers import BulkRangeAttendanceUpdateSerializer
from datetime import datetime, time, timedelta
import random



# def handle_csv_file(csv_file):
#     import pandas as pd
#     data = pd.read_csv(csv_file)
#     pd_data = data[['emp_id']]
#     for key, emp_id in enumerate(pd_data['emp_id']):
#         try:
#             profile = Profile.objects.get(username=emp_id)
#             profile.save()
#         except:
#             pass


def calculate_leave_balance(profile, prev_month_last_day):
    full_day_count = Attendance.objects.filter(Q(profile=profile), Q(date__range=[prev_month_last_day.replace(day=1),
                                                                                  prev_month_last_day]),
                                               Q(status__in=['Present', 'Week Off', 'Comp Off',
                                                             'Client Off', 'Training', 'PL', 'SL'])).count()
    half_day_count = Attendance.objects.filter(Q(profile=profile), Q(date__range=[prev_month_last_day.replace(day=1),
                                                                                  prev_month_last_day]),
                                               Q(status='Half Day')).count()
    earned = full_day_count + (half_day_count / 2)
    pl_balance = round(earned / 20, 2)
    sl_balance = 1 if pl_balance > 0 else 0
    return pl_balance, sl_balance


def compute_leave_balance(profiles, date_now=None, update_leave_balance=True):
    objs = []
    monthly_lb_objs = []
    if date_now is None:
        date_now = tz.localize(datetime.now())
    prev_month_last_day = date_now.date().replace(day=1) - timedelta(days=1)
    for profile in profiles:
        monthly_leave_balance = MonthlyLeaveBalance.objects.filter(profile=profile,
                                                                   date__month=date_now.month, date__year=date_now.year)
        #excluding the updation of sl for prev month <=15 date joined emps
        if profile.date_of_joining.year == prev_month_last_day.year and profile.date_of_joining.month == prev_month_last_day.month and  profile.date_of_joining.day <= 15:
            if monthly_leave_balance.count() > 1:
                continue
        else:
            if monthly_leave_balance.count() > 0:
                continue
        pl, sl = calculate_leave_balance(profile, prev_month_last_day)
        leave_balance, created = LeaveBalance.objects.get_or_create(profile=profile)
        if profile.status == "Attrition" or (profile.date_of_joining.year == prev_month_last_day.year and profile.date_of_joining.month == prev_month_last_day.month and  profile.date_of_joining.day <= 15):
            sl = 0
        if update_leave_balance:
            leave_balance.sick_leaves += sl
            leave_balance.paid_leaves += pl
            leave_balance.total = round(leave_balance.sick_leaves + leave_balance.paid_leaves, 2)
            objs.append(
                LeaveBalanceHistory(profile=profile, date=date_now, leave_type="PL",
                                    pl_balance=leave_balance.paid_leaves,
                                    sl_balance=leave_balance.sick_leaves - sl, transaction="Leaves Earned",
                                    no_of_days=pl,
                                    total=leave_balance.total - sl))
            if not (profile.date_of_joining.year == prev_month_last_day.year and profile.date_of_joining.month == prev_month_last_day.month and  profile.date_of_joining.day <= 15):
                objs.append(
                    LeaveBalanceHistory(profile=profile, date=date_now, leave_type="SL",
                                        pl_balance=leave_balance.paid_leaves,
                                        sl_balance=leave_balance.sick_leaves, transaction="Leaves Earned", no_of_days=sl,
                                        total=leave_balance.total))
            monthly_lb_objs.append(MonthlyLeaveBalance(profile=profile, date=date_now, leave_type="PL",
                                                       transaction="Leaves Earned", no_of_days=pl,
                                                       total=leave_balance.total - sl))
            if not (profile.date_of_joining.year == prev_month_last_day.year and profile.date_of_joining.month == prev_month_last_day.month and  profile.date_of_joining.day <= 15):
                monthly_lb_objs.append(MonthlyLeaveBalance(profile=profile, date=date_now, leave_type="SL",
                                                           transaction="Leaves Earned", no_of_days=sl,
                                                           total=leave_balance.total))
            leave_balance.save()
        else:
            lbh = LeaveBalanceHistory.objects.filter(profile=profile, date__year=prev_month_last_day.year,
                                                     date__month=prev_month_last_day.month).order_by("date").last()
            if lbh is None:
                continue

            total = lbh.total
            total += sl + pl
            objs.append(
                LeaveBalanceHistory(profile=profile, date=date_now, leave_type="PL", pl_balance=0,
                                    sl_balance=0, transaction="Leaves Earned", no_of_days=pl,
                                    total=total - sl))
            objs.append(
                LeaveBalanceHistory(profile=profile, date=date_now, leave_type="SL", pl_balance=0,
                                    sl_balance=0, transaction="Leaves Earned", no_of_days=sl,
                                    total=total))
            monthly_lb_objs.append(MonthlyLeaveBalance(profile=profile, date=date_now, leave_type="PL",
                                                       transaction="Leaves Earned", no_of_days=pl,
                                                       total=total - sl))
            monthly_lb_objs.append(MonthlyLeaveBalance(profile=profile, date=date_now, leave_type="SL",
                                                       transaction="Leaves Earned", no_of_days=sl,
                                                       total=total))

    if len(objs) > 0:
        LeaveBalanceHistory.objects.bulk_create(objs)
        MonthlyLeaveBalance.objects.bulk_create(monthly_lb_objs)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_leave_balance(request):
    leave_balance = None
    profile = request.user
    try:
        leave_balance = LeaveBalance.objects.get(profile=profile)
    except Exception as e:
        logger.info("exception --- there is no leave balance records for  {0} ".format(request.user.emp_id))
    data = {"sick_leaves": round(leave_balance.sick_leaves, 2) if leave_balance else 0,
            "paid_leaves": round(leave_balance.paid_leaves, 2) if leave_balance else 0,
            "total": round(leave_balance.total, 2) if leave_balance else 0}
    return Response(data)


class GetMyLeaveBalanceHistory(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllLeaveBalanceHistorySerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"emp_name": "profile__full_name", 'emp_id': "profile__emp_id"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        self.queryset = LeaveBalanceHistory.objects.filter(Q(profile=request.user)).filter(**filter_by).filter(
            search_query).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


class GetTeamLeaveBalanceHistory(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllLeaveBalanceHistorySerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"emp_name": "profile__full_name", 'emp_id': "profile__emp_id"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        self.queryset = LeaveBalanceHistory.objects.filter(profile__team__manager=request.user).filter(
            **filter_by).filter(search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


class GetAllLeaveBalanceHistory(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllLeaveBalanceHistorySerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"emp_name": "profile__full_name", 'emp_id': "profile__emp_id"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        self.queryset = LeaveBalanceHistory.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


class GetMyTeamLeaveBalance(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllLeaveBalanceSerializer

    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"emp_name": "profile__full_name", 'emp_id': "profile__emp_id"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        self.queryset = LeaveBalance.objects.filter(profile__team__manager=request.user,
                                                    profile__is_active=True).filter(**filter_by).filter(
            search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


def get_leave_obj_by_id(leave_id):
    try:
        leave = Leave.objects.get(id=leave_id)
        return leave
    except Exception as e:
        raise ValueError("Invalid leave id")


def return_back_the_leaves_to_employee(leave, leave_balance, transaction_msg):
    no_of_days = leave.no_of_days
    if transaction_msg == "Leave Withdrawn" and leave.status == "Approved":
        no_of_days = Attendance.objects.filter(profile=leave.profile, date__gte=leave.start_date,
                                               date__lte=leave.end_date,
                                               status__in=["PL", "SL"]).count()
    if leave.leave_type == "PL":
        leave_balance.paid_leaves = round(leave_balance.paid_leaves + no_of_days, 2)
    else:
        leave_balance.sick_leaves = round(leave_balance.sick_leaves + no_of_days, 2)
    leave_balance.total = round(leave_balance.total + no_of_days, 2)
    leave_balance.save()
    LeaveBalanceHistory.objects.create(sl_balance=leave_balance.sick_leaves, pl_balance=leave_balance.paid_leaves,
                                       profile=leave.profile, date=datetime.now(), leave_type=leave.leave_type,
                                       transaction=transaction_msg,
                                       no_of_days=no_of_days, total=leave_balance.total)


def deduct_the_leaves_from_employee(leave, leave_balance, transaction_msg):
    if leave.leave_type == "PL":
        leave_balance.paid_leaves = round(leave_balance.paid_leaves - leave.no_of_days, 2)
    else:
        leave_balance.sick_leaves = round(leave_balance.sick_leaves - leave.no_of_days, 2)
    leave_balance.total = round(leave_balance.total - leave.no_of_days, 2)
    leave_balance.save()
    LeaveBalanceHistory.objects.create(sl_balance=leave_balance.sick_leaves, pl_balance=leave_balance.paid_leaves,
                                       profile=leave.profile, date=datetime.now(), leave_type=leave.leave_type,
                                       transaction=transaction_msg,
                                       no_of_days=leave.no_of_days, total=leave_balance.total)


def create_or_update_attendance(start_date, end_date, attendance, profile, usr, stat):
    dates = get_dates_range(start_date, end_date)
    for lday in dates:
        attend, created = Attendance.objects.get_or_create(
            profile=profile, date=lday,
            defaults={"profile": profile, "status": stat, "date": lday,
                      "comment": "approved leave", "approved_by": usr, "start_time": "00:00:00",
                      "end_time": "00:00:00"})
    attendance.update(profile=profile, approved_by=usr, status=stat)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def approve_leave(request, leave_id):
    try:
        first_day_of_month = datetime.today().date().replace(day=1)
        prev_month_last_day = first_day_of_month - timedelta(days=1)
        today_date = datetime.today().date()

        leave_approve_status = request.data.get("status")
        comments = request.data.get("comments")
        approve_serializer = ApproveLeaveSerializer(data=request.data)
        if not approve_serializer.is_valid():
            return_error_response(approve_serializer, raise_exception=True)
        if leave_approve_status is None or comments is None:
            raise ValueError("Provide valid status and comments")
        usr = request.user
        my_team = get_team_ids(usr)

        if my_team is None:
            raise ValueError("The employee's team is not under you")
        leave = get_leave_obj_by_id(leave_id)
        if leave.status == "Rejected":
            raise ValueError("The leave is already rejected")
        approve_emp = leave.profile

        if approve_emp.team.id not in my_team:
            raise ValueError("team of the candidate and manager doesn't match")
        is_tl = False
        is_mgr = False
        if usr == approve_emp.team.manager:
            is_tl = True
        if usr == approve_emp.team.manager.team.manager:
            is_mgr = True
        if not (is_tl or is_mgr):
            raise ValueError("This activity can be done by only the employees respective RM1 and RM2")
        leave_balance = LeaveBalance.objects.get(profile=leave.profile)

        logger.info("statues {0} {1} {2}".format(check_if_date_is_excepted(leave.start_date), (
                (prev_month_last_day.month == leave.start_date.month) and today_date.day != 1), (
                                                         leave.start_date < prev_month_last_day.replace(day=1))))
        if not check_if_date_is_excepted(leave.start_date) and (
                (prev_month_last_day.month == leave.start_date.month) and today_date.day != 1) or (
                leave.start_date < prev_month_last_day.replace(day=1)):
            raise ValueError("You can not approve the past month leaves")

        if leave_approve_status == "Approved":
            check_if_user_is_inactive(leave.profile)

        if is_tl and is_mgr:
            if leave.manager_status != "Pending":
                raise ValueError("Manager has already {0} the leave request".format(leave.manager_status))

            leave.manager_status = leave_approve_status
            leave.tl_status = leave_approve_status
            leave.manager_comments = comments
            leave.tl_comments = comments
            leave.status = leave_approve_status
            leave.approved_by1 = usr
            leave.approved_by2 = usr
        elif is_tl:
            if leave.tl_status != "Pending":
                raise ValueError(
                    "First reporting manager {0} has already {1} the leave request".format(leave.approved_by1.full_name,
                                                                                           leave.tl_status))
            leave.tl_status = leave_approve_status
            leave.tl_comments = comments
            leave.approved_by1 = usr

        else:
            if leave.manager_status != "Pending":
                raise ValueError("Manager has already {0} the leave request".format(leave.manager_status))

            leave.manager_comments = comments
            leave.manager_status = leave_approve_status
            leave.approved_by2 = usr

        if leave_approve_status == "Rejected":
            return_back_the_leaves_to_employee(leave, leave_balance, "Leave Rejected")
            leave.status = leave_approve_status
        elif leave.tl_status == leave.manager_status and leave.tl_status == "Approved":
            leave.status = leave_approve_status
            attendance = Attendance.objects.filter(profile=leave.profile, date__gte=leave.start_date,
                                                   date__lte=leave.end_date)
            create_or_update_attendance(leave.start_date, leave.end_date, attendance, leave.profile, usr,
                                        leave.leave_type)
            leave_balance.save()
        leave.save()
        return Response({"message": "Leave status updated successfully"})
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def appeal_leave_request(request, leave_id):
    try:
        leave = get_leave_obj_by_id(leave_id)
        if leave.profile != request.user:
            raise ValueError("this leave record doesn't belong to yours")
        leave.escalate = True
        leave.status = "Pending"
        leave.escalate_comment = request.data.get("escalate_comment")
        leave_balance = LeaveBalance.objects.get(profile=leave.profile)
        deduct_the_leaves_from_employee(leave, leave_balance, "Leave Escalated")
        leave.save()
        return Response({"message": "Operation successful"})
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllAppliedLeaves(mixins.ListModelMixin,
                          GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllAppliedLeaveSerializer
    model = serializer_class.Meta.model

    def get(self, request, eom, *args, **kwargs):
        emp = request.user
        mapping_column_names = {"emp_name": "profile__full_name", 'emp_id': "profile__emp_id",
                                "tl_name": "profile__team__manager__full_name",
                                "manager_name": "profile__team__manager__team__manager__full_name",
                                "tl_emp_id": "profile__team__manager__emp_id",
                                "manager_emp_id": "profile__team__manager__team__manager__emp_id"
                                }
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        team = get_team_ids(emp)
        if team is None:
            self.queryset = []
        else:
            if check_if_date_gte_25() and str(eom) == "1":
                self.queryset = Leave.objects.filter(Q(status="Pending") & (
                        Q(start_date__gte=get_1st_date()) | Q(start_date__in=get_excluded_dates()))).filter(
                    Q(profile__team__id__in=team)).filter(**filter_by).filter(search_query).order_by(*order_by_cols)
            else:
                self.queryset = Leave.objects.filter(Q(status="Pending") & (
                        Q(start_date__gte=get_1st_date()) | Q(start_date__in=get_excluded_dates()))).filter(
                    Q(manager_status="Pending", tl_status="Approved", profile__team__manager__team__manager=emp) | Q(
                        tl_status="Pending", profile__team__manager=emp)).filter(
                    **filter_by).filter(search_query).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


def get_leaves_count(usr, eom):
    team = get_team_ids(usr)
    if not team:
        return 0
    if check_if_date_gte_25() and str(eom) == "1":
        return Leave.objects.filter(Q(status="Pending") & (
                Q(start_date__gte=get_1st_date()) | Q(start_date__in=get_excluded_dates()))).filter(
            Q(profile__team__id__in=team)).count()

    return Leave.objects.filter(Q(status="Pending") & (
            Q(start_date__gte=get_1st_date()) | Q(start_date__in=get_excluded_dates()))).filter(
        Q(profile__team__manager__team__manager=usr, manager_status="Pending", tl_status="Approved") | Q(
            profile__team__manager=usr, tl_status="Pending")).count()


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_all_applied_leaves_count(request, eom):
    leave_count = get_leaves_count(request.user, eom)
    return Response({"count": leave_count})


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def withdraw_leave(request, leave_id):
    try:
        leave = get_leave_obj_by_id(leave_id)
        if leave.profile != request.user:
            raise ValueError("This leave doesn't belong to yours")
        today = datetime.today().date()
        if leave.status in ["Rejected", "Withdrawn"]:
            raise ValueError("The leave is already {0}".format(leave.status))
        last_month_first_day = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        if today.year != leave.start_date.year:
            raise ValueError("You can withdraw only current year leaves")
        if leave.start_date < last_month_first_day:
            raise ValueError(
                "Sorry, you can not withdraw leaves applied prior to last month")
        leave_balance = LeaveBalance.objects.get(profile=leave.profile)
        return_back_the_leaves_to_employee(leave, leave_balance, "Leave Withdrawn")
        if leave.status == "Approved":
            Attendance.objects.filter(profile=leave.profile, date__gte=leave.start_date, status__in=["PL", "SL"],
                                      date__lte=leave.end_date).update(status="Scheduled")

        leave.status = 'Withdrawn'
        leave.save()
        return HttpResponse(json.dumps({"message": "Leave withdrawn successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def check_for_applied_leave(leaves, start_date, end_date, leave_attendances):
    leave_days = get_dates_range(start_date, end_date)

    for i in leave_days:
        if i in leave_attendances:
            raise ValueError("Leave is already applied for {0}".format(i))

    for i in leaves:
        days = get_dates_range(i.start_date, i.end_date)
        if start_date <= i.start_date and end_date >= i.end_date:
            raise ValueError(
                "Leave is already applied for {0} to {1} with status {2}".format(i.start_date, i.end_date, i.status))
        if start_date in days or end_date in days:
            raise ValueError(
                "Leave is already applied for {0} to {1} with status {2}".format(i.start_date, i.end_date, i.status))


def check_if_candidate_has_completed_3_months(profile, leave_type):
    if not profile.date_of_joining:
        raise ValueError("Date of joining is not present please contact - admin")
    # joining_days = (datetime.today().date() - profile.date_of_joining).days
    # if int(joining_days) <= 90:
    #     raise ValueError("You must complete 90 days to apply for any leave")


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def apply_for_leave(request):
    try:
        profile = request.user
        data = update_request(request.data, profile=profile.id)
        leave_serializer = CreateLeaveSerializer(data=data)
        if not leave_serializer.is_valid():
            return_error_response(leave_serializer, raise_exception=True)
        end_date = leave_serializer.validated_data.get('end_date')
        start_date = leave_serializer.validated_data.get('start_date')
        leave_type = data.get('leave_type')
        check_if_candidate_has_completed_3_months(profile, leave_type)

        today = datetime.today()
        leave_balance = LeaveBalance.objects.get(profile=profile)
        no_of_days = (end_date - start_date).days + 1
        if no_of_days - 1 < 0:
            raise ValueError("End date must be greater than start date")

        last_month_last_day = datetime.today().date().replace(day=1) - timedelta(days=1)
        logger.info("SL{0} {1} {2}".format(check_if_date_is_excepted(start_date), (
                (start_date.month == today.month) and start_date <= today.date() and
                end_date <= today.date()), today.day == 1 and start_date.month == last_month_last_day.month))
        if leave_type == "SL":
            if not check_if_date_is_excepted(start_date) and not (
                    (start_date.month == today.month) and start_date <= today.date() and
                    end_date <= today.date() or (today.day == 1 and start_date.month == last_month_last_day.month)):
                raise ValueError(
                    "Invalid start-date or end-date, it should be today or previous to today of this month")
            if not leave_balance.sick_leaves >= no_of_days:
                raise ValueError("You don't have sufficient leave balance to apply for leave")

        elif leave_type == "PL":
            last_date = today.date() + timedelta(days=30)
            if not (
                    start_date > today.date() and start_date <= end_date and end_date >= start_date and end_date <= last_date):
                logger.info(f"PL Invalid start-date or end-date  {start_date} {end_date} by emp_id {profile.emp_id}")
                raise ValueError("Invalid start-date or end-date, it should be within 30 days from today")
            if not leave_balance.paid_leaves >= no_of_days:
                raise ValueError("You don't have sufficient leave balance to apply for leave")

        leaves = Leave.objects.filter(profile=profile, status="Pending").filter(
            Q(start_date__month=start_date.month) | Q(end_date__month=end_date.month))
        leave_attendances = list(Attendance.objects.filter(profile=profile, date__gte=start_date, date__lte=end_date,
                                                           status__in=["SL", "PL"]).values_list("date", flat=True))
        check_for_applied_leave(leaves, start_date, end_date, leave_attendances)
        leave_serializer.validated_data['no_of_days'] = no_of_days
        leave_serializer.validated_data['status'] = 'Pending'
        # if profile.team.manager == profile:
        #     leave_serializer.validated_data["manager_status"] = "Approved"
        #     leave_serializer.validated_data["manager_comments"] = "Self approved"
        #     leave_serializer.validated_data['status'] = "Approved"
        #     attendance = Attendance.objects.filter(profile=profile, date__gte=start_date,
        #                                            date__lte=end_date)
        #     attendance.update(status=leave_type)

        leave = leave_serializer.create(leave_serializer.validated_data)
        deduct_the_leaves_from_employee(leave, leave_balance, "Leave Applied")
        return Response({"message": "Leave applied successfully"})
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllLeaveHistory(mixins.ListModelMixin,
                         GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllAppliedLeaveSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            emp = request.user
            mapping_column_names = {"emp_name": "profile__full_name", 'emp_id': "profile__emp_id",
                                    "tl_name": "profile__team__manager__full_name",
                                    "tl_emp_id": "profile__team__manager__emp_id",
                                    "manager_name": "profile__team__manager__team__manager__full_name",
                                    "manager_emp_id": "profile__team__manager__team__manager__emp_id"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(
                request.GET, fields_look_up=mapping_column_names)
            self.queryset = Leave.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)

        except Exception as e:
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllTeamSelfLeaveHistory(mixins.ListModelMixin,
                                 GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllAppliedLeaveSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            emp = request.user
            mapping_column_names = {"emp_name": "profile__full_name", 'emp_id': "profile__emp_id",
                                    "tl_name": "profile__team__manager__full_name",
                                    "tl_emp_id": "profile__team__manager__emp_id",
                                    "manager_name": "profile__team__manager__team__manager__full_name",
                                    "manager_emp_id": "profile__team__manager__team__manager__emp_id"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(
                request.GET, fields_look_up=mapping_column_names)
            team = get_team_ids(emp)
            if team:
                self.queryset = Leave.objects.filter(
                    Q(profile__team__manager=emp) | Q(profile=emp) | Q(profile__team__manager__team__manager=emp) | Q(
                        profile__team__manager__team__manager__team__manager=emp)).filter(
                    **filter_by).filter(search_query).order_by(*order_by_cols)
            else:
                self.queryset = Leave.objects.filter(profile=emp).filter(**filter_by).filter(search_query).order_by(
                    *order_by_cols)
            return self.list(request, *args, **kwargs)

        except Exception as e:
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_attendance(request, emp_id):
    try:
        start_date = request.data.get("start_date")  # TODO Remove it.
        end_date = request.data.get("end_date")
        if not validate_input_date(start_date) or not validate_input_date(end_date):
            raise ValueError("Please provide valid start_date and end_date in the form YYYY-mm-dd")
        profile = Profile.objects.get(emp_id=emp_id)
        attendance = Attendance.objects.filter(date__gte=start_date, date__lte=end_date, profile=profile)
        attendance = AttendanceSerializer(attendance, many=True).data
        return HttpResponse(json.dumps({"attendance": attendance}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_team_members_emp_ids(request):
    my_team = get_team_ids(request.user)
    if not my_team:
        return HttpResponse(json.dumps({"members": []}))
    profile_ids = list(Profile.objects.exclude(status__in=["Attrition"]).filter(
        team__in=my_team).values_list('emp_id', flat=True).distinct())
    return HttpResponse(json.dumps({"members": profile_ids}))


def get_unmarked_attendance_count(emp, eom):
    team = get_team_ids(emp)
    four_days_prev_day = datetime.today() - timedelta(days=4)
    eight_days_prev_day = datetime.today() - timedelta(days=8)
    if not team:
        return 0
    if check_if_date_gte_25() and str(eom) == "1":
        return Attendance.objects.filter(Q(
            status="Scheduled", emp_start_time__isnull=False, emp_end_time__isnull=False,
            date__lte=datetime.today().date(), profile__team__id__in=team) & (Q(
            date__gte=get_1st_date()) | Q(date__in=get_excluded_dates()))).count()
    return Attendance.objects.filter(Q(
        status="Scheduled", emp_start_time__isnull=False, emp_end_time__isnull=False) & (Q(
        date__gte=get_1st_date()) | Q(date__in=get_excluded_dates()))).filter(
        Q(date__lt=eight_days_prev_day, profile__team__manager__team__manager__team__manager=emp) | Q(
            date__gte=eight_days_prev_day, date__lt=four_days_prev_day,
            profile__team__manager__team__manager=emp) | Q(
            profile__team__manager=emp, date__gte=four_days_prev_day,
            date__lte=datetime.today().date())).count()


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_all_unmarked_attendance_count(request, eom):
    attendance_count = get_unmarked_attendance_count(request.user, eom)
    return Response({"count": attendance_count})


class GetApproveTeamAttendanceSchedule(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAttendanceScheduleSerializer
    model = serializer_class.Meta.model

    def get(self, request, eom, *args, **kwargs):
        try:
            emp = request.user
            four_days_prev_day = datetime.today() - timedelta(days=4)
            eight_days_prev_day = datetime.today() - timedelta(days=8)

            mapping_column_names = {"emp_name": "profile__full_name", "emp_id": "profile__emp_id",
                                    "manager_emp_id": "profile__team__manager__emp_id",
                                    "manager_name": "profile__team__manager__full_name",
                                    "team": "profile__team__name", "base_team": "profile__team__base_team__name",
                                    "sch_upd_by_emp_id": "sch_upd_by__emp_id",
                                    "sch_upd_by_name": "sch_upd_by__full_name"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(
                request.GET, fields_look_up=mapping_column_names)
            my_team = get_team_ids(emp)
            if my_team is None:
                self.queryset = []
                return self.list(request, *args, **kwargs)

            if check_if_date_gte_25() and str(eom) == "1":
                self.queryset = Attendance.objects.filter(Q(
                    status="Scheduled", emp_start_time__isnull=False, emp_end_time__isnull=False,
                    date__lte=datetime.today().date(), profile__team__id__in=my_team) & (Q(
                    date__gte=get_1st_date()) | Q(date__in=get_excluded_dates()))).filter(
                    **filter_by).filter(search_query).order_by(*order_by_cols)
            else:
                self.queryset = Attendance.objects.filter(Q(
                    status="Scheduled", emp_start_time__isnull=False, emp_end_time__isnull=False) & (Q(
                    date__gte=get_1st_date()) | Q(date__in=get_excluded_dates()))).filter(
                    Q(date__lt=eight_days_prev_day, profile__team__manager__team__manager__team__manager=emp) | Q(
                        date__gte=eight_days_prev_day, date__lt=four_days_prev_day,
                        profile__team__manager__team__manager=emp) | Q(
                        profile__team__manager=emp, date__gte=four_days_prev_day,
                        date__lte=datetime.today().date())).filter(**filter_by).filter(search_query).order_by(
                    *order_by_cols)

            return self.list(request, *args, **kwargs)

        except Exception as e:
            return HttpResponse(json.dumps({"error": str(e)}),
                                status=status.HTTP_400_BAD_REQUEST)


class GetTeamAttendanceSchedule(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAttendanceScheduleSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            emp = request.user
            mapping_column_names = {"emp_name": "profile__full_name", "emp_id": "profile__emp_id",
                                    "manager_emp_id": "profile__team__manager__emp_id",
                                    "manager_name": "profile__team__manager__full_name",
                                    "team": "profile__team__name", "base_team": "profile__team__base_team__name",
                                    "sch_upd_by_emp_id": "sch_upd_by__emp_id",
                                    "approved_by_name": "approved_by__full_name",
                                    "approved_by_emp_id": "approved_by__emp_id",
                                    "sch_upd_by_name": "sch_upd_by__full_name"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(
                request.GET, fields_look_up=mapping_column_names)

            # TODO make it non-hard-coded
            if is_management(emp):
                # Excluding Inactive Employees
                self.queryset = Attendance.objects.filter(profile__is_staff=False, profile__is_active=True).filter(
                    **filter_by).filter(search_query).order_by(*order_by_cols)
            else:
                # Everyone under emp in the Team Hierarchy should be visible in Team Schedule
                self.queryset = Attendance.objects.filter(profile__is_active=True).filter(
                    Q(profile__team__manager=emp) | Q(profile__team__manager__team__manager=emp) | Q(
                        profile__team__manager__team__manager__team__manager=emp)).filter(**filter_by).filter(
                    search_query).order_by(*order_by_cols)

            return self.list(request, *args, **kwargs)

        except Exception as e:
            logger.info("exception at GetTeamAttendanceSchedule {0}".format(traceback.format_exc(5)))
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetMyAttendanceSchedule(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAttendanceScheduleSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            emp = request.user
            mapping_column_names = {"emp_name": "profile__full_name", "emp_id": "profile__emp_id",
                                    "manager_emp_id": "profile__team__manager__emp_id",
                                    "manager_name": "profile__team__manager__full_name",
                                    "team": "profile__team__name", "base_team": "profile__team__base_team__name",
                                    "sch_upd_by_emp_id": "sch_upd_by__emp_id",
                                    "approved_by_name": "approved_by__full_name",
                                    "approved_by_emp_id": "approved_by__emp_id",
                                    "sch_upd_by_name": "sch_upd_by__full_name"}

            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=mapping_column_names)
            self.queryset = Attendance.objects.filter(profile=emp).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)

        except Exception as e:
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def approve_team_attendance(request):
    try:
        usr = request.user
        attendance_list = request.data.get("attendance")
        my_team = get_team_ids(usr)
        first_day_of_month = datetime.today().date().replace(day=1)
        prev_month_last_day = first_day_of_month - timedelta(days=1)
        today_date = datetime.today().date()

        if my_team is None:
            raise ValueError("The employee's team is not under you")
        attend_list = []
        for attendance in attendance_list:
            serialize_attendance = ApproveAttendanceSerializer(data=attendance)
            if not serialize_attendance.is_valid():
                return return_error_response(serialize_attendance, raise_exception=True)
            date_val = serialize_attendance.validated_data['date']
            if not check_if_date_is_excepted(date_val) and not (
                    (prev_month_last_day.month == date_val.month and today_date.day == 1) or
                    (today_date.month == date_val.month and date_val <= today_date)):
                raise ValueError("You can only update current months attendance")
            try:
                attendance['profile'] = Profile.objects.get(emp_id=attendance['emp_id'])
            except:
                raise ValueError("Provide valid emp_id")
            validate_team_and_rm1_rm2_rm3(usr, attendance['profile'], my_team)
            leave_count = Leave.objects.filter(profile=attendance['profile'], status="Pending",
                                               start_date__gte=date_val, end_date__lte=date_val).count()
            if leave_count > 0:
                raise ValueError("emp {0} has applied leave for {1} ".format(attendance['emp_id'], attendance['date']))
            attend_list.append(attendance)

        for attend in attend_list:
            is_half_day = parse_boolean_value(attend.get('is_half_day'))
            attend_obj = Attendance.objects.get(profile=attend['profile'], date=attend['date'])
            if attend_obj.status in ["PL", "SL"]:
                raise ValueError("Leaves cannot be changed, please refresh your page")
            if attend_obj.status != "Scheduled":
                comment = attend.get('comment')
                if comment is None:
                    raise ValueError("Provide the comment for update")
                attend_obj.comment = comment
            if is_half_day:
                attend_obj.status = "Half Day"
            else:
                if attend_obj.is_training:
                    attend_obj.status = "Training"
                else:
                    attend_obj.status = "Present"
            attend_obj.approved_by = usr
            attend_obj.save()

        return Response({"message": "Marked attendance successfully"})

    except Exception as e:
        logger.info("exception at approve_team_attendance {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_ml(request, emp_id):  # TODO test after attendance done
    try:
        profile = get_emp_by_emp_id(emp_id)
        loc_date = request.data.get("date")
        if not loc_date:
            raise ValueError("Please provide the date")
        loc_date = datetime.fromisoformat(loc_date)
        _180_days = loc_date + timedelta(days=179)
        attendances = Attendance.objects.filter(profile=profile, date__gte=loc_date, date__lte=_180_days)
        create_or_update_attendance(loc_date, _180_days, attendances, profile, request.user, "ML")
        attendances.update(status="ML")
        return HttpResponse(json.dumps({"message": "Updated maternity leave successfully"}))
    except Exception as e:
        logger.info("exception at update_ml {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def check_and_get_attendance_login_value(attendance):
    login_hours_window = MiscellaneousMiniFields.objects.filter(field="login_hours_window").last().content
    one_hour_earlier_time = reduce_hour_minute_to_time(int(login_hours_window), 0, attendance.start_time)
    one_hour_past_time = add_hour_minute_to_time(int(login_hours_window), 0, attendance.start_time)
    now_time = datetime.now().time()
    login = False
    if not attendance.emp_end_time and one_hour_earlier_time <= now_time <= one_hour_past_time:
        login = True
    if attendance.status != "Scheduled":
        login = False
    return login


def check_and_log_suspicious_activity(request, attendance, event_type):
    try:
        new_ip = get_ip_address(request)
        # logger.info(f"new_ip {new_ip} pre_ip {attendance.logged_in_ip}")
        if attendance.logged_in_ip and attendance.logged_in_ip != new_ip:
            SuspiciousLoginActivity.objects.create(attendance=attendance, logged_in_ip=attendance.logged_in_ip,
                                                   activity_type=event_type, other_ip_address=new_ip)
    except Exception as e:
        logger.info(f"exception at check_and_log_suspicious_activity {str(e)}")
        pass


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_login_attendance(request):
    try:
        # TODO Handle if employee logs out after 24 hr off-schedule
        usr = request.user
        today = datetime.today().date()
        attendance = Attendance.objects.filter(profile=usr, date=today).last()
        if attendance is None:
            raise ValueError("There is no schedule for today")
        if attendance.emp_start_time:
            raise ValueError("You are already logged in")

        login = check_and_get_attendance_login_value(attendance)

        if attendance.emp_start_time and attendance.emp_end_time:
            raise ValueError("Your login entry exists, cannot login again")

        if not login:
            raise ValueError(
                "you can login only if your start time is one hour earlier to your shift time or greater than that")

        if not attendance.emp_end_time and login:
            attendance.emp_start_time = datetime.now().replace(microsecond=0)
            attendance.logged_in_ip = get_ip_address(request)
            attendance.save()

        return HttpResponse(json.dumps({"login": login}))
    except Exception as e:
        logger.info("exception at update_login_attendance {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def end_all_ongoing_break(request, prev_attendance, msg):
    existing = Break.objects.filter(attendance=prev_attendance) or None
    if existing:
        ongoing, obj = check_existing_ongoing_break(request, existing)
        if ongoing:
            obj.break_end_time = datetime.now()
            obj.comment = msg
            obj.save()
    return None


def check_if_day_is_endofmonth_for_auto_approval(attendance):
    today = datetime.today().date()
    tomo = today + timedelta(days=1)
    day_after_tomo = tomo + timedelta(days=1)
    total_hour, minutes, seconds = [int(i) for i in attendance.total_time.split(":")]
    minutes = minutes + seconds / 60
    total_hour = total_hour + minutes / 60
    logger.info(f"totalHour {total_hour}, {6 <= total_hour <= 10}")
    if 6 <= total_hour <= 10:
        if (today.day > tomo.day and tomo.strftime("%A") in ["Saturday", "Sunday"]) or (
                today.day > day_after_tomo.day and day_after_tomo.strftime("%A") == "Sunday"):
            attendance.is_auto_approved = True
            attendance.approved_at = tz.localize(datetime.now())
            attendance.status = "Present"
            if attendance.is_training:
                attendance.status = "Training"
            attendance.save()


def check_if_day_is_endofmonth_for_auto_approval_custom_seed_one(attendance):
    today = datetime.today().date()
    tomo = today + timedelta(days=1)
    day_after_tomo = tomo + timedelta(days=1)
    total_hour, minutes, seconds = [int(i) for i in attendance.total_time.split(":")]
    minutes = minutes + seconds / 60
    total_hour = total_hour + minutes / 60
    # logger.info(f"totalHour {total_hour}, {6 <= total_hour <= 10}")
    if 6 <= total_hour <= 10:
        attendance.is_auto_approved = True
        attendance.approved_at = tz.localize(datetime.now())
        attendance.status = "Present"
        if attendance.is_training:
            attendance.status = "Training"
        attendance.save()


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_logout_attendance(request):
    try:
        usr = request.user
        prev_attendance, login_status = get_login_status(usr)
        message = "No changes made"
        if not prev_attendance:
            raise ValueError("You are not logged in. Please refresh your browser once and try again")
        end_all_ongoing_break(request, prev_attendance, "Employee Logged out.")
        prev_attendance.emp_end_time = datetime.now().replace(microsecond=0)
        prev_attendance.is_self_marked = True
        h, m, s = get_diff_hours_minutes(prev_attendance.emp_start_time, prev_attendance.emp_end_time)
        h, m, s = format_hour_min_second(h, m, s)
        prev_attendance.total_time = f"{h}:{m}:{s}"
        prev_attendance.save()
        check_if_day_is_endofmonth_for_auto_approval(prev_attendance)
        check_and_log_suspicious_activity(request, prev_attendance, "logout")
        message = "Logged out Successfully"
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at update_logout_attendance {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_login_status(usr):
    prev_attendance = Attendance.objects.filter(profile=usr, emp_start_time__isnull=False,
                                                emp_end_time__isnull=True).last()
    login_status = True if prev_attendance else False
    return prev_attendance, login_status


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_attend_login_status(request):
    try:
        usr = request.user
        today = datetime.today().date()
        prev_attendance, login = get_login_status(usr)
        start_time = None
        end_time = None
        if prev_attendance is None:
            attendance = Attendance.objects.filter(profile=usr, date=today).last()
            if attendance is None:
                # raise ValueError("There is No schedule exists for this date")
                return Response({"error": "There is No schedule exists for this date"},
                                status=status.HTTP_400_BAD_REQUEST)
            login = check_and_get_attendance_login_value(attendance)
            total_time = attendance.total_time
            start_time = attendance.start_time
            end_time = attendance.end_time
        else:
            total_time = prev_attendance.total_time
            start_time = prev_attendance.start_time
            end_time = prev_attendance.end_time
        total_time = str(total_time) if total_time else None
        emp_start_time = prev_attendance.emp_start_time if prev_attendance else None
        emp_start_time = str(emp_start_time) if emp_start_time else None
        return Response(
            {"emp_start_time": emp_start_time, "login": login, "total_time": total_time, "start_time": start_time,
             "end_time": end_time})
    except Exception as e:
        logger.info("exception at get_attend_login_status {0}".format(traceback.format_exc(5)))
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def upload_attend_schedule(request):
    try:
        usr = request.user
        xl_file = request.data.get("attend_schedule_file")
        xl_data = read_file_format_output(xl_file)
        team_ids = get_team_ids(usr)
        if team_ids is None:
            raise ValueError("No Employees under your team.")
        count = 0
        fields = ["emp_id", "start_date", "end_date", "start_time", "end_time", 'week_off', "is_training"]

        headers = xl_data.keys()
        for field in fields:
            if field not in headers:
                raise ValueError("Please provide the {0} information in the excel".format(field))
        emp_id_list = xl_data.get('emp_id')
        fields.remove("week_off")
        message = "No Changes made"
        logger.info("len={0}".format(len(emp_id_list)))
        not_updated = ""
        att_list = []
        att_up_list = []
        sch_list = []
        i = 0
        while i < len(emp_id_list):
            emp_id = xl_data['emp_id'][i]
            if not emp_id:
                i += 1
                continue
            start_date = xl_data['start_date'][i]
            end_date = xl_data['end_date'][i]
            start_time = xl_data['start_time'][i]
            if end_date < start_date:
                raise ValueError("Start date should be less that End Date.")
            end_time = xl_data['end_time'][i]
            week_offs = xl_data['week_off'][i]
            is_training = bool(xl_data["is_training"][i]) if xl_data["is_training"][i] else False
            xl_data["is_training"][i] = is_training
            comment = xl_data['comment'][i] if xl_data.get('comment') else None
            brk = False
            for field in fields:
                val = xl_data[field][i]
                if val is None or val == "":
                    brk = True
            if brk:
                continue
            profile = Profile.objects.filter(emp_id=emp_id).last()
            if profile is None:
                message = "record with emp_id {0} doesnt exist ".format(emp_id)
                i += 1
                continue
            if profile.team.id not in team_ids:
                message = "employee is not in the teams"
                not_updated += str(profile.emp_id)
                i += 1
                continue
            if week_offs:
                week_offs = week_offs.split(",")
                for wo in week_offs:
                    wo = str(wo).strip().lower()
                    if wo == "":
                        continue
                    elif wo not in ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]:
                        raise ValueError(
                            "weekoff value {0} is not in the valid list => Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday".format(
                                wo))
                week_offs = [day.strip().title() for day in week_offs]
            else:
                week_offs = ""
            if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
                raise ValueError("Start date and End date must be in the format YYYY-MM-DD")
            check_for_60th_day(end_date)
            try:
                if type(start_time) == str:
                    start_time = time.fromisoformat(start_time)
                if type(end_time) == str:
                    end_time = time.fromisoformat(end_time)
            except Exception as e:
                raise ValueError("start-time {0} and end-time {1} must be format HH:MM:SS".format(start_time, end_time))
            if not isinstance(start_time, time) or not isinstance(end_time, time):
                raise ValueError("start-time {0} and end-time {1} must be format HH:MM:SS".format(start_time, end_time))
            start_date = start_date.date()
            end_date = end_date.date()
            att_list, att_up_list, sch_list = update_schedule(
                Attendance, usr, profile, start_date, end_date, week_offs, start_time, end_time, comment, is_training,
                Schedule, joining_date=None, att_list=att_list, att_up_list=att_up_list, sch_list=sch_list, upload=True)
            i += 1
        # message = create_att_list_upd_list_sch_list(Attendance, Schedule, att_list, att_up_list, sch_list)
        message = f"These employees not in the team under you - {not_updated}" if not_updated != "" else "Schedule create/update is successful"
        logger.info("message={0}".format(message))
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at upload_attend_schedule {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)



@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def upload_attendance(request):
    try:
        usr = request.user
        xl_file = request.data.get("attend_schedule_file")
        xl_data = read_file_format_output(xl_file)
        fields = ["emp_id", "date", "attendance"]

        headers = xl_data.keys()
        for field in fields:
            if field not in headers:
                raise ValueError("Please provide the {0} information in the excel".format(field))
        emp_id_list = xl_data.get('emp_id')
        message = "No Changes made"
        logger.info("len={0}".format(len(emp_id_list)))
        attendance_list = []
        i = 0
        while i < len(emp_id_list):
            emp_id = xl_data['emp_id'][i]
            if not emp_id:
                i += 1
                continue
            date = xl_data['date'][i]
            attendance_status = xl_data['attendance'][i]
            profile = Profile.objects.filter(emp_id=emp_id).last()
            if profile is None:
                i += 1
                continue
            if attendance_status.lower() not in [status[0].lower() for status in settings.DIRECT_ATTENDANCE_MARK_STATUS]:
                raise ValueError(f"Invalid Attendance status for emp_id {emp_id}")
            attendance = Attendance.objects.filter(profile=profile, date=date).last()
            leave_balance = LeaveBalance.objects.get(profile=profile)
            if attendance is None:
                raise ValueError(f"Attendance is not foud on {date} for emp_id {emp_id}")
            brk = False
            for field in fields:
                val = xl_data[field][i]
                if val is None or val == "":
                    brk = True
            if brk:
                i += 1
                continue
            if attendance.status not in ["Scheduled","Absent"]:
                i+=1
                continue

            attendance.status = attendance_status
            attendance.sch_upd_by = usr
            attendance.comment = f"Updated by {usr.emp_id}"
            if attendance_status.lower()=="present":
                start_time_obj = datetime.strptime(attendance.start_time, "%H:%M:%S").time()
                end_time_obj = datetime.strptime(attendance.end_time, "%H:%M:%S").time()
                logger.info(f"start_time_obj----{start_time_obj}")
                attendance.emp_start_time=datetime.combine(date, start_time_obj)
                attendance.end_time=datetime.combine(date, end_time_obj)
            attendance_list.append(attendance)
            if attendance_status.lower()=="sl":
                data={"start_date":date.date(),"end_date":date.date(),"reason":f"Updated by {usr.emp_id}","leave_type":"SL","profile":profile.id}
                leave_serializer=CreateLeaveSerializer(data=data)
                if not leave_serializer.is_valid():
                    return_error_response(leave_serializer, raise_exception=True)
                s_end_date = leave_serializer.validated_data.get('end_date')
                s_start_date = leave_serializer.validated_data.get('start_date')
                no_of_days = (s_end_date - s_start_date).days + 1

                if not leave_balance.sick_leaves >= no_of_days:
                    raise ValueError(
                        f"Profile emp -{profile.emp_id} don't have sufficient leave balance to apply for leave")
                leave_serializer.validated_data['no_of_days'] = no_of_days
                leave_serializer.validated_data['status'] = 'Approved'
                leave_serializer.validated_data["tl_status"]='Approved'
                leave_serializer.validated_data["manager_status"]='Approved'
                leave_serializer.validated_data["tl_comments"]="Manual attendance sl approved"
                leave_serializer.validated_data["manager_comments"]="Manual attendance sl approved"
                leave_serializer.validated_data["approved_by1"]=usr
                leave_serializer.validated_data["approved_by2"]=usr

                leave = leave_serializer.create(leave_serializer.validated_data)
                deduct_the_leaves_from_employee(leave, leave_balance, "SL applied via ams/upload_attendance")

            if attendance_status.lower()=="pl":
                data = {"start_date": date.date(), "end_date": date.date(), "reason": f"Updated by {usr.emp_id}",
                        "leave_type": "PL", "profile": profile.id}
                leave_serializer = CreateLeaveSerializer(data=data)
                if not leave_serializer.is_valid():
                    return_error_response(leave_serializer, raise_exception=True)
                s_end_date = leave_serializer.validated_data.get('end_date')
                s_start_date = leave_serializer.validated_data.get('start_date')
                no_of_days = (s_end_date - s_start_date).days + 1
                if not leave_balance.paid_leaves >= no_of_days:
                    raise ValueError(f"Profile emp -{profile.emp_id} don't have sufficient leave balance to apply for leave")
                leave_serializer.validated_data['no_of_days'] = no_of_days
                leave_serializer.validated_data['status'] = 'Approved'
                leave_serializer.validated_data["tl_status"] = 'Approved'
                leave_serializer.validated_data["manager_status"] = 'Approved'
                leave_serializer.validated_data["tl_comments"] = "Manual attendance pl approved"
                leave_serializer.validated_data["manager_comments"] = "Manual attendance pl approved"
                leave_serializer.validated_data["approved_by1"] = usr
                leave_serializer.validated_data["approved_by2"] = usr

                leave = leave_serializer.create(leave_serializer.validated_data)
                deduct_the_leaves_from_employee(leave, leave_balance, "PL applied via ams/upload_attendance")

            i += 1
        if len(attendance_list) > 0:
            Attendance.objects.bulk_update(attendance_list, ["sch_upd_by", "status", "comment"])
            message = "Changes made"
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at upload_attendance {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)



@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_attend_schedule(request):
    try:
        usr = request.user
        start_date, end_date, week_offs, start_time, end_time = get_start_date_end_date_week_offs_start_end_time(
            CreateAttendanceScheduleSerializer, request)
        today = datetime.today().date()
        if start_date < today or end_date < today:
            raise ValueError("start date and end date must be greater than or equal to today")

        check_for_60th_day(end_date)
        # Correction in is_training
        is_training = json.loads(request.data.get("is_training", "false"))
        comment = request.data.get("comment")
        team_ids = get_team_ids(usr)
        if team_ids is None:
            raise ValueError("There is no team member under you")

        team = request.data.get('team')
        emp_ids = request.data.get("emp_ids")
        try:
            profiles = get_selected_emp_under_team(usr, team, emp_ids)
        except Exception as e:
            raise ValueError(str(e) + " try refreshing the browser once and try again")
        message = "No Changes made"
        not_updated = ""
        att_list = []
        att_up_list = []
        sch_list = []

        for profile in profiles:
            if profile.team.id not in team_ids:
                message = "employee is not in the teams"
                not_updated += ", " + str(profile.emp_id)
                continue
            att_list, att_up_list, sch_list = update_schedule(
                Attendance, usr, profile, start_date, end_date, week_offs, start_time, end_time,
                comment, is_training, Schedule, joining_date=None, att_list=att_list, att_up_list=att_up_list,
                sch_list=sch_list)
        message = create_att_list_upd_list_sch_list(Attendance, Schedule, att_list, att_up_list, sch_list)
        message = f"These employees not in the team under you - {not_updated}" if not_updated != "" else message
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at create_attend_schedule {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def request_for_attendance_correction(request):
    try:
        usr = request.user
        attendance_list = request.data.get("attendance")
        if attendance_list is None:
            raise ValueError("Please provide the attendance input data")
        my_team = get_team_ids(usr)

        if my_team is None:
            raise ValueError("The employee is not under your team")
        attend_list = []
        for attendance in attendance_list:
            serialize_attendance = RequestForAttendanceCorrectionSerializer(data=attendance)
            if attendance.get("is_training") is None:
                raise ValueError(
                    "please provide is_training info, try refreshing the browser once if there is an error")
            if not serialize_attendance.is_valid():
                return return_error_response(serialize_attendance, raise_exception=True)
            yesterday = datetime.today().date() - timedelta(days=1)
            first_day_of_month = datetime.today().date().replace(day=1)
            date_val = serialize_attendance.validated_data['date']
            if not (
                    date_val >= first_day_of_month and date_val <= yesterday) and not date_val == datetime.today().date() and not check_if_date_is_excepted(
                date_val):
                raise ValueError("You can only request for past days of the current month")
            try:
                attendance['profile'] = Profile.objects.get(emp_id=attendance['emp_id'])
                if not attendance['profile'].is_active:
                    raise ValueError("The employee {0} is not active {0}".format(attendance['profile'].emp_id))
            except:
                raise ValueError("Provide valid emp_id")
            if date_val == datetime.today().date():
                attend_obj = Attendance.objects.filter(profile=attendance['profile'], date=date_val).last()
                if attend_obj:
                    if attend_obj.emp_start_time and attend_obj.emp_end_time is None:
                        raise ValueError(
                            "emp {0} cannot request for correction until logs out".format(attend_obj.profile.emp_id))
                else:
                    raise ValueError("You can only request for past days of the current month")

            if attendance['profile'].team.id not in my_team and not is_management(usr):
                raise ValueError("emp-id {0} with team {1} doesn't belong to your team".format(
                    attendance['profile'].emp_id, attendance['profile'].team.name))

            leave_count = Leave.objects.filter(profile=attendance['profile'], status="Approved",
                                               start_date=date_val, end_date=date_val).count()
            if leave_count > 0:
                raise ValueError("emp {0} has applied leave for {1} ".format(attendance['emp_id'], attendance['date']))
            attend_list.append(attendance)
        att_cor_reqs = []
        attend_list_objs = []
        for attend in attend_list:
            attend_obj = Attendance.objects.get(profile=attend['profile'], date=attend['date'])
            comment = attend.get('comment')
            is_training = json.loads(attend.get("is_training", "false"))
            if comment is None:
                raise ValueError("Provide the comment for update")
            att_cor = AttendanceCorrectionHistory.objects.filter(correction_status="Pending", attendance=attend_obj)
            if att_cor.count() > 0:
                raise ValueError(
                    "Attendance correction request already exists for {0} on date {1}".format(attend['profile'].emp_id,
                                                                                              attend['date']))
            att_cor_reqs.append(
                AttendanceCorrectionHistory(correction_status="Pending", attendance=attend_obj, request_comment=comment,
                                            att_cor_req_by=usr, requested_status=attend['status'],
                                            is_training=is_training))
            attend_obj.is_att_cor_req = True
            attend_list_objs.append(attend_obj)
        if len(att_cor_reqs) > 0:
            AttendanceCorrectionHistory.objects.bulk_create(att_cor_reqs)
            Attendance.objects.bulk_update(attend_list_objs, ['is_att_cor_req'])

        return Response({"message": "Request for attendance correction successful"})

    except Exception as e:
        logger.info("exception at request_for_attendance_correction {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllAttCorRequests(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllAttCorRequestSerializer
    model = serializer_class.Meta.model

    def get(self, request, eom, *args, **kwargs):
        emp = request.user
        # Changing the Timezone to UTC
        timez = pytz.timezone('utc')
        four_days_prev_day = datetime.now(timez) - timedelta(days=4)
        eight_days_prev_day = datetime.now(timez) - timedelta(days=8)

        mapping_column_names = {"emp_name": "attendance__profile__full_name", "emp_id": "attendance__profile__emp_id",
                                "current_status": "attendance__status", "date": "attendance__date",
                                "att_cor_req_by_emp_id": "att_cor_req_by__emp_id",
                                "att_cor_req_by_name": "att_cor_req_by__full_name",
                                "approved_by_emp_id": "approved_by__emp_id",
                                "approved_by_name": "approved_by__full_name",
                                "to_be_approved_by_name": "att_cor_req_by__team__manager__full_name",
                                "to_be_approved_by_emp_id": "att_cor_req_by__team__manager__emp_id"
                                }

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(
            request.GET, fields_look_up=mapping_column_names)
        my_team = get_team_ids(emp)
        if my_team is None and emp.designation.department.dept_id != "hr":
            self.queryset = []
            return self.list(request, *args, **kwargs)
        if my_team is None:
            my_team = []

        if check_if_date_gte_25() and str(eom) == "1":
            if emp.designation.department.dept_id == "hr":
                self.queryset = AttendanceCorrectionHistory.objects.filter(
                    correction_status="Pending", created_at__date__gte=get_1st_date(),
                    attendance__profile__is_active=True).filter(
                    Q(created_at__lt=eight_days_prev_day) | Q(
                        att_cor_req_by__team__id__in=my_team, created_at__date__lte=datetime.today().date())).filter(
                    **filter_by).filter(search_query).order_by(*order_by_cols)
                return self.list(request, *args, **kwargs)

            self.queryset = AttendanceCorrectionHistory.objects.filter(
                correction_status="Pending", created_at__date__gte=get_1st_date(),
                attendance__profile__is_active=True).filter(
                Q(att_cor_req_by__team__id__in=my_team, created_at__date__lte=datetime.today().date())).filter(
                **filter_by).filter(search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)

        if emp.designation.department.dept_id == "hr":
            self.queryset = AttendanceCorrectionHistory.objects.filter(
                correction_status="Pending", created_at__date__gte=get_1st_date(),
                attendance__profile__is_active=True).filter(
                Q(created_at__lt=eight_days_prev_day) | Q(
                    created_at__gte=eight_days_prev_day, created_at__lt=four_days_prev_day,
                    att_cor_req_by__team__manager__team__manager=emp) | Q(
                    att_cor_req_by__team__manager=emp, created_at__gte=four_days_prev_day,
                    created_at__lte=datetime.now(timez))).filter(**filter_by).filter(search_query).order_by(
                *order_by_cols)
        else:
            correction_count = AttendanceCorrectionHistory.objects.filter(
                correction_status="Pending", created_at__date__gte=get_1st_date(),
                attendance__profile__is_active=True).filter(
                Q(created_at__date__gte=eight_days_prev_day, created_at__date__lt=four_days_prev_day,
                  att_cor_req_by__team__manager__team__manager=emp) | Q(
                    att_cor_req_by__team__manager=emp, created_at__date__gte=four_days_prev_day,
                    created_at__date__lte=datetime.today().date())).count()

            self.queryset = AttendanceCorrectionHistory.objects.filter(
                correction_status="Pending", created_at__date__gte=get_1st_date(),
                attendance__profile__is_active=True).filter(
                Q(created_at__date__gte=eight_days_prev_day, created_at__date__lt=four_days_prev_day,
                  att_cor_req_by__team__manager__team__manager=emp) | Q(
                    att_cor_req_by__team__manager=emp, created_at__date__gte=four_days_prev_day,
                    created_at__date__lte=datetime.today().date())).filter(**filter_by).filter(search_query).order_by(
                *order_by_cols)

        return self.list(request, *args, **kwargs)


def return_back_the_sl_pl_to_employee(no_of_days, profile, leave_type):
    leave_balance = LeaveBalance.objects.get(profile=profile)

    if leave_type == "PL":
        leave_balance.paid_leaves = round(leave_balance.paid_leaves + no_of_days, 2)
    else:
        leave_balance.sick_leaves = round(leave_balance.sick_leaves + no_of_days, 2)

    leave_balance.total = round(leave_balance.total + no_of_days, 2)
    leave_balance.save()
    LeaveBalanceHistory.objects.create(sl_balance=leave_balance.sick_leaves, pl_balance=leave_balance.paid_leaves,
                                       profile=profile, date=datetime.now(), leave_type=leave_type,
                                       transaction="credited back by attendance correction request",
                                       no_of_days=no_of_days, total=leave_balance.total)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def approve_correction_request(request):
    try:
        first_day_of_month = datetime.today().date().replace(day=1)
        prev_month_last_day = first_day_of_month - timedelta(days=1)
        today_date = datetime.today().date()

        usr = request.user
        attendance_list = request.data.get("attendance")
        my_team = get_team_ids(usr)
        if my_team is None and usr.designation.department.dept_id != "hr":
            raise ValueError("There are no teams under you")
        if my_team is None:
            my_team = []

        attend_cor_list = []
        attend_list = []
        return_back_sl_pl = []
        for attendance in attendance_list:
            serialize_attendance = ApproveAttendanceCorrectionSerializer(data=attendance)
            if not serialize_attendance.is_valid():
                return return_error_response(serialize_attendance, raise_exception=True)
            att_date = attendance.get('date')
            if att_date is None:
                raise ValueError("Please send the date")
            try:
                attendance['date'] = datetime.fromisoformat(att_date).date()
            except:
                raise ValueError("Please send proper date")
            try:
                att_cor = AttendanceCorrectionHistory.objects.get(id=attendance['id'])
            except:
                raise ValueError("Provide valid attendance correction id")
            if not att_cor.attendance.profile.is_active:
                raise ValueError("The employee {0} is not active".format(att_cor.attendance.profile.emp_id))
            date_val = att_cor.attendance.date
            if not check_if_date_is_excepted(date_val) and not (
                    (prev_month_last_day.month == date_val.month and today_date.day == 1) or
                    (today_date.month == date_val.month and date_val <= today_date)):
                raise ValueError("You can only approve the current months attendance correction requests")

            if att_cor.attendance.profile.team.id not in my_team:
                if usr.designation.department.dept_id != "hr":
                    raise ValueError("emp-id {0} with team {1} doesn't belong to your team".format(
                        att_cor.attendance.profile.emp_id, att_cor.attendance.profile.team.name))
            if usr.designation.department.dept_id != "hr":
                rm1 = att_cor.att_cor_req_by.team.manager if att_cor.att_cor_req_by.team and att_cor.att_cor_req_by.team.manager else None
                if rm1 is None or rm1.team is None or rm1.team.manager is None:
                    raise ValueError("RM1 or RM2 of the EID {0} does not exist contact admin {0}".format(
                        att_cor.att_cor_req_by.emp_id))
                if not (rm1 == usr or rm1.team.manager == usr):
                    raise ValueError(
                        "Approving attendance correction for emp-id {0} can be done by RM1 or RM2 of {0}".format(
                            att_cor.att_cor_req_by.emp_id))

            if attendance["correction_status"] == "Approved":
                check_if_user_is_inactive(att_cor.attendance.profile)

            att_cor.correction_status = attendance["correction_status"]
            att_cor.approved_comment = attendance["approved_comment"]
            att_cor.approved_by = usr
            att_cor.approved_at = datetime.now()
            attend_cor_list.append(att_cor)
            attendance = att_cor.attendance
            attendance.is_att_cor_req = False
            if att_cor.correction_status == "Approved":
                stat = attendance.status
                if stat in ["PL", "SL"]:
                    return_back_sl_pl.append(
                        {"no_of_days": 1, "profile": att_cor.attendance.profile, "leave_type": stat})
                attendance.is_training = att_cor.is_training

                if att_cor.is_training and att_cor.requested_status == "Present":
                    attendance.status = "Training"
                else:
                    attendance.status = att_cor.requested_status
            else:
                attendance.status = attendance.status
            attend_list.append(attendance)

        for ret_back_leave in return_back_sl_pl:
            return_back_the_sl_pl_to_employee(ret_back_leave["no_of_days"], ret_back_leave["profile"],
                                              leave_type=ret_back_leave["leave_type"])
        if len(attend_cor_list) > 0:
            AttendanceCorrectionHistory.objects.bulk_update(attend_cor_list,
                                                            ["correction_status", "approved_comment", "approved_by",
                                                             "approved_at"])
            Attendance.objects.bulk_update(attend_list, ['is_att_cor_req', "status", "is_training"])
        return Response({"message": "Approved attendance correction successfully"})

    except Exception as e:
        logger.info("exception at approve_correction_request {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllAttCorReqHistory(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllAttCorRequestSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"emp_name": "attendance__profile__full_name", "emp_id": "attendance__profile__emp_id",
                                "current_status": "attendance__status", "date": "attendance__date",
                                "att_cor_req_by_emp_id": "att_cor_req_by__emp_id",
                                "att_cor_req_by_name": "att_cor_req_by__full_name",
                                "approved_by_emp_id": "approved_by__emp_id",
                                "approved_by_name": "approved_by__full_name",
                                "to_be_approved_by_name": "att_cor_req_by__team__manager__full_name",
                                "to_be_approved_by_emp_id": "att_cor_req_by__team__manager__emp_id"
                                }

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        usr = request.user
        self.queryset = AttendanceCorrectionHistory.objects.filter(
            attendance__profile__is_active=True).filter(Q(att_cor_req_by=usr) | Q(approved_by=usr)).filter(
            **filter_by).filter(search_query).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


def format_att_row_with_date_range(attendance, att_dict, profile, dates_range):
    att_dict["EID"].append(profile.emp_id)
    att_dict["Name"].append(profile.full_name)
    att_dict["DOJ"].append(str(profile.date_of_joining) if profile.date_of_joining else None)
    att_dict["Status"].append(profile.status)
    att_dict["Department"].append(profile.designation.department.name) if profile.designation else None
    att_dict["Designation"].append(profile.designation.name) if profile.designation else None
    team = profile.sudo_team if profile.sudo_team else profile.team
    att_dict["Process"].append(team.base_team.name if team and team.base_team else None)
    att_dict["Team"].append(team.name if team else None)
    rm1 = team.manager if team and team.manager else None
    rm2 = rm1.team.manager if rm1 and rm1.team and rm1.team.manager else None
    rm3 = rm2.team.manager if rm2 and rm2.team and rm2.team.manager else None
    att_dict["RM1"].append(rm1.full_name if rm1 else None)
    att_dict["RM2"].append(rm2.full_name if rm2 else None)
    att_dict["RM3"].append(rm3.full_name if rm3 else None)
    att_dict["LWD"].append(str(profile.last_working_day) if profile.last_working_day else None)
    pro_att = attendance.filter(profile=profile)
    training_count = 0
    for date1 in dates_range:
        at_status = None
        at = pro_att.filter(date=date1).last()
        if at:
            at_status = at.status
            if at.is_training:
                training_count += 1
        att_dict[str(date1)].append(at_status)
    att_dict["Training"].append(training_count)
    return att_dict


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def download_all_att_report(request):
    try:
        today = datetime.today().date()
        team = request.data.get('team')
        base_team = request.data.get("base_team")
        start_date = request.data.get('start_date', today)
        end_date = request.data.get('end_date', today)
        if base_team is None:
            raise ValueError("Please select the proper department")
        if team is None and base_team != "all":
            raise ValueError("Please provide the team information")
        profiles = None
        attendances = None
        if team and team != 'all':
            try:
                team_obj = Team.objects.get(id=team, is_active=True)
            except Exception as e:
                raise ValueError("Invalid team id is provided")
            profiles = Profile.objects.filter(team=team_obj, is_superuser=False)
            attendances = Attendance.objects.filter(
                profile__team=team_obj, date__gte=start_date, date__lte=end_date,
                profile__is_superuser=False)

        elif team == 'all' and base_team != 'all':
            profiles = Profile.objects.filter(team__base_team=base_team, is_superuser=False)
            attendances = Attendance.objects.filter(profile__team__base_team=base_team, date__gte=start_date,
                                                    profile__is_superuser=False, date__lte=end_date)
        elif base_team == 'all':
            profiles = Profile.objects.filter(is_superuser=False)
            attendances = Attendance.objects.filter(date__gte=start_date, profile__is_superuser=False,
                                                    date__lte=end_date)
        if attendances is None or profiles is None:
            raise ValueError("Invalid input information")
        column_names = ["EID", "Name", "DOJ", "Status", "Department", "Designation", "Process", "Team", "RM1", "RM2",
                        "RM3", "Training", "LWD"]
        sel_dates = get_dates_range(datetime.fromisoformat(start_date).date(), datetime.fromisoformat(end_date).date())
        column_names = column_names + [str(i) for i in sel_dates]
        att_dict = {}
        for col in column_names:
            att_dict[col] = []
        for profile in profiles:
            format_att_row_with_date_range(attendances, att_dict, profile, sel_dates)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Attendance_report.csv"'
        writer = csv.writer(response)

        writer.writerow(column_names)

        for row in zip(*att_dict.values()):
            writer.writerow(row)

        return response
    except Exception as e:
        logger.info("exception at download_team_att_report {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def download_team_att_report(request):
    try:
        usr = request.user
        team_ids = get_team_ids(usr)
        today = datetime.today().date()

        if team_ids is None:
            raise ValueError("There is no team member under you")
        start_date = request.data.get('start_date', today)
        end_date = request.data.get('end_date', today)

        team = request.data.get('team')
        emp_ids = request.data.get("emp_ids")
        include_inactive_employees = parse_boolean_value(request.data.get("include_inactive_emp"))
        consider_active = False if include_inactive_employees else True
        try:
            profiles = get_selected_emp_under_team(usr, team, emp_ids, consider_active=consider_active)
        except Exception as e:
            raise ValueError(str(e) + " try refreshing the browser once and try again")

        attendances = Attendance.objects.filter(profile__id__in=list(profiles.values_list("id", flat=True)),
                                                date__gte=start_date, profile__is_superuser=False, date__lte=end_date)

        column_names = ["date", "Emp ID", "Emp Name", "Attendance", "Designation", "Department", "Manager", "Team",
                        "Process", "Training", "LWD"]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Attendance_report.csv"'

        writer = csv.writer(response)

        writer.writerow(column_names)

        for item in attendances:
            row = [get_formatted_date(item.date), item.profile.emp_id, item.profile.full_name, item.status,
                   item.profile.designation.name if item.profile and item.profile.designation else None,
                   item.profile.designation.department.name if item.profile.designation else None,
                   item.profile.team.manager.full_name if item.profile.team and item.profile.team.manager else None,
                   item.profile.team.name if item.profile.team else None,
                   item.profile.team.base_team.name if item.profile.team else None,
                   item.is_training, get_formatted_date(item.profile.last_working_day)]
            writer.writerow(row)

        return response
    except Exception as e:
        logger.info("exception at download_team_att_report {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_attendance_live_stats(request):
    try:
        emp = request.user
        my_team = get_team_ids(emp)
        if my_team is None:
            return HttpResponse(json.dumps({"message": "You do not manage any team"}))
        if is_management(emp):
            attendances = Attendance.objects.filter(date=datetime.today().date())
        else:
            attendances = Attendance.objects.filter(date=datetime.today().date()).filter(
                Q(profile__team__manager=emp) | Q(profile__team__manager__team__manager=emp) | Q(
                    profile__team__manager__team__manager__team__manager=emp))
        logged_in = attendances.filter(emp_start_time__isnull=False).count()
        scheduled = attendances.filter(status__in=["Present", "Scheduled", "Training", "Absent"]).count()
        emp_status = list(
            attendances.values("status").annotate(count=Count("status")).values_list("status", "count", named=True))
        out = {"logged_in": logged_in, "total_scheduled": scheduled}
        for stat in emp_status:
            out[stat[0]] = stat[1]

        return HttpResponse(json.dumps(out))

    except Exception as e:
        logger.info("exception at get_attendance_live_stats {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def schedule_correction(request):
    try:
        usr = request.user
        attendance_list = request.data.get("schedule")
        my_team = get_team_ids(usr)

        if my_team is None:
            raise ValueError("The employee is not under your team")
        attend_list = []
        for attendance in attendance_list:
            if attendance["status"] == "Week Off":
                attendance["start_time"] = attendance["end_time"] = "00:00:00"
            serialize_attendance = RequestForScheduleCorrectionSerializer(data=attendance)
            if not serialize_attendance.is_valid():
                return return_error_response(serialize_attendance, raise_exception=True)
            today = datetime.today().date()
            date_val = serialize_attendance.validated_data['date']
            stat = serialize_attendance.validated_data["status"]
            if stat not in ["Scheduled", "Week Off"]:
                raise ValueError("Only Scheduled and Week Off status is allowed")
            if date_val < today:
                raise ValueError("You can change schedule only for present day and future days")
            try:
                attendance['profile'] = Profile.objects.get(emp_id=attendance['emp_id'])
            except:
                raise ValueError("Provide valid emp_id")
            if date_val == datetime.today().date():
                attend_obj = Attendance.objects.filter(profile=attendance['profile'], date=date_val).last()
                if attend_obj:
                    if attend_obj.emp_start_time:
                        if attend_obj.emp_end_time:
                            raise ValueError(
                                "emp {0} cannot request for schedule correction, request for attendance correction".format(
                                    attend_obj.profile.emp_id))
                        else:
                            raise ValueError(
                                "emp {0} has already logged in cannot request for schedule correction".format(
                                    attend_obj.profile.emp_id))

            if attendance['profile'].team.id not in my_team and not is_management(usr):
                raise ValueError("emp-id {0} with team {1} doesn't belong to your team".format(
                    attendance['profile'].emp_id, attendance['profile'].team.name))

            attend_list.append(attendance)
        attend_list_objs = []
        for attend in attend_list:
            attend_obj = Attendance.objects.get(profile=attend['profile'], date=attend['date'])
            if not attend_obj.profile.status == "Active":
                raise ValueError("You cannot change Schedule as the employee is no longer Active.")
            if attend_obj.status == "PL":
                update_leave_balance(attend['profile'], "schedule correction by manager", 1)
            attend_obj.comment = attend["comment"]
            attend_obj.status = attend["status"]
            attend_obj.start_time = attend["start_time"]
            attend_obj.end_time = attend["end_time"]
            attend_obj.is_training = attend["is_training"]
            attend_obj.sch_upd_by = usr
            attend_list_objs.append(attend_obj)
        if len(attend_list_objs) > 0:
            Attendance.objects.bulk_update(attend_list_objs,
                                           ['comment', "status", "start_time", "end_time", "sch_upd_by", "is_training"])

        return Response({"message": "Schedule Correction successfully"})

    except Exception as e:
        logger.info("exception at schedule_correction {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def mark_absent_if_not_worked():
    yesterday = (datetime.today() - timedelta(hours=24)).date()
    # first_day_of_current_month = datetime.today().replace(day=1)
    attendances = Attendance.objects.filter(
        Q(status="Scheduled", date__lte=yesterday, date__month=yesterday.month, emp_start_time__isnull=True))
    # Q(status="Scheduled", date=today.date(), emp_start_time__isnull=True, end_time__lt=today.time()))
    # if today.day > 1:
    #     attendances2 = Attendance.objects.filter(Q(status="Scheduled", date__lte=first_day_of_current_month))
    #     attendances2.update(status="Absent", comment="RM1 did not mark the attendance")

    attendances.update(status="Absent", comment="Employee did not login")


def create_attendance_records(profile, year, month, days, existing_records):
    all_objs = []
    start_time = datetime.now()
    for pobj in profile:
        objs = []
        emp_id = pobj.emp_id
        for day in range(1, days + 1):
            if emp_id in existing_records and day in existing_records[emp_id]:
                continue
            objs.append(Attendance(status="Scheduled", date=date(year, month, day), profile=pobj))

        # print("emp_id=", emp_id)
        all_objs.extend(objs)
    Attendance.objects.bulk_create(all_objs)
    end_time = datetime.now()
    logger.info("total time took to execute {0}".format(end_time - start_time))


def get_formatted_existing_month_records(all_month_records):
    existing_records_list = list(all_month_records.values_list("profile__emp_id", "date__day"))
    existing_records = {}
    for i in existing_records_list:
        if i[0] in existing_records:
            existing_records[i[0]].append(i[1])
        else:
            existing_records[i[0]] = [i[1]]
    return existing_records


def create_att_calender(profile, attendance_list, date1, date2, att_status="Scheduled"):
    prev_days = get_dates_range(date1, date2)
    for prev_day in prev_days:
        attendance = Attendance.objects.filter(profile=profile, date=prev_day).last()
        if attendance is None:
            attendance_list.append(Attendance(profile=profile, date=prev_day, status=att_status))
    return attendance_list


def generate_attendance_calender():
    # evaluate the last_month records and create new records

    # status, date, emp_id
    # prev_days = [datetime.today().date() - timedelta(hours=24 * day) for day in days_list]
    date_of_joining = datetime.today().replace(year=2024, month=4, day=11)
    yesterday = (datetime.today() - timedelta(hours=24)).date()
    profiles = Profile.objects.filter(is_active=True, is_superuser=0)
    attendance_list = []

    for profile in profiles:
        # print(profile)

        new_date1 = date_of_joining.date()
        new_date1 = new_date1 if profile.date_of_joining < new_date1 else profile.date_of_joining
        attendance_list = create_att_calender(profile, attendance_list, new_date1, yesterday)
    if len(attendance_list) > 0:
        Attendance.objects.bulk_create(attendance_list)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def force_logout_attendance(request):
    try:
        emp_ids = request.data.get("emp_ids")
        message = "No changes made"
        for emp in emp_ids:
            emp = Profile.objects.filter(emp_id=emp).last()
            prev_attendance, login_status = get_login_status(emp)
            if not prev_attendance:
                raise ValueError("Employee is not logged in.")
            end_all_ongoing_break(request, prev_attendance, "Employee was force Logged out.")
            prev_attendance.emp_end_time = datetime.now().replace(microsecond=0)
            prev_attendance.is_self_marked = False
            h, m, s = get_diff_hours_minutes(prev_attendance.emp_start_time, prev_attendance.emp_end_time)
            h, m, s = format_hour_min_second(h, m, s)
            prev_attendance.total_time = f"{h}:{m}:{s}"
            prev_attendance.logged_out_by = request.user
            prev_attendance.save()
            message = "Employee Force Logged out Successfully"
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at force_logout_attendance {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def check_existing_ongoing_break(request, existing):
    latest = existing.latest('break_start_time')
    if not latest.break_end_time:
        return True, latest
    return False, None


def check_break_limit(request, existing, break_type):
    break_limit = MiscellaneousMiniFields.objects.filter(field="break_limit").last().content
    break_type_limited = list(
        MiscellaneousMiniFields.objects.filter(field='break_type_limited').values_list('content', flat=True))
    limited_break = [] if len(break_type_limited) == 0 else [i.strip() for i in str(break_type_limited[0]).split(",")]
    if break_type in limited_break and existing.filter(break_type__in=limited_break).count() >= int(break_limit):
        raise ValueError("Break limit reached already.")
    return None


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def toggle_break(request):
    try:
        emp = request.user
        data = request.data
        is_starting = data.get("is_starting")
        prev_attendance, _ = get_login_status(emp)
        break_type = data.get("break_type")
        if not prev_attendance:
            raise ValueError("You are not Logged in.")
        existing = Break.objects.filter(attendance=prev_attendance) or None
        if existing:
            # This is to End Break if any pending break exist
            ongoing, obj = check_existing_ongoing_break(request, existing)
            if is_starting and ongoing:
                raise ValueError("You have an ongoing Break.")
            if ongoing:
                comm = data.get("comment")
                obj.break_end_time = datetime.now()
                h, m, s = get_diff_hours_minutes(obj.break_start_time, obj.break_end_time)
                obj.total_time = f"{h}:{m}:{s}"
                obj.comment = comm if comm else None
                obj.save()
                check_and_log_suspicious_activity(request, prev_attendance, obj.break_type)
                return HttpResponse(json.dumps({"message": "Break Ended."}))
            check_break_limit(request, existing, break_type)
        data = update_request(data, profile=emp.id, break_start_time=datetime.now(), attendance=prev_attendance.id)
        serializer = BreakSerializer(data=data)
        if not serializer.is_valid():
            return_error_response(serializer, raise_exception=True)
        if not is_starting:
            raise ValueError("You have no ongoing Break. Try refreshing your browser in case of any errors")
        emp_break = serializer.create(serializer.validated_data)
        check_and_log_suspicious_activity(request, prev_attendance, break_type)
        return HttpResponse(json.dumps({"message": "Break Started."}))
    except Exception as e:
        logger.info("exception at toggle_break for emp {0} {1}".format(emp.emp_id, traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def break_status(request):
    try:
        emp = get_emp_by_emp_id(request.user.emp_id)
        prev_attendance, _ = get_login_status(emp)
        if not prev_attendance:
            return HttpResponse(json.dumps({}))
        existing = Break.objects.filter(attendance=prev_attendance) or None
        if existing:
            latest = existing.latest('break_start_time')
            ongoing = existing.filter(break_end_time=None)
            return HttpResponse(json.dumps({"existing": BreakSerializer(existing, many=True).data if existing else None,
                                            "ongoing": BreakSerializer(ongoing, many=True).data if ongoing else None}))
        return HttpResponse(json.dumps({}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllTeamBreak(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = BreakSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        emp = request.user
        my_team = get_team_ids(emp)

        mapping_column_names = {"emp_name": "profile__full_name", "emp_id": "profile__emp_id"}

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(
            request.GET, fields_look_up=mapping_column_names)

        if emp.designation.department.dept_id == "hr":
            self.queryset = Break.objects.filter().filter(**filter_by).filter(search_query).order_by(*order_by_cols)

        elif not my_team:
            self.queryset = []

        else:
            self.queryset = Break.objects.filter(
                Q(profile__team__manager__team__manager__team__manager=emp) | Q(
                    profile__team__manager__team__manager=emp) | Q(profile__team__manager=emp)).filter(
                **filter_by).filter(search_query).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


class GetConsolidatedAllTeamBreak(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = ConsolidatedBreakSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        emp = request.user
        my_team = get_team_ids(emp)

        mapping_column_names = {"emp_name": "profile__full_name", "emp_id": "profile__emp_id",
                                "date": "attendance__date", "rm1_name": "profile__team__manager__full_name",
                                "rm1_emp_id": "profile__team__manager__emp_id",
                                "process": "profile__team__base_team__name"}

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        # logger.info(f"order_by_cols, search_query, filter_by, {order_by_cols}, {search_query}, {filter_by}")
        if is_management(emp) or is_hr(emp) or is_cc(emp):
            base_queryset = Break.objects.filter(**filter_by).filter(search_query).order_by(
                *order_by_cols).values("attendance")  # Ensure only distinct records before pagination

        elif not my_team:
            base_queryset = []

        else:
            base_queryset = Break.objects.filter(Q(profile__team__manager__team__manager__team__manager=emp) | Q(
                profile__team__manager__team__manager=emp) | Q(profile__team__manager=emp)).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols).values(
                "attendance")  # Ensure only distinct records before pagination
        paginated_queryset = self.paginate_queryset(base_queryset)
        if not paginated_queryset:
            return self.get_paginated_response([])

        sql_query = f"""({get_group_concat_query_part("comment")}
                                 FROM ams_break
                                 WHERE ams_break.attendance_id = ams_attendance.id
                                   AND ams_break.break_type NOT IN ('Break 1', 'Break 2', 'Break 3'))
                      """
        attendance_ids = list(dict.fromkeys([entry['attendance'] for entry in paginated_queryset]))
        if len(order_by_cols) > 0:
            if 'id' in order_by_cols:
                order_by_cols.remove('id')
            if '-id' in order_by_cols:
                order_by_cols.remove('-id')

        filtered_queryset = Break.objects.filter(attendance__in=attendance_ids).values(
            "profile", "profile__emp_id", "profile__full_name", "profile__team__manager__full_name",
            "profile__team__manager__emp_id", "profile__team__base_team__name",
            # Include emp_id & full_name from Profile
            "attendance", "attendance__date"  # Include date from Attendance
        ).annotate(
            # Total Break 1,2,3 duration (Summed per attendance date)
            total_break_time=Coalesce(
                Cast(
                    Sum(
                        ExpressionWrapper(
                            F("break_end_time") - F("break_start_time"),
                            output_field=fields.DurationField()
                        ),
                        filter=Q(break_type__in=["Break 1", "Break 2", "Break 3", "Bio"])
                    ),
                    output_field=fields.DurationField()
                ),
                Value(timedelta(0))
            ),

            # Total duration of other breaks (Summed per attendance date)
            bio=Coalesce(
                Cast(
                    Sum(
                        ExpressionWrapper(
                            F("break_end_time") - F("break_start_time"),
                            output_field=fields.DurationField()
                        ),
                        filter=Q(break_type__in=["Bio"])
                    ),
                    output_field=fields.DurationField()
                ),
                Value(timedelta(0))
            ),
            team_huddle=Coalesce(
                Cast(
                    Sum(
                        ExpressionWrapper(
                            F("break_end_time") - F("break_start_time"),
                            output_field=fields.DurationField()
                        ),
                        filter=Q(break_type__in=["Team Huddle"])
                    ),
                    output_field=fields.DurationField()
                ),
                Value(timedelta(0))
            ),
            other=Coalesce(
                Cast(
                    Sum(
                        ExpressionWrapper(
                            F("break_end_time") - F("break_start_time"),
                            output_field=fields.DurationField()
                        ),
                        filter=Q(break_type__in=["Other"])
                    ),
                    output_field=fields.DurationField()
                ),
                Value(timedelta(0))
            ),

            # Get first & last timestamps per attendance date for each break type
            break1_start_time=Min("break_start_time", filter=Q(break_type="Break 1")),
            break1_end_time=Max("break_end_time", filter=Q(break_type="Break 1")),
            break1_comment=Min("comment", filter=Q(break_type="Break 1")),  # Fetch first available comment

            break2_start_time=Min("break_start_time", filter=Q(break_type="Break 2")),
            break2_end_time=Max("break_end_time", filter=Q(break_type="Break 2")),
            break2_comment=Min("comment", filter=Q(break_type="Break 2")),

            break3_start_time=Min("break_start_time", filter=Q(break_type="Break 3")),
            break3_end_time=Max("break_end_time", filter=Q(break_type="Break 3")),
            break3_comment=Min("comment", filter=Q(break_type="Break 3")),
            # Concatenate all "Other" break comments
            other_comment=Coalesce(
                Cast(RawSQL(sql_query, ()), TextField()),
                Value("", output_field=TextField())
            ),
        ).order_by(*order_by_cols)

        serializer = self.serializer_class(filtered_queryset, many=True)

        return self.get_paginated_response(serializer.data)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_attendance_correction_count(request, eom):
    emp = request.user
    my_team = get_team_ids(emp)
    timez = pytz.timezone('utc')
    four_days_prev_day = datetime.now(timez) - timedelta(days=4)
    eight_days_prev_day = datetime.now(timez) - timedelta(days=8)

    if not my_team and emp.designation.department.dept_id != "hr":
        return Response({"count": 0})
    if my_team is None:
        my_team = []
    if check_if_date_gte_25() and str(eom) == "1":
        if emp.designation.department.dept_id == "hr":
            correction_count = AttendanceCorrectionHistory.objects.filter(
                correction_status="Pending", created_at__date__gte=get_1st_date(),
                attendance__profile__is_active=True).filter(
                Q(created_at__lt=eight_days_prev_day) | Q(
                    att_cor_req_by__team__id__in=my_team,
                    created_at__date__lte=datetime.today().date())).count()
        else:
            correction_count = AttendanceCorrectionHistory.objects.filter(
                correction_status="Pending", created_at__date__gte=get_1st_date(),
                attendance__profile__is_active=True).filter(
                Q(att_cor_req_by__team__id__in=my_team,
                  created_at__date__lte=datetime.today().date())).count()
        return Response({"count": correction_count})

    if emp.designation.department.dept_id == "hr":
        correction_count = AttendanceCorrectionHistory.objects.filter(
            correction_status="Pending", created_at__date__gte=get_1st_date(),
            attendance__profile__is_active=True).filter(
            Q(created_at__lt=eight_days_prev_day) | Q(
                created_at__gte=eight_days_prev_day, created_at__lt=four_days_prev_day,
                att_cor_req_by__team__manager__team__manager=emp) | Q(
                att_cor_req_by__team__manager=emp, created_at__gte=four_days_prev_day,
                created_at__lte=datetime.now(timez))).count()
    else:
        correction_count = AttendanceCorrectionHistory.objects.filter(
            correction_status="Pending", created_at__date__gte=get_1st_date(),
            attendance__profile__is_active=True).filter(
            Q(created_at__date__gte=eight_days_prev_day, created_at__date__lt=four_days_prev_day,
              att_cor_req_by__team__manager__team__manager=emp) | Q(
                att_cor_req_by__team__manager=emp, created_at__date__gte=four_days_prev_day,
                created_at__date__lte=datetime.today().date())).count()
    return Response({"count": correction_count})


def handle_manual_attendance_creation(request, att_status, update=False, create_type="MSC"):
    usr = request.user
    emp_ids = request.data.get("emp_ids")
    profiles = Profile.objects.filter(emp_id__in=str(emp_ids).split(","))
    start_date = request.data.get("start_date")
    end_date = request.data.get("end_date")
    comment = request.data.get("comment")
    week_offs = split_week_off_and_return(request)
    start_time = request.data.get("start_time", "00:00:00")
    end_time = request.data.get("end_time", "00:00:00")
    is_training = request.data.get("is_training")
    is_training = parse_boolean_value(is_training)
    if comment is None or str(comment).strip() == "":
        raise ValueError("please provide comment")
    cr_attendance_list = []
    up_attendance_list = []
    week_offs_str = " ".join(str(wo) for wo in week_offs)
    actions = []
    sc_list = []
    if profiles.count() > 0:
        for profile in profiles:
            new_schedule = False
            leave_balance = LeaveBalance.objects.get(profile=profile)
            att_days = get_dates_range(datetime.fromisoformat(start_date), datetime.fromisoformat(end_date))
            for att_day in att_days:
                attendance = Attendance.objects.filter(profile=profile, date=att_day).last()
                if att_day.strftime("%A") in week_offs:
                    stat = "Week Off"
                else:
                    stat = att_status

                if attendance is None:
                    cr_attendance_list.append(
                        Attendance(profile=profile, date=att_day, status=stat, sch_upd_by=usr, is_training=is_training,
                                   comment="MAC " + comment, start_time=start_time, end_time=end_time))
                    new_schedule = True

                else:
                    if update:
                        attendance.status = stat
                        attendance.sch_upd_by = usr
                        attendance.comment = "MAU " + comment
                        attendance.start_time = start_time
                        attendance.end_time = end_time
                        up_attendance_list.append(attendance)
            if new_schedule:
                sc_list.append(
                    Schedule(profile=profile, start_date=start_date, end_date=end_date, start_time=start_time,
                             end_time=end_time, week_off=week_offs_str, comment="missing schedule creation",
                             created_by=usr, is_training=is_training, create_type=create_type, emp_id=profile.emp_id,
                             rm1_id=profile.team.manager.emp_id, created_by_emp_id=usr.emp_id))
            if stat=="SL":
                data={"start_date":start_date,"end_date":end_date,"reason":f"Manual_attendance {comment}","leave_type":"SL","profile":profile.id}
                leave_serializer=CreateLeaveSerializer(data=data)
                if not leave_serializer.is_valid():
                    return_error_response(leave_serializer, raise_exception=True)
                s_end_date = leave_serializer.validated_data.get('end_date')
                s_start_date = leave_serializer.validated_data.get('start_date')
                no_of_days = (s_end_date - s_start_date).days + 1

                if not leave_balance.sick_leaves >= no_of_days:
                    raise ValueError(
                        f"Profile emp -{profile.emp_id} don't have sufficient leave balance to apply for leave")
                leave_serializer.validated_data['no_of_days'] = no_of_days
                leave_serializer.validated_data['status'] = 'Approved'
                leave_serializer.validated_data["tl_status"]='Approved'
                leave_serializer.validated_data["manager_status"]='Approved'
                leave_serializer.validated_data["tl_comments"]="Manual attendance sl approved"
                leave_serializer.validated_data["manager_comments"]="Manual attendance sl approved"
                leave_serializer.validated_data["approved_by1"]=usr
                leave_serializer.validated_data["approved_by2"]=usr

                leave = leave_serializer.create(leave_serializer.validated_data)
                deduct_the_leaves_from_employee(leave, leave_balance, "Manual SL Applied")

            if stat=="PL":
                data = {"start_date": start_date, "end_date": end_date, "reason": f"Manual_attendance {comment}",
                        "leave_type": "PL", "profile": profile.id}
                leave_serializer = CreateLeaveSerializer(data=data)
                if not leave_serializer.is_valid():
                    return_error_response(leave_serializer, raise_exception=True)
                s_end_date = leave_serializer.validated_data.get('end_date')
                s_start_date = leave_serializer.validated_data.get('start_date')
                no_of_days = (s_end_date - s_start_date).days + 1
                if not leave_balance.paid_leaves >= no_of_days:
                    raise ValueError(f"Profile emp -{profile.emp_id} don't have sufficient leave balance to apply for leave")
                leave_serializer.validated_data['no_of_days'] = no_of_days
                leave_serializer.validated_data['status'] = 'Approved'
                leave_serializer.validated_data["tl_status"] = 'Approved'
                leave_serializer.validated_data["manager_status"] = 'Approved'
                leave_serializer.validated_data["tl_comments"] = "Manual attendance pl approved"
                leave_serializer.validated_data["manager_comments"] = "Manual attendance pl approved"
                leave_serializer.validated_data["approved_by1"] = usr
                leave_serializer.validated_data["approved_by2"] = usr

                leave = leave_serializer.create(leave_serializer.validated_data)
                deduct_the_leaves_from_employee(leave, leave_balance, "Manual PL Applied")


        if len(cr_attendance_list) > 0:
            Attendance.objects.bulk_create(cr_attendance_list)
            actions.append("create")
        if update and len(up_attendance_list) > 0:
            Attendance.objects.bulk_update(up_attendance_list, ["sch_upd_by", "status", "comment"])
            actions.append("update")
        if len(sc_list) > 0:
            Schedule.objects.bulk_create(sc_list)
    return actions

def direct_handle_manual_attendance_creation(request, att_status, update=False, create_type="MSC"):
    usr = request.user
    emp_id = request.data.get("emp_id")
    profile = Profile.objects.filter(emp_id=str(emp_id)).first()
    start_date = request.data.get("start_date")
    end_date = request.data.get("end_date")
    comment = request.data.get("comment")
    # week_offs = split_week_off_and_return(request)
    start_time = request.data.get("start_time", "00:00:00")
    end_time = request.data.get("end_time", "00:00:00")
    is_training = True if att_status=="Training" else False
    # is_training = parse_boolean_value(is_training)
    if comment is None or str(comment).strip() == "":
        raise ValueError("please provide comment")
    cr_attendance_list = []
    up_attendance_list = []
    # week_offs_str = " ".join(str(wo) for wo in week_offs)
    actions = []
    sc_list = []

    new_schedule = False
    leave_balance = LeaveBalance.objects.get(profile=profile)
    att_days = get_dates_range(datetime.fromisoformat(start_date), datetime.fromisoformat(end_date))
    for att_day in att_days:
        attendance = Attendance.objects.filter(profile=profile, date=att_day).last()
        # if att_day.strftime("%A") in week_offs:
        #     stat = "Week Off"
        # else:

        stat = att_status

        if attendance is None:
            cr_attendance_list.append(
                Attendance(profile=profile, date=att_day, status=stat, sch_upd_by=usr, is_training=is_training,
                           comment="MAC " + comment, start_time=start_time, end_time=end_time))
            new_schedule = True

        else:
            if update:
                attendance.status = stat
                attendance.sch_upd_by = usr
                attendance.comment = "MAU " + comment
                attendance.start_time = start_time
                attendance.end_time = end_time
                up_attendance_list.append(attendance)
    if new_schedule:
        sc_list.append(
            Schedule(profile=profile, start_date=start_date, end_date=end_date, start_time=start_time,
                     end_time=end_time, comment="missing schedule creation",
                     created_by=usr, is_training=is_training, create_type=create_type, emp_id=profile.emp_id,
                     rm1_id=profile.team.manager.emp_id, created_by_emp_id=usr.emp_id))
    if stat not in["SL","PL"]:
        #If applying other than sl and pl - withdrawn sl and pl if already sl and pl applied
        already_applied_leaves=Leave.objects.filter(profile=profile,start_date__gte=start_date,end_date__lte=end_date)
        for leave in already_applied_leaves:
            return_back_the_leaves_to_employee(leave, leave_balance, "Manual attendance Leave Withdrawn")
            leave.status = 'Withdrawn'
            leave.save()

    if stat=="SL":
        already_sl_applied_leaves = Leave.objects.filter(profile=profile, start_date__gte=start_date,
                                                         end_date__lte=end_date, leave_type="SL")
        if already_sl_applied_leaves:
            raise ValueError(f"SL already applied for this date range-{start_date} -> {end_date} ")

        #While applying SL - withdrawn already applied PL
        already_pl_applied_leaves = Leave.objects.filter(profile=profile, start_date__gte=start_date, end_date__lte=end_date,leave_type="PL")
        for leave in already_pl_applied_leaves:
            return_back_the_leaves_to_employee(leave, leave_balance, "Manual attendance Leave Withdrawn")
            leave.status = 'Withdrawn'
            leave.save()
        data={"start_date":start_date,"end_date":end_date,"reason":f"Manual_attendance {comment}","leave_type":"SL","profile":profile.id}
        leave_serializer=CreateLeaveSerializer(data=data)
        if not leave_serializer.is_valid():
            return_error_response(leave_serializer, raise_exception=True)
        s_end_date = leave_serializer.validated_data.get('end_date')
        s_start_date = leave_serializer.validated_data.get('start_date')
        no_of_days = (s_end_date - s_start_date).days + 1

        if not leave_balance.sick_leaves >= no_of_days:
            raise ValueError(
                f"Profile emp -{profile.emp_id} don't have sufficient leave balance to apply for leave")
        leave_serializer.validated_data['no_of_days'] = no_of_days
        leave_serializer.validated_data['status'] = 'Approved'
        leave_serializer.validated_data["tl_status"]='Approved'
        leave_serializer.validated_data["manager_status"]='Approved'
        leave_serializer.validated_data["tl_comments"]="Manual attendance sl approved"
        leave_serializer.validated_data["manager_comments"]="Manual attendance sl approved"
        leave_serializer.validated_data["approved_by1"]=usr
        leave_serializer.validated_data["approved_by2"]=usr

        leave = leave_serializer.create(leave_serializer.validated_data)
        deduct_the_leaves_from_employee(leave, leave_balance, "Manual SL Applied")

    if stat=="PL":
        already_pl_applied_leaves = Leave.objects.filter(profile=profile, start_date__gte=start_date,
                                                         end_date__lte=end_date, leave_type="PL")
        if already_pl_applied_leaves:
            raise ValueError(f"PL already applied for this date range-{start_date} -> {end_date} ")
        # While applying PL - withdrawn already applied SL
        already_sl_applied_leaves = Leave.objects.filter(profile=profile, start_date__gte=start_date,
                                                         end_date__lte=end_date, leave_type="SL")
        for leave in already_sl_applied_leaves:
            return_back_the_leaves_to_employee(leave, leave_balance, "Manual attendance Leave Withdrawn")
            leave.status = 'Withdrawn'
            leave.save()
        data = {"start_date": start_date, "end_date": end_date, "reason": f"Manual_attendance {comment}",
                "leave_type": "PL", "profile": profile.id}
        leave_serializer = CreateLeaveSerializer(data=data)
        if not leave_serializer.is_valid():
            return_error_response(leave_serializer, raise_exception=True)
        s_end_date = leave_serializer.validated_data.get('end_date')
        s_start_date = leave_serializer.validated_data.get('start_date')
        no_of_days = (s_end_date - s_start_date).days + 1
        if not leave_balance.paid_leaves >= no_of_days:
            raise ValueError(f"Profile emp -{profile.emp_id} don't have sufficient leave balance to apply for leave")
        leave_serializer.validated_data['no_of_days'] = no_of_days
        leave_serializer.validated_data['status'] = 'Approved'
        leave_serializer.validated_data["tl_status"] = 'Approved'
        leave_serializer.validated_data["manager_status"] = 'Approved'
        leave_serializer.validated_data["tl_comments"] = "Manual attendance pl approved"
        leave_serializer.validated_data["manager_comments"] = "Manual attendance pl approved"
        leave_serializer.validated_data["approved_by1"] = usr
        leave_serializer.validated_data["approved_by2"] = usr

        leave = leave_serializer.create(leave_serializer.validated_data)
        deduct_the_leaves_from_employee(leave, leave_balance, "Manual PL Applied")


    if len(cr_attendance_list) > 0:
        Attendance.objects.bulk_create(cr_attendance_list)
        actions.append("create")
    if update and len(up_attendance_list) > 0:
        Attendance.objects.bulk_update(up_attendance_list, ["sch_upd_by", "status", "comment"])
        actions.append("update")
    if len(sc_list) > 0:
        Schedule.objects.bulk_create(sc_list)
    return actions




@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_schedule_manually(request):
    try:
        actions = handle_manual_attendance_creation(request, "Scheduled")
        message = "no changes made"
        if len(actions) > 0:
            message = "Default schedule creation is successful"
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info(f"exception at create_schedule_manually {traceback.format_exc(5)}")
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def direct_attendance_marking_by_cc(request):
    try:
        emp_ids = request.data.get("emp_ids", "").split(",")
        create_type = "CCU"
        if str(request.user.emp_id) == "2907":
            create_type = "HBU"
            if len(emp_ids) != 1 or ("2907" not in emp_ids):
                raise ValueError("You can mark only your attendance")

        actions = handle_manual_attendance_creation(request, request.data.get("status"), update=True,
                                                    create_type=create_type)
        message = "Attendance " + " ".join(i for i in actions) + " done successfully" if len(
            actions) > 0 else "no changes done"
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info(f"exception at direct_attendance_marking_by_cc {traceback.format_exc(5)}")
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)



@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def direct_attendance_marking(request):
    try:
        emp_ids = request.data.get("emp_ids", "").split(",")
        create_type = "CCU"
        actions = direct_handle_manual_attendance_creation(request, request.data.get("status"), update=True,
                                                    create_type=create_type)
        message = "Attendance updated successfully."
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info(f"exception at direct_attendance_marking_by_cc {traceback.format_exc(5)}")
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)

def get_break_duration(att, limited_breaks):
    breaks = list(
        Break.objects.filter(attendance=att, break_type__in=limited_breaks).values_list("total_time", flat=True))
    return str(timedelta(
        seconds=sum(
            map(lambda x: sum(int(i) * 60 ** j for j, i in enumerate(reversed(x.split(':')))) if x is not None else 0,
                breaks))))


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_checkin_report(request):
    try:
        three_days = datetime.today().date() - timedelta(days=3)
        # last_retrieved = MiscellaneousMiniFields.objects.filter(field="cico_report_last_day").last()

        # start_date = datetime.today().date().replace(year=2023, month=12, day=1)
        # if last_retrieved:
        #     start_date = datetime.fromisoformat(last_retrieved.content)
        #     last_retrieved.content = str(three_days)
        #     logger.info("pbi cico last_retrieved {0}".format(last_retrieved.content))
        team = request.data.get('team')
        base_team = request.data.get("base_team")
        if base_team is None:
            raise ValueError("Please select the proper department")
        if team is None and base_team != "all":
            raise ValueError("Please provide the team information")

        today = datetime.today().date()
        start_date = request.data.get('start_date', today)
        end_date = request.data.get('end_date', today)
        limited_breaks = get_limited_breaks()
        profiles = None
        attendances = None

        if team and team != 'all':
            try:
                team_obj = Team.objects.get(id=team, is_active=True)
            except Exception as e:
                raise ValueError("Invalid team id is provided")
            profiles = Profile.objects.filter(team=team_obj, is_superuser=False)
            attendances = Attendance.objects.filter(
                profile__team=team_obj, date__gte=start_date, date__lte=end_date,
                profile__is_superuser=False).filter(
                Q(emp_start_time__isnull=False) | Q(emp_end_time__isnull=False))

        elif team == 'all' and base_team != 'all':
            profiles = Profile.objects.filter(team__base_team=base_team, is_superuser=False)
            attendances = Attendance.objects.filter(profile__team__base_team=base_team, date__gte=start_date,
                                                    profile__is_superuser=False, date__lte=end_date).filter(
                Q(emp_start_time__isnull=False) | Q(emp_end_time__isnull=False))
        elif base_team == 'all':
            profiles = Profile.objects.filter(is_superuser=False)
            attendances = Attendance.objects.filter(date__gte=start_date, profile__is_superuser=False,
                                                    date__lte=end_date).filter(
                Q(emp_start_time__isnull=False) | Q(emp_end_time__isnull=False))
        if attendances is None or profiles is None:
            raise ValueError("Invalid input information")

        # attendance = Attendance.objects.filter(date__gte=start_date, date__lte=end_date)
        # if last_retrieved is None:
        #     MiscellaneousMiniFields.objects.create(content=str(three_days), field="cico_report_last_day")
        # else:
        #     last_retrieved.save()
        column_names = ["emp_id", "process", "date", "emp_start_time", "emp_end_time", "break_duration", "total_time",
                        "start_time", "end_time"]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Checkin checkout report.csv"'
        writer = csv.writer(response)

        writer.writerow(column_names)

        for attend in attendances:
            row = [attend.profile.emp_id if attend.profile else None,
                   attend.profile.team.base_team.name if attend.profile and attend.profile.team and attend.profile.team.base_team else None,
                   attend.date,
                   attend.emp_start_time.astimezone(tz) if attend.emp_start_time else None,
                   attend.emp_end_time.astimezone(tz) if attend.emp_end_time else None,
                   get_break_duration(attend, limited_breaks),
                   attend.total_time,
                   attend.start_time, attend.end_time]
            writer.writerow(row)

        return response
    except Exception as e:
        logger.info("exception at get_checkin_report {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_leave_balance_history_report(request):
    try:
        today = datetime.today().date()
        start_date = request.data.get('start_date', today)
        end_date = request.data.get('end_date', today)
        leave_balance_history = LeaveBalanceHistory.objects.filter(date__gte=start_date, date__lte=end_date)
        # if last_retrieved is None:
        #     MiscellaneousMiniFields.objects.create(content=str(three_days), field="cico_report_last_day")
        # else:
        #     last_retrieved.save()
        column_names = ["emp_id", "full_name", "process", "date", "transaction", "no_of_days", "sl_balance",
                        "pl_balance", "total"]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="leave balance history report.csv"'
        writer = csv.writer(response)

        writer.writerow(column_names)

        for lbh in leave_balance_history:
            row = [lbh.profile.emp_id if lbh.profile else None,
                   lbh.profile.full_name,
                   lbh.profile.team.base_team.name if lbh.profile and lbh.profile.team and lbh.profile.team.base_team else None,
                   lbh.date.strftime("%Y-%m-%d"),
                   lbh.leave_type,
                   lbh.transaction,
                   lbh.no_of_days,
                   lbh.sl_balance,
                   lbh.pl_balance,
                   lbh.total]
            writer.writerow(row)

        return response
    except Exception as e:
        logger.info("exception at get_leave_balance_history_report {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def suspicious_activity_report(request):
    try:
        today = datetime.today().date()
        start_date = request.data.get('start_date', today)
        end_date = request.data.get('end_date', today)
        sus_activity = SuspiciousLoginActivity.objects.filter(created_at__gte=start_date, created_at__lte=end_date)
        column_names = ["date_time", "emp_id", "full_name", "process", "activity", "designation", "rm1_emp_id",
                        "rm1_name", "logged_in_ip", "other_ip_address", ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Suspicious activity report.csv"'
        writer = csv.writer(response)

        writer.writerow(column_names)

        for activity in sus_activity:
            profile = activity.attendance.profile
            manager = profile.team.manager if profile and profile.team and profile.team.manager else None
            row = [str(activity.created_at), profile.emp_id if profile else None,
                   profile.full_name if profile else None,
                   profile.team.base_team.name if profile and profile.team and profile.team.base_team else None,
                   activity.activity_type, profile.designation.name if profile else None,
                   manager.emp_id if manager else None, manager.full_name if manager else None,
                   activity.logged_in_ip, activity.other_ip_address]
            writer.writerow(row)

        return response
    except Exception as e:
        logger.info("exception at suspicious_activity_report {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def add_holiday(request):
    try:
        logger.info(f"data {request.data}")
        usr = request.user
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        comment = request.data.get("comment")
        if start_date is None or end_date is None:
            raise ValueError("Provide proper start date and end date")
        is_training = request.data.get("is_training")
        holiday_type = request.data.get("holiday_type")
        is_training = parse_boolean_value(is_training)
        if comment is None or str(comment).strip() == "":
            raise ValueError("please provide comment")
        cr_attendance_list = []
        up_attendance_list = []
        actions = []
        sc_list = []
        team_ids = get_team_ids(usr)
        if team_ids is None:
            raise ValueError("There is no team member under you")

        team = request.data.get('team')
        emp_ids = request.data.get("emp_ids")
        try:
            profiles = get_selected_emp_under_team(usr, team, emp_ids)
        except Exception as e:
            raise ValueError(str(e) + " try refreshing the browser once and try again")

        allowed_holidays = [i[0] for i in settings.AMS_MARK_HOLIDAY]
        if holiday_type not in allowed_holidays:
            raise ValueError(f"Allowed holiday options are {', '.join(allowed_holidays)}")
        att_days = get_dates_range(datetime.fromisoformat(start_date), datetime.fromisoformat(end_date))
        start_date1 = att_days[0].date()
        if start_date1 <= datetime.now().date():
            raise ValueError("Start date must be future date")

        stat = holiday_type

        if profiles.count() > 0:
            for profile in profiles:
                new_schedule = False
                for att_day in att_days:
                    attendance = Attendance.objects.filter(profile=profile, date=att_day).last()

                    if attendance is None:
                        cr_attendance_list.append(
                            Attendance(profile=profile, date=att_day, status=stat, sch_upd_by=usr,
                                       comment="MAC " + comment, start_time="00:00:00", end_time="00:00:00"))
                        new_schedule = True
                    else:
                        if attendance.status == "Scheduled":
                            attendance.status = stat
                            attendance.sch_upd_by = usr
                            attendance.comment = "GEN " + comment
                            up_attendance_list.append(attendance)
                if new_schedule:
                    sc_list.append(
                        Schedule(profile=profile, start_date=start_date, end_date=end_date, start_time="00:00:00",
                                 end_time="00:00:00", week_off="", comment="holiday schedule creation",
                                 created_by=usr, create_type="GEN", emp_id=profile.emp_id,
                                 rm1_id=profile.team.manager.emp_id, created_by_emp_id=usr.emp_id))

            if len(cr_attendance_list) > 0:
                Attendance.objects.bulk_create(cr_attendance_list)
                actions.append("create")
            if len(up_attendance_list) > 0:
                Attendance.objects.bulk_update(up_attendance_list, ["sch_upd_by", "status", "comment"])
                actions.append("update")
            if len(sc_list) > 0:
                Schedule.objects.bulk_create(sc_list)
        return Response({"message": f"Schedule updated successfully"})
    except Exception as e:
        logger.info("exception at suspicious_activity_report {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


import csv
from django.http import HttpResponse
from django.utils.dateparse import parse_datetime
from .models import AttendanceLog


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def exportTurnstileReport(request):
    data = request.data
    from_date = data.get('start_date')
    to_date = data.get('end_date')

    if not from_date or not to_date:
        return HttpResponse("Missing from_date or to_date", status=400)

    try:
        from_dt = parse_datetime(from_date)
        to_dt = parse_datetime(to_date)
    except Exception:
        return HttpResponse("Invalid date format", status=400)

    logs = AttendanceLog.objects.filter(timestamp__range=(from_dt, to_dt)).order_by('timestamp')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=attendance_logs.csv'

    writer = csv.writer(response)
    writer.writerow(['User ID', 'User Name', 'Timestamp', 'Status', 'Device IP', 'Entry Type'])

    for log in logs:
        writer.writerow([
            log.user_id,
            log.user_name,
            localtime(log.timestamp),
            log.status,
            log.device_ip,
            log.entry_type
        ])

    return response


class GetAllBiometricLog(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = AttendanceLogSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {}

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(
            request.GET, fields_look_up=mapping_column_names)

        self.queryset = AttendanceLog.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)



class BulkAttendanceRangeUpdateView(APIView):
    def post(self, request):
        serializer = BulkRangeAttendanceUpdateSerializer(data=request.data)
        if serializer.is_valid():
            emp_ids = serializer.validated_data['emp_ids']
            start_date = serializer.validated_data['start_date']
            end_date = serializer.validated_data['end_date']

            profiles = Profile.objects.filter(emp_id__in=emp_ids)
            found_emp_ids = set(p.emp_id for p in profiles)
            not_found = [eid for eid in emp_ids if eid not in found_emp_ids]

            updated_records = []

            for profile in profiles:
                attendances = Attendance.objects.filter(
                    profile=profile,
                    date__range=(start_date, end_date)
                ).exclude(status="Week Off")

                for attendance in attendances:
                    # Random start time between 9:45 and 10:00 AM
                    start_offset = random.randint(0, 15)
                    emp_start_time = datetime.combine(attendance.date, time(9, 45)) + timedelta(minutes=start_offset)

                    # Random duration between 9:00 and 9:10 hours
                    extra_minutes = random.randint(0, 10)
                    emp_end_time = emp_start_time + timedelta(hours=9, minutes=extra_minutes)

                    # Format total_time as "H:MM"
                    total_seconds = (emp_end_time - emp_start_time).seconds
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    total_time_str = f"{hours}:{minutes:02d}"

                    # Set fixed working hours
                    attendance.start_time = time(10, 0)
                    attendance.end_time = time(19, 0)

                    # Save all fields
                    attendance.emp_start_time = emp_start_time
                    attendance.emp_end_time = emp_end_time
                    attendance.total_time = total_time_str
                    attendance.save()

                    updated_records.append({
                        "emp_id": profile.emp_id,
                        "date": attendance.date,
                        "attendance_id": attendance.id,
                        "emp_start_time": emp_start_time,
                        "emp_end_time": emp_end_time,
                        "total_time": total_time_str,
                        "start_time": attendance.start_time,
                        "end_time": attendance.end_time
                    })

            return Response({
                "message": f"Attendance updated for {len(updated_records)} record(s).",
                "updated": updated_records,
                "not_found_emp_ids": not_found
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def download_leave_report(request):
    try:
        # applied - 1 to 30 --leave  ---
        # user filter prevoius 28 to 15
        # expecting----1--15 days should get
        today = datetime.today().date()
        start_date = request.data.get('start_date', today)
        end_date = request.data.get('end_date', today)
        leaves = Leave.objects.filter(start_date__lte=end_date, end_date__gte=start_date)
        # if last_retrieved is None:
        #     MiscellaneousMiniFields.objects.create(content=str(three_days), field="cico_report_last_day")
        # else:
        #     last_retrieved.save()
        column_names = ["start_date", "end_date", "process", "team", "emp_name", "emp_id", "rm1_name", "rm1_id",
                        "rm2_name", "rm2_id", "status", "sl/pl", "days",
                        "rm1_status", "rm1_comment", "rm2_status", "rm2_comment",
                        ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="leaves report.csv"'
        writer = csv.writer(response)

        writer.writerow(column_names)

        for lv in leaves:
            rm1 = lv.profile.team.manager if lv.profile and lv.profile.team and lv.profile.team.manager else None
            rm2 = rm1.team.manager if rm1 and rm1.team and rm1.team.manager else None
            row = [lv.start_date.strftime("%Y-%m-%d"), lv.end_date.strftime("%Y-%m-%d"),
                   lv.profile.team.base_team.name if lv.profile and lv.profile.team and lv.profile.team.base_team else None,
                   lv.profile.team.name if lv.profile and lv.profile.team else None,
                   lv.profile.full_name if lv.profile else None,
                   lv.profile.emp_id if lv.profile else None,
                   rm1.full_name if rm1 else None,
                   rm1.emp_id if rm1 else None,
                   rm2.full_name if rm2 else None,
                   rm2.emp_id if rm2 else None,
                   lv.status,
                   lv.leave_type,
                   lv.no_of_days,
                   lv.tl_status,
                   lv.tl_comments,
                   lv.manager_status,
                   lv.manager_comments]
            writer.writerow(row)

        return response
    except Exception as e:
        logger.info("exception at get_leaves_report {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)




@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_mcl(request, emp_id):
    try:
        profile = get_emp_by_emp_id(emp_id)
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        attendances = Attendance.objects.filter(profile=profile, date__gte=start_date, date__lte=end_date)
        create_or_update_attendance(datetime.fromisoformat(start_date), datetime.fromisoformat(end_date), attendances,
                                    profile, request.user, "MCL")
        attendances.update(status="MCL")
        return HttpResponse(json.dumps({"message": "Updated Miscarriage leave successfully"}))
    except Exception as e:
        logger.info("exception at update_mcl {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
