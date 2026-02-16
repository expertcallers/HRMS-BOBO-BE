import traceback

from django.http import HttpResponse
import json
from datetime import datetime, timedelta, date
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from ams.views import deduct_the_leaves_from_employee
from mapping.views import HasUrlPermission
from ams.models import LeaveBalance, LeaveBalanceHistory
from mapping.models import Profile
from utils.util_classes import CustomTokenAuthentication
from .models import Resignation, ResignationHistory, ExitFeedbackInterview, ExitChecklist, FinalApprovalChecklist
from .serializers import CreateResignationSerializer, ViewResignationSerializer, ResignationStatusSerializer, \
    ApproveResignationSerializer, UpdateNoticePeriodSerializer, ResignationHistorySerializer, \
    SubmitExitFeedbackSerializer, ViewExitFeedbackSerializer, ExitChecklistSerializer, FinalApprovalSerializer, \
    ViewApprovalSerializer, HRApproveResignationSerializer
from utils.utils import return_error_response, update_request, get_sort_and_filter_by_cols, get_formatted_name, \
    get_team_ids, parse_boolean_value

logger = logging.getLogger(__name__)


def add_resignation_history(resign, transaction, message):
    ResignationHistory.objects.create(resignation=resign, transaction=transaction, message=message,
                                      created_at=datetime.now())
    return None


def get_resignation_by_id(resign_id):
    if resign_id is None:
        raise ValueError("Provide valid ID")
    try:
        resignation_obj = Resignation.objects.get(id=resign_id)
    except:
        raise ValueError("Resignation with this ID doesn't exist.")
    return resignation_obj


def get_notice_period_days_as_per_doj_and_start_date(doj, start_date):
    after_6th_month = doj + timedelta(days=180)
    if start_date >= after_6th_month:
        return 30
    return 7


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def apply_resignation(request):
    try:
        usr = request.user
        data = update_request(request.data, applied_by=usr.id)
        status_in = ['Approved', 'Pending', 'Terminated']
        existing = Resignation.objects.filter(applied_by__emp_id=usr.emp_id, resignation_status__in=status_in)
        if existing:
            raise ValueError("You are not allowed to Apply for Resignation.")
        serializer = CreateResignationSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        start_date = serializer.validated_data["start_date"]
        notice_period = get_notice_period_days_as_per_doj_and_start_date(usr.date_of_joining, start_date)
        serializer.validated_data["notice_period_in_days"] = notice_period

        if start_date < datetime.today().date():
            raise ValueError("Start date can't be a past date.")

        serializer.validated_data["exit_date"] = start_date + timedelta(days=notice_period - 1)
        serializer.validated_data["resignation_status"] = "Pending"
        resignation = serializer.create(serializer.validated_data)
        add_resignation_history(resignation, transaction="Resignation Applied",
                                message="Resignation applied by '{0}' on {1} effective from {2}".format(
                                    get_formatted_name(request.user), datetime.today().date(), start_date))
        resignation = ViewResignationSerializer(resignation).data
        return HttpResponse(json.dumps({"resignation": resignation}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def get_resignation_status(request):
    try:
        resignation_obj = Resignation.objects.filter(applied_by__emp_id=request.user.emp_id).last()
        if not resignation_obj:
            return HttpResponse(json.dumps({}))
        if not resignation_obj.applied_by.id == request.user.id:
            raise ValueError("You are not authorized to see the Resignation Status.")
        resignation_status = ResignationStatusSerializer(resignation_obj).data
        return HttpResponse(json.dumps({"status": resignation_status}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetmyTeamAppliedResignation(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = ViewResignationSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"applied_by_emp_id": "applied_by__emp_id", "applied_by_name": "applied_by__full_name",
                                "accepted_or_rejected_by_emp_id": "accepted_or_rejected_by__emp_id",
                                "accepted_or_rejected_by_name": "accepted_or_rejected_by__full_name",
                                "hr_accepted_or_rejected_by_emp_id": "hr_accepted_or_rejected_by__emp_id",
                                "hr_accepted_or_rejected_by_name": "hr_accepted_or_rejected_by__full_name",
                                "applied_by_designation": "applied_by__designation__name",
                                "applied_by_process": "applied_by__team__base_team__name",
                                }

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        usr = request.user
        my_team = get_team_ids(usr)
        if my_team is None:
            self.queryset = []
        else:
            self.queryset = Resignation.objects.filter(applied_by__team__in=my_team).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


class GetAllApproveAppliedResignation(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = ViewResignationSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"applied_by_emp_id": "applied_by__emp_id", "applied_by_name": "applied_by__full_name",
                                "accepted_or_rejected_by_emp_id": "accepted_or_rejected_by__emp_id",
                                "accepted_or_rejected_by_name": "accepted_or_rejected_by__full_name",
                                "hr_accepted_or_rejected_by_emp_id": "hr_accepted_or_rejected_by__emp_id",
                                "hr_accepted_or_rejected_by_name": "hr_accepted_or_rejected_by__full_name"}

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        dept_id = request.user.designation.department.dept_id
        resignations = Resignation.objects.filter(resignation_status__in=["Approved", "Terminated"])
        if dept_id == "admin":
            self.queryset = resignations.filter(admin_team_approval=False).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
        elif dept_id == "it":
            self.queryset = resignations.filter(it_team_approval=False).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
        elif dept_id == "hr":
            self.queryset = resignations.filter(hr_team_approval=False).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
        else:
            self.queryset = []

        return self.list(request, *args, **kwargs)


class GetAllAppliedResignation(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = ViewResignationSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"applied_by_emp_id": "applied_by__emp_id", "applied_by_name": "applied_by__full_name",
                                "accepted_or_rejected_by_emp_id": "accepted_or_rejected_by__emp_id",
                                "accepted_or_rejected_by_name": "accepted_or_rejected_by__full_name",
                                "hr_accepted_or_rejected_by_emp_id": "hr_accepted_or_rejected_by__emp_id",
                                "applied_by_designation": "applied_by__designation__name",
                                "applied_by_process": "applied_by__team__base_team__name",
                                "hr_accepted_or_rejected_by_name": "hr_accepted_or_rejected_by__full_name"}

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        self.queryset = Resignation.objects.all().filter(
            **filter_by).filter(search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([HasUrlPermission, IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def approve_resignation(request, resign_id):
    try:
        usr = request.user
        resignation_obj = Resignation.objects.filter(id=resign_id).last()
        last_status = resignation_obj.resignation_status
        if not resignation_obj:
            raise ValueError("Resignation with this ID doesn't exist")
        if usr.designation.department.dept_id == "hr":
            if not resignation_obj.accepted_or_rejected_by:
                raise ValueError("Resignation has not been approved by Manager yet.")
            data = update_request(request.data, hr_accepted_or_rejected_by=usr.id,
                                  hr_accepted_or_rejected_comment=request.data.get("accepted_or_rejected_comment"))
            serializer = HRApproveResignationSerializer(data=data)
            if not serializer.is_valid():
                return return_error_response(serializer)
            new_status = serializer.validated_data["resignation_status"]
            if last_status in ['Withdrawn', "Approved", "Rejected"]:
                raise ValueError("Resignation status already set to {0}".format(last_status))
            resignation_obj.resignation_status = new_status
            resignation_obj.hr_accepted_or_rejected_by = usr
            resignation_obj.hr_accepted_or_rejected_comment = serializer.validated_data[
                "hr_accepted_or_rejected_comment"]
            resignation_obj.hr_accepted_or_rejected_at = datetime.now()
            if new_status == "Approved":
                resignation_obj.applied_by.last_working_day = resignation_obj.exit_date
                resignation_obj.applied_by.save()
            resignation_obj.save()
            add_resignation_history(resignation_obj, transaction="Change in Resignation Status by HR",
                                    message="Resignation '{0}' by '{1}' from HR Team".format(new_status,
                                                                                             get_formatted_name(
                                                                                                 request.user)))
            resignation = ViewResignationSerializer(resignation_obj).data
            return HttpResponse(json.dumps({"resignation": resignation}))
        teams = get_team_ids(usr)

        if not resignation_obj.applied_by.team.id in teams:
            raise ValueError("You are not authorized to Approve/Reject this Resignation.")
        data = update_request(request.data, accepted_or_rejected_by=usr.id)
        serializer = ApproveResignationSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        new_status = serializer.validated_data["resignation_status"]
        if last_status in ['Withdrawn', "Approved", "Rejected"]:
            raise ValueError("Resignation status already set to {0}".format(last_status))
        resignation_obj.resignation_status = "Rejected" if (new_status == "Rejected") else "Pending"
        resignation_obj.accepted_or_rejected_by = usr
        resignation_obj.accepted_or_rejected_comment = serializer.validated_data["accepted_or_rejected_comment"]
        resignation_obj.accepted_or_rejected_at = datetime.now()
        resignation_obj.save()
        add_resignation_history(resignation_obj, transaction="Change in Resignation Status by Manager",
                                message="Resignation '{0}' by '{1}' from {2}".format(new_status, get_formatted_name(
                                    request.user), request.user.designation.department))
        resignation = ViewResignationSerializer(resignation_obj).data
        return HttpResponse(json.dumps({"resignation": resignation}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def get_resignation_history(request):
    try:
        resignation_obj = Resignation.objects.filter(applied_by__emp_id=request.user.emp_id)
        if not resignation_obj:
            return HttpResponse(json.dumps({}))
        resignation_history = ResignationHistory.objects.filter(resignation__in=resignation_obj)
        resignation_history = ResignationHistorySerializer(resignation_history, many=True).data
        return HttpResponse(json.dumps({"resignation_history": resignation_history}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([HasUrlPermission, IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def update_notice_period(request, resign_id):
    try:
        yr, month, day = request.POST["exit_date"].split("-")
        deduct_lb=parse_boolean_value(request.data.get('deduct_leave_balance'))
        new_exit_date = date(int(yr), int(month), int(day))
        resignation_obj = Resignation.objects.filter(id=resign_id).last()
        if not resignation_obj:
            raise ValueError("Resignation with this ID doesn't exist")
        res_status = resignation_obj.resignation_status
        if res_status in ["Rejected", "Withdrawn", "Terminated"]:
            raise ValueError("Resignation has been {0}. Any change in Notice Period is not allowed.".format(res_status))
        # Todo Check who can update the Exit Date
        if not request.user.designation.department.dept_id == "hr":
            raise ValueError("You are not authorized to Extend/Reduce the Notice Period.")
        # if new_exit_date < datetime.today().date():
        #     raise ValueError("Exit Date can't be set to date in the Past.")
        last_exit_date = resignation_obj.exit_date
        if new_exit_date == last_exit_date:
            raise ValueError("Exit Date set to {0}. No more changes allowed.".format(last_exit_date))
        if new_exit_date < last_exit_date:
            try:
                leave_balance = LeaveBalance.objects.get(profile=resignation_obj.applied_by)
            except:
                raise ValueError("Leave Balance for this user not found.")
            if deduct_lb:
                if not (last_exit_date - new_exit_date).days <= leave_balance.paid_leaves:
                    raise ValueError("User doesn't have sufficient Leave Balance.")
                leave_balance.paid_leaves -= (last_exit_date - new_exit_date).days
                leave_balance.total -= (last_exit_date - new_exit_date).days
                leave_balance.save()
                LeaveBalanceHistory.objects.create(sl_balance=leave_balance.sick_leaves,
                                                   pl_balance=leave_balance.paid_leaves,
                                                   profile=resignation_obj.applied_by, date=datetime.now(),
                                                   leave_type="PL",
                                                   transaction=f"Update Notice period deducts {(last_exit_date - new_exit_date).days} PL ",
                                                   no_of_days=(last_exit_date - new_exit_date).days, total=leave_balance.total)
            resignation_obj.is_notice_period_reduced = True
        data = update_request(request.data, notice_period_extended_or_reduced_by=request.user.id)
        serializer = UpdateNoticePeriodSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        resignation_obj.exit_date = serializer.validated_data["exit_date"]
        resignation_obj.notice_period_extended_or_reduced_by = request.user
        resignation_obj.notice_period_extended_or_reduced_comments = serializer.validated_data[
            "notice_period_extended_or_reduced_comments"]
        resignation_obj.notice_period_in_days = (new_exit_date - resignation_obj.start_date).days + 1
        resignation_obj.save()
        add_resignation_history(resignation_obj, transaction="Change in Notice Period",
                                message="Exit Date for '{0}' changed from '{1}' to '{2}' by '{3}'. Hence, new Notice Period will be {4} days".format(
                                    get_formatted_name(resignation_obj.applied_by), last_exit_date, new_exit_date,
                                    get_formatted_name(request.user), resignation_obj.notice_period_in_days))
        resignation = ViewResignationSerializer(resignation_obj).data
        return HttpResponse(json.dumps({"resignation": resignation}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def withdraw_resignation(request):
    try:
        resignation_obj = Resignation.objects.filter(applied_by__emp_id=request.user.emp_id).last()
        if not resignation_obj:
            raise ValueError("Resignation for this employee doesn't exist")
        comment = request.data.get("comment")
        if not comment:
            raise ValueError("Comment is required.")
        if resignation_obj.resignation_status == "Withdrawn":
            raise ValueError("Resignation has already been Withdrawn.")
        lwd = resignation_obj.exit_date
        if lwd < datetime.today().date():
            raise ValueError("Resignation withdrawal Failed as Exit Date already passed.")
        resignation_obj.resignation_status = "Withdrawn"
        resignation_obj.withdrawal_comments = comment
        resignation_obj.applied_by.last_working_day = None
        resignation_obj.applied_by.save()
        resignation_obj.save()
        add_resignation_history(resignation_obj, transaction="Resignation Withdrawn",
                                message="Resignation withdrawn by '{0}' at {1}. \nComment: {2}".format(
                                    get_formatted_name(request.user), datetime.now(), comment))
        return HttpResponse(json.dumps({"message": "Resignation withdrawn successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def submit_exit_feedback(request):
    try:
        resignation_obj = Resignation.objects.filter(applied_by__emp_id=request.user.emp_id,
                                                     resignation_status="Approved").last()
        if not resignation_obj:
            raise ValueError("Resignation for this employee doesn't exist")
        existing = ExitFeedbackInterview.objects.filter(resignation=resignation_obj.id)
        if existing:
            raise ValueError("You have already submitted the Exit Feedback Form.")
        data = update_request(request.data, resignation=resignation_obj.id)
        serializer = SubmitExitFeedbackSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        feedback = serializer.create(serializer.validated_data)
        add_resignation_history(resignation_obj, transaction="Exit Feedback Submitted",
                                message="Exit feedback attempted by '{0}' at {1}.".format(
                                    get_formatted_name(request.user), datetime.now()))
        return HttpResponse(json.dumps({"message": "Feedback submitted successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def view_team_exit_feedback(request, resign_id):
    try:
        feedback = ExitFeedbackInterview.objects.filter(resignation=resign_id).last()
        if not feedback:
            raise ValueError("No Exit Feedback Data found.")
        feedback = ViewExitFeedbackSerializer(feedback).data
        return HttpResponse(json.dumps({"feedback": feedback}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_exit_checklist(request, resign_id):
    try:
        usr = request.user
        resignation_obj = get_resignation_by_id(resign_id)
        usr_mgr = resignation_obj.applied_by.team.manager
        if usr.designation.department.dept_id in ['it', 'hr', 'admin']:
            check_list = ExitChecklist.objects.filter(dept=usr.designation.department)
            check_list = ExitChecklistSerializer(check_list, many=True).data
            return HttpResponse(json.dumps({"checklist": check_list}))
        if not (usr == usr_mgr or usr == usr_mgr.team.manager or usr == usr_mgr.team.manager.team.manager):
            raise ValueError("You are not Authorized for this Action.")
        check_list = ExitChecklist.objects.filter(dept__isnull=True)
        check_list = ExitChecklistSerializer(check_list, many=True).data
        is_mgr = True if (
                usr == usr_mgr or usr == usr_mgr.team.manager or usr == usr_mgr.team.manager.team.manager) else False
        return HttpResponse(json.dumps({"checklist": check_list, "is_mgr": is_mgr}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def handle_final_approval_checklist(final_approval, resign_id, usr):
    for approve in final_approval:
        approve = update_request(approve, resignation=resign_id, approved_by=usr.id, checklist=approve["checklist"],
                                 due_status=approve["due_status"])
        serializer = FinalApprovalSerializer(data=approve)
        if not serializer.is_valid():
            return return_error_response(serializer)
        existing = FinalApprovalChecklist.objects.filter(checklist=approve["checklist"], resignation=resign_id)
        if existing:
            continue
        approval = serializer.create(serializer.validated_data)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def final_exit_approval(request, resign_id):
    try:
        usr = request.user
        data = request.data
        final_approval = data.get('final_approval')
        approval_comm = data.get("comment")
        if not approval_comm:
            raise ValueError("Comment is required.")
        resignation_obj = get_resignation_by_id(resign_id)
        if not resignation_obj.resignation_status in ["Approved", "Terminated"]:
            raise ValueError("Action allowed only for Approved Resignations.")
        usr_dept = usr.designation.department
        usr_mgr = resignation_obj.applied_by.team.manager
        if usr_dept.dept_id == "it":
            if resignation_obj.it_team_approval:
                raise ValueError("Resignation already approved by '{0}' Department".format(usr_dept.name))
            handle_final_approval_checklist(final_approval, resign_id, usr)
            resignation_obj.it_team_approval = True
            resignation_obj.it_team_comments = approval_comm
        elif usr_dept.dept_id == "admin":
            if resignation_obj.admin_team_approval:
                raise ValueError("Resignation already approved by '{0}' Department".format(usr_dept.name))
            handle_final_approval_checklist(final_approval, resign_id, usr)
            resignation_obj.admin_team_approval = True
            resignation_obj.admin_team_comments = approval_comm
        elif usr_dept.dept_id == "hr":
            if resignation_obj.hr_team_approval:
                raise ValueError("Resignation already approved by '{0}' Department".format(usr_dept.name))
            handle_final_approval_checklist(final_approval, resign_id, usr)
            resignation_obj.hr_team_approval = True
            resignation_obj.hr_team_comments = approval_comm
        else:
            if not (usr == usr_mgr or usr == usr_mgr.team.manager or usr == usr_mgr.team.manager.team.manager):
                raise ValueError("You are not Authorized for this Action.")
            else:
                if resignation_obj.dept_approval:
                    raise ValueError("Resignation already approved by Department")
                handle_final_approval_checklist(final_approval, resign_id, usr)
                kt = json.loads(data.get('knowledge_transfer'))
                resignation_obj.knowledge_transfer = kt
                resignation_obj.dept_approval = True
                resignation_obj.dept_approval_comments = approval_comm
        resignation_obj.save()
        add_resignation_history(resignation_obj,
                                transaction="Department Approval from {0} department.".format(usr_dept),
                                message="Resignation approved by '{0}' from '{1}' Department. \nComment: '{2}'".format(
                                    get_formatted_name(request.user), usr_dept, approval_comm))
        return HttpResponse(json.dumps({"message": "Approval done successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomTokenAuthentication])
def view_final_exit_approval(request, resign_id):
    try:
        checklist = ExitChecklist.objects.all()
        checklist = ViewApprovalSerializer(checklist, many=True, context={"resign_id": resign_id}).data
        return HttpResponse(json.dumps({"approval": checklist}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def terminate(request, emp_id):
    try:
        data = request.data
        comm = data.get("comment")
        if not comm:
            raise ValueError("Provide a Comment.")
        today = datetime.today().date()
        emp = Profile.objects.filter(emp_id=emp_id).last()
        if not emp:
            raise ValueError("Provide valid Emp ID")
        existing = Resignation.objects.filter(applied_by=emp, resignation_status="Terminated")
        if existing or emp.status == "Terminated":
            raise ValueError("Employee already Terminated")
        data = update_request(data, resignation_message=comm, start_date=today, applied_by=emp.id)
        serializer = CreateResignationSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["exit_date"] = today
        serializer.validated_data["resignation_status"] = "Terminated"
        resignation = serializer.create(serializer.validated_data)
        resignation.notice_period_in_days = 0
        resignation.hr_accepted_or_rejected_at = datetime.now()
        resignation.hr_accepted_or_rejected_by = request.user
        resignation.hr_accepted_or_rejected_comment = comm
        resignation.save()
        emp.status = "Terminated"
        emp.is_active = False
        emp.last_working_day = today
        emp.save()
        add_resignation_history(resignation, transaction="Employee Termination",
                                message="Employee Terminated by {0} at {1}".format(get_formatted_name(request.user),
                                                                                   today))
        resignation = ViewResignationSerializer(resignation).data
        return HttpResponse(json.dumps({"resignation": resignation, "message": "Employee terminated successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)

# class GetAllTeamWithdrawRequest(GenericAPIView, ListModelMixin):
#     authentication_classes = [CustomTokenAuthentication]
#     permission_classes = [IsAuthenticated, HasUrlPermission]
#     serializer_class = ViewWithdrawRequestSerializer
#     model = serializer_class.Meta.model
#
#     def get(self, request, *args, **kwargs):
#         mapping_column_names = {"applied_by_emp_id": "applied_by__emp_id", "applied_by_name": "applied_by__first_name",
#                                 "approved_by_emp_id": "approved_by__emp_id",
#                                 "approved_by_name": "approved_by__first_name"}
#
#         usr = request.user
#         order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
#                                                                              fields_look_up=mapping_column_names)
#         self.queryset = WithdrawRequest.objects.filter(resignation__applied_by__team__manager=usr).filter(
#             **filter_by).filter(search_query).order_by(*order_by_cols)
#         return self.list(request, *args, **kwargs)
#
#
# def approve_withdraw(request, withdraw_req_id):
#     try:
#         data = request.data
#         withdraw_request = WithdrawRequest.objects.filter(id=withdraw_req_id).last()
#         if not withdraw_request:
#             raise ValueError("Withdraw Request with this ID doesn't exist")
#         approved_comment = data.get("approved_comment")
#         if not approved_comment or status:
#             raise ValueError("Comment and Status are required.")
#         if not withdraw_request.status == "Pending":
#             raise ValueError("Request has already been Approved/Rejected")
#         data = update_request(data, approved_by=request.user)
#         serializer = ApproveWithdrawRequestSerializer(data=data)
#         if not serializer.is_valid():
#             return return_error_response(serializer)
#         if serializer.validated_data["status"] == "Approved":
#             withdraw_request.resignation.resignation_status = "Withdrawn"
#             withdraw_request.resignation.save()
#         withdraw_request.approved_by = request.user
#         withdraw_request.approved_comment = serializer.validated_data["approved_comment"]
#         withdraw_request.approved_at = datetime.now()
#         withdraw_request.status = serializer.validated_data["status"]
#         withdraw_request.save()
#         add_resignation_history(withdraw_request.resignation, transaction="Resignation Withdraw Requested",
#                                 message="Resignation withdraw request {0} by '{1}' at {2}. \nComment: {3}".format(
#                                     serializer.validated_data["status"], get_formatted_name(request.user),
#                                     datetime.now(), serializer.validated_data["approved_comment"]))
#         return HttpResponse(
#             json.dumps({"message": "Resignation withdraw request {0}".format(serializer.validated_data["status"])}))
#     except Exception as e:
#         return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
