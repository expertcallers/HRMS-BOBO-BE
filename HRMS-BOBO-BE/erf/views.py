import json
import traceback

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime, timedelta
import logging

from erf.models import ERF, ERFHistory
from hrms import settings
from interview.models import Candidate
from interview_test.models import Test
from mapping.models import Designation, Profile, MiscellaneousMiniFields, Department
from mapping.serializer import GetAllProfileSerializer
from mapping.views import HasUrlPermission
from erf.serializers import ERFSerializer, GetAllERFSerializer, GetERFSerializer, ErfApprovalSerializer, \
    OpenERFSerializer, GetErfHistorySerializer
from team.models import Process
from utils.util_classes import CustomTokenAuthentication
from utils.utils import update_request, return_error_response, get_sort_and_filter_by_cols, unhash_value, tz, \
    get_all_profile_serializer_map_columns

logger = logging.getLogger(__name__)


def get_erf_by_id(erf_id):
    erf = ERF.objects.filter(id=erf_id)
    if erf.count() == 0:
        raise ValueError("Record not found")
    return erf[0]


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_erf(request):
    try:
        desi = request.data.get('designation')
        if not desi:
            raise ValueError("Please provide designation")
        dept = request.data.get("department")
        designation = Designation.objects.filter(name=desi, department__id=dept)
        if designation.count() == 0:
            raise ValueError("Please provide valid designation")
        designation = designation[0]
        department = designation.department

        process = request.data.get('process')
        if not process:
            raise ValueError("Please provide process")
        process = Process.objects.filter(name=process, is_active=True).last()
        if process is None:
            raise ValueError("Please provide valid process information")
        round_names = request.data.get("round_names")
        persons = request.data.get("persons")
        data = update_request(request.data, round_names=round_names, interview_persons=persons,
                              department=department.id, designation=designation.id, process=process.id)
        erf_serializer = ERFSerializer(data=data)
        if not erf_serializer.is_valid():
            return_error_response(erf_serializer, raise_exception=True)
        int_tests = request.data.get("tests")
        int_tests = [str(i).strip() for i in int_tests.split(",") if
                     Test.objects.filter(id=str(i).strip()).last()] if int_tests and str(
            int_tests).strip() != "" else []
        int_persons = [str(i).strip() for i in persons.split(",")]
        int_persons_len = len(int_persons)
        int_persons = list(set([str(i).strip() for i in persons.split(",")]))
        round_names_list = [str(i).strip() for i in round_names.split(",")]
        profiles = Profile.objects.filter(emp_id__in=int_persons)
        if len(profiles) != len(int_persons):
            raise ValueError("please provide valid persons list ")
        if len(round_names_list) != int_persons_len:
            raise ValueError("please provide valid round-names")

        erf_serializer.validated_data["no_of_rounds"] = len(round_names_list)

        req_type = data.get('requisition_type')
        if req_type == "Replacement" and data.get('reason_for_replace') is None:
            raise ValueError("Reason for Replace is required if requisition type is Replacement")
        today = datetime.today()
        try:
            misc = MiscellaneousMiniFields.objects.get(field="erf_approval_limit")
            approval_limit = int(misc.content) if str(misc.content).isnumeric() else settings.ERF_APPROVAL_LIMIT
        except Exception as e:
            approval_limit = settings.ERF_APPROVAL_LIMIT
        if desi not in settings.DESI_DONOT_REQUIRES_VP_APPROVAL or int(data.get("salary_range_to")) >= approval_limit:
            erf_serializer.validated_data["approval_status"] = "Pending"
        else:
            erf_serializer.validated_data["approval_status"] = "Approved"
        deadline = erf_serializer.validated_data["deadline"]
        diff = deadline - today.date()
        if deadline < today.date() or int(diff.days) < 7:
            raise ValueError("Deadline should be greater than 7 days from today.")
        if today.weekday() == 4 and today.time().hour >= 19:
            requisition_day = today + timedelta(days=3)
            deadline = deadline + timedelta(days=3)
        elif today.weekday() == 5:
            requisition_day = today + timedelta(days=2)
            deadline = deadline + timedelta(days=2)
        elif today.weekday() == 6:
            requisition_day = today + timedelta(days=1)
            deadline = deadline + timedelta(days=1)
        else:
            requisition_day = today
        if int(data.get('pricing')) < 0 or int(data.get("salary_range_frm")) < 1 or int(
                data.get("salary_range_to")) < 1:
            raise ValueError("salary-range-from and salary-range-to should have minimum value 1")

        if int(data.get("salary_range_frm")) >= int(data.get("salary_range_to")):
            raise ValueError("Salary-range-from must be lesser than salary-range-to")

        erf_serializer.validated_data['deadline'] = deadline
        erf_serializer.validated_data['requisition_date'] = requisition_day
        erf_serializer.validated_data['created_by'] = request.user

        erf = erf_serializer.create(erf_serializer.validated_data)
        for test_id in int_tests:
            erf.test.add(test_id)
        profiles.update(interview=True)

        return Response({"message": "Erf Created successfully"})
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_erf_approval_status(request):
    try:
        approvals = request.data.get("approvals")
        user = request.user
        if user.designation.category.name != "VP":
            raise ValueError("Only VP can approve or reject ERF")
        if type(approvals) is not list:
            raise ValueError("Provide approvals in list format")
        for data in approvals:
            serializer = ErfApprovalSerializer(data=data)
            if not serializer.is_valid():
                return_error_response(serializer, raise_exception=True)
        erf_approvals = []
        for approval in approvals:
            erf = ERF.objects.filter(id=approval.get('id')).last()
            if not erf.is_erf_open:
                raise ValueError("The erf is not open")
            if not erf:
                raise ValueError("Erf with id {0} does not exist".format(approval.get('id')))
            if erf.approval_status != "Pending":
                raise ValueError("erf {0} has already {1}".format(erf.id, erf.approval_status))
            approval_status = approval.get('approval_status')
            is_erf_open = False if approval_status == "Rejected" else True
            erf.approval_status = approval_status
            erf.is_erf_open = is_erf_open
            erf.approved_or_rejected_by = user
            erf_approvals.append(erf)
        if len(erf_approvals) > 0:
            ERF.objects.bulk_update(erf_approvals, ["approval_status", "is_erf_open", "approved_or_rejected_by"])

        return HttpResponse(json.dumps({"message": "ERFs Updated Successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllErf(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllERFSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            fields_to_look_up = {"created_by_emp_id": "created_by__emp_id", "closed_by_emp_id": "closed_by__emp_id",
                                 "created_by_name": "created_by__full_name", "closed_by_name": "closed_by__full_name",
                                 "process": "process__name", "designation": "designation__name",
                                 "department": "department__name"}

            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(
                request.GET, fields_look_up=fields_to_look_up)
            self.queryset = ERF.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        except Exception as e:
            logger.info("Exception at GetAllErf {0} {1}".format(str(e), traceback.format_exc(0)))
            self.queryset = []
        return self.list(request, *args, **kwargs)


class GetErfProfiles(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllProfileSerializer
    model = serializer_class.Meta.model

    def get(self, request, erf_id, *args, **kwargs):
        try:
            erf = ERF.objects.filter(id=erf_id)
            if erf.count() == 0:
                self.queryset = []
                return self.list(request, *args, **kwargs)

            profiles = list(erf[0].profiles.values_list('id', flat=True))
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=get_all_profile_serializer_map_columns)

            self.queryset = Profile.objects.filter(id__in=profiles).select_related('team__manager').prefetch_related(
            'onboard__candidate__current_application').filter(**filter_by).filter(search_query).order_by(
                *order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("Exception at GetErfProfiles {0} {1}".format(str(e), traceback.format_exc(0)))

        return self.list(request, *args, **kwargs)


class GetMyErf(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllERFSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            usr = request.user
            fields_to_look_up = {"created_by_emp_id": "created_by__emp_id", "closed_by_emp_id": "closed_by__emp_id",
                                 "created_by_name": "created_by__full_name", "closed_by_name": "closed_by__full_name",
                                 "process": "process__name", "designation": "designation__name",
                                 "department": "department__name"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(
                request.GET, fields_look_up=fields_to_look_up)
            self.queryset = ERF.objects.filter(created_by_id=request.user.id).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)

        except Exception as e:
            self.queryset = []
            logger.info("Exception at GetMyErf {0} {1}".format(str(e), traceback.format_exc(0)))

        return self.list(request, *args, **kwargs)


class GetErfHistory(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetErfHistorySerializer
    model = serializer_class.Meta.model

    def get(self, request, erf_id, *args, **kwargs):
        fields_to_look_up = {"added_or_removed_by_emp_id": "added_or_removed_by__emp_id",
                             "added_or_removed_by_name": "added_or_removed_by__full_name", "emp_id": "profile__emp_id",
                             "emp_name": "profile__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=fields_to_look_up)
        self.queryset = ERFHistory.objects.filter(erf_id=erf_id).filter(**filter_by).filter(
            search_query).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_my_erf_stats(request):
    erfs = ERF.objects.filter(created_by_id=request.user.id)
    open_erf = erfs.filter(is_erf_open=True, approval_status="Approved").count()
    rejected = erfs.filter(approval_status="Rejected").count()
    pending_approval = erfs.filter(approval_status="Pending").count()
    return HttpResponse(
        json.dumps({"open_erf": open_erf, "rejected": rejected, "pending_approval": pending_approval}))


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_all_erf_stats(request):
    erfs = ERF.objects.all()
    open_erf = erfs.filter(is_erf_open=True, approval_status="Approved").count()
    rejected = erfs.filter(approval_status="Rejected").count()
    pending_approval = erfs.filter(approval_status="Pending").count()
    return HttpResponse(
        json.dumps({"open_erf": open_erf, "rejected": rejected, "pending_approval": pending_approval}))


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_erf(request, erf_id):
    try:
        erf = get_erf_by_id(erf_id)
        erf_data = GetERFSerializer(erf).data
        return HttpResponse(json.dumps({"erf": erf_data}))

    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_open_erf(request):
    dept = request.GET.get("dept")
    if dept and str(dept).isnumeric():
        open_positions = ERF.objects.filter(approval_status="Approved", designation__department__id=dept).filter(
            Q(is_erf_open=True) | Q(always_open=True))
    else:
        open_positions = ERF.objects.filter(approval_status="Approved").filter(
            Q(is_erf_open=True) | Q(always_open=True))
    open_erf = OpenERFSerializer(open_positions, many=True).data
    return HttpResponse(json.dumps({"open_erf": open_erf}))


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def close_erf_by_mgr(request, erf_id):
    try:
        usr = request.user
        comment = request.data.get("comment")
        if comment is None or str(comment).strip() == "":
            raise ValueError("comment is required")
        erf = get_erf_by_id(erf_id)
        if erf.created_by != usr:
            raise ValueError("this erf is not created by you")
        erf.is_erf_open = False
        erf.closed_by = usr
        erf.closure_date = datetime.today().date()
        erf.close_reason = comment
        erf.save()
        return HttpResponse(json.dumps({"message": "erf is closed successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def unlink_erf(request, erf_id, emp_id):
    try:
        usr = request.user
        erf = get_erf_by_id(erf_id)
        comment = request.data.get("comment")
        if comment is None:
            raise ValueError("Please send me a comment")
        try:
            emp = Profile.objects.get(emp_id=emp_id)
        except:
            raise ValueError("employee with emp_id {0} does not exist".format(emp_id))
        if not erf.profiles.contains(emp):
            raise ValueError("emp_id {0} is not linked with erf_id {1}".format(emp_id, erf_id))
        if erf.created_by != usr:
            raise ValueError("You cannot unlink, this erf doesn't belong to you")
        erf.profiles.remove(emp)

        if not erf.is_erf_open:
            erf.is_erf_open = True
            erf.closure_date = None
            erf.closed_by = None
            erf.erf_reopen = True
            erf.erf_reopen_date = tz.localize(datetime.now())
            erf.save()
        _ = ERFHistory.objects.create(comment=comment, erf=erf, profile=emp, status="Unlinked",
                                      added_or_removed_by=request.user)
        return HttpResponse(json.dumps({"message": "employee unlinked from erf successfully"}))

    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
