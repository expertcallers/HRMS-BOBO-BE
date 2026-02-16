import datetime
import json
import logging
import traceback

from django.http import HttpResponse
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import status, authentication, mixins
from django.db.models import Q
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from mapping.views import HasUrlPermission
from utils.util_classes import CustomTokenAuthentication
from .serializers import *
from utils.utils import return_error_response, update_request, get_sort_and_filter_by_cols
from mapping.models import Designation

logger = logging.getLogger(__name__)


def get_ijp_info_by_id(ijp_id):
    if not str(ijp_id).isnumeric() or ijp_id is None:
        raise ValueError('{0} is invalid, Please provide a Valid ID'.format(ijp_id))
    try:
        ijp = IJP.objects.get(id=ijp_id)
    except Exception as e:
        raise ValueError('IJP record not found')
    return ijp


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_new_ijp(request):
    try:
        desi = request.data.get("designation")
        dept = request.data.get("department")
        selection_criteria=request.data.getlist("selection_criteria")

        selection_process=request.data.getlist("selection_process")
        designation = Designation.objects.filter(name=desi, department__id=dept).last()
        if not designation:
            raise ValueError("Provide a Valid Designation")
        process_name = request.data.get("process")
        if not process_name or str(process_name).strip() == "":
            raise ValueError("process name is required")
        process = Process.objects.filter(name=process_name, is_active=True).last()
        if not process:
            raise ValueError("Provide a Valid Process")
        department = designation.department
        last_date_to_apply = request.data.get("last_date_to_apply")
        if not last_date_to_apply:
            raise ValueError("Kindly provide a valid Last Date.")
        yr, month, day = last_date_to_apply.split("-")
        last_date_to_apply = datetime.date(int(yr), int(month), int(day))
        if last_date_to_apply < datetime.date.today():
            raise ValueError("The Last date to Apply can't be a date in the Past.")
        round_names = request.data.get('round_names')
        # round_location = request.data.get('round_location')
        # round_dates = request.data.get('round_dates')
        # round_location_list = [str(i).strip() for i in round_location.split(",")]
        # round_dates_list = [str(i).strip() for i in round_dates.split(",")]
        no_of_rounds = len([str(i).strip() for i in round_names.split(",")])
        # if len(round_location_list) != no_of_rounds or len(round_dates_list) != no_of_rounds:
        #     raise ValueError("Provide valid Round Dates & Location.")
        data = update_request(request.data, department=department.id, designation=designation.id,
                              process=process.id, no_of_rounds=no_of_rounds)
        ijp_serializer = CreateIJPSerializer(data=data)
        if not ijp_serializer.is_valid():
            return return_error_response(ijp_serializer)
        # ijp_serializer.validated_data["approval_status"] = "Pending"
        ijp_serializer.validated_data["created_by"] = request.user
        ijp_serializer.validated_data["selection_criteria"]=json.dumps(selection_criteria)
        ijp_serializer.validated_data["selection_process"]=json.dumps(selection_process)
        ijp = ijp_serializer.create(ijp_serializer.validated_data)
        ijp.save()
        ijp = ViewIJPSerializer(ijp).data
        return HttpResponse(json.dumps({"ijp": ijp}))
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}),
                            status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_ijp_info(request, id):
    try:
        ijp = get_ijp_info_by_id(id)
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
    ijp = ViewIJPSerializer(ijp).data
    return HttpResponse(json.dumps({'ijp': ijp}))


class GetAllIJP(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ViewIJPSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            fields_to_look_up = {
                "process": "process__name", "designation": "designation__name",
                "department": "department__name", "closed_by_emp_id": "closed_by__emp_id",
                "closed_by_name": "closed_by__full_name",
                "ijp_applied": "ijp_applied__designation__name", "created_by": "created_by__full_name"}

            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=fields_to_look_up)

            self.queryset = IJP.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("Exception at GetErfProfiles {0} {1}".format(str(e), traceback.format_exc(5)))

        return self.list(request, *args, **kwargs)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def close_ijp(request, ijp_id):
    try:
        close_ijp = get_ijp_info_by_id(ijp_id)
        if not close_ijp.is_ijp_open:
            raise ValueError("IJP not Active.")
        close_ijp.is_ijp_open = False
        close_ijp.closed_by = request.user
        close_ijp.save()
        return HttpResponse(json.dumps({'message': "Status changed Successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


# @api_view(['POST'])
# def update_ijp_approval_status(request):
#     try:
#         data = request.data
#         serializer = ApprovalStatusSerializer(data=data)
#         if not serializer.is_valid():
#             return return_error_response(serializer)
#         ijp = get_ijp_info_by_id(data.get("ijp_id"))
#         if ijp.approval_status != "Pending":
#             raise ValueError("IJP has already been {0}".format(ijp.approval_status))
#         approval_status = data.get("approval_status")
#         if approval_status == "Rejected":
#             ijp.is_ijp_open = False
#             ijp.closed_by = request.user
#         ijp.approval_status = approval_status
#         ijp.approved_or_rejected_by = request.user
#         ijp.save()
#         return HttpResponse(json.dumps({"message": "Status changed Successfully."}))
#     except Exception as e:
#         return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def apply_to_ijp(request, ijp_id):
    try:
        usr = request.user
        ijp_applied = get_ijp_info_by_id(ijp_id)
        get_application_if_any = IJPCandidate.objects.filter(ijp_applied=ijp_applied, profile=usr.id)
        if get_application_if_any:
            raise ValueError("You have already applied to this IJP.")
        if ijp_applied.last_date_to_apply < datetime.date.today():
            raise ValueError("Application Deadline Passed")
        if not ijp_applied.is_ijp_open:
            raise ValueError("IJP not Active")
        # if ijp_applied.approval_status == "Rejected" or ijp_applied.approval_status == "Pending":
        #     raise ValueError("IJP wasn't Approved")
        data = update_request(request.data, profile=usr.id, ijp_applied=ijp_applied.id)
        serializer = ApplyIJPSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        apply = serializer.create(serializer.validated_data)
        apply.current_process = usr.team.base_team
        apply.save()
        apply = ViewIJPCandidateSerializer(apply).data
        return HttpResponse(json.dumps({'applied': apply, "message": "Applied for IJP Successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetIJPApplications(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ViewAllApplicationSerializer
    model = serializer_class.Meta.model

    def get(self, request, ijp_id, *args, **kwargs):
        try:
            fields_to_look_up = {
                "process": "process__name", "designation": "profile__designation__name",
                "department": "profile__designation__department__name", "emp_id": "profile__emp_id",
                "ijp_applied": "ijp_applied__designation__name", "emp_name": "profile__full_name",
                "current_process": "current_process__name"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=fields_to_look_up)

            self.queryset = IJPCandidate.objects.filter(ijp_applied=ijp_id).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("Exception at GetErfProfiles {0} {1}".format(str(e), traceback.format_exc(5)))

        return self.list(request, *args, **kwargs)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_no_of_open_ijp(request):
    try:
        applied_ijp_id = []
        all_ijp = IJP.objects.filter(is_ijp_open=True, last_date_to_apply__gte=datetime.date.today())
        for ijp in all_ijp:
            applied = IJPCandidate.objects.filter(profile=request.user.id, ijp_applied=ijp.id)
            if applied:
                applied_ijp_id.append(ijp.id)
        open_ijp_count = IJP.objects.filter(is_ijp_open=True, last_date_to_apply__gte=datetime.date.today()).exclude(
            id__in=applied_ijp_id).count()
        return HttpResponse(json.dumps({'count': open_ijp_count}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllUnappliedIJP(mixins.ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ViewIJPSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            fields_to_look_up = {
                "process": "process__name", "designation": "designation__name",
                "department": "department__name", "closed_by_emp_id": "closed_by__emp_id",
                "closed_by_name": "closed_by__full_name", "ijp_applied": "ijp_applied__designation__name",
                "created_by": "created_by__full_name"}

            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=fields_to_look_up)
            applied_ijp_id = list(IJPCandidate.objects.filter(profile=request.user.id, ijp_applied__is_ijp_open=True,
                                                              ijp_applied__last_date_to_apply__gte=datetime.date.today()).values_list(
                "ijp_applied__id", flat=True))
            self.queryset = IJP.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols).exclude(
                id__in=applied_ijp_id)
        except Exception as e:
            self.queryset = []
            logger.info("Exception at GetAllUnappliedIJP {0} {1}".format(str(e), traceback.format_exc(5)))

        return self.list(request, *args, **kwargs)


class GetOpenIJP(mixins.ListModelMixin, GenericAPIView):
    serializer_class = OpenIJPSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            fields_to_look_up = {
                "process": "process__name", "designation": "designation__name",
                "department": "department__name", "closed_by_emp_id": "closed_by__emp_id",
                "closed_by_name": "closed_by__full_name", "ijp_applied": "ijp_applied__designation__name",
                "created_by": "created_by__full_name"}

            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=fields_to_look_up)
            self.queryset = IJP.objects.filter(is_ijp_open=True,
                                               last_date_to_apply__gte=datetime.datetime.today().date()).filter(
                **filter_by).filter(search_query).order_by(*order_by_cols)
        except Exception as e:
            self.queryset = []
            logger.info("Exception at GetOpenIJP {0} {1}".format(str(e), traceback.format_exc(5)))

        return self.list(request, *args, **kwargs)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def change_ijp_candidate_status(request, cand_id):
    try:
        candidate = IJPCandidate.objects.filter(id=cand_id).last()
        if not candidate:
            raise ValueError("IJP Candidate with this ID doesn't exist.")
        serializer = ChangeCandidateStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.update(candidate, serializer.validated_data)
        return HttpResponse(json.dumps({"message": "Candidate Status updated successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
