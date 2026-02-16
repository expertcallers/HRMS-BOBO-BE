import json
import logging
import traceback
from datetime import datetime

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated

from it.models import ChangeMgmt
from it.serializers import CreateChangeMgmtSerializer, GetAllChangeMgmtSerializer, UpdateChangeMgmtSerializer
from mapping.models import MiscellaneousMiniFields, Profile
from mapping.views import HasUrlPermission
from utils.util_classes import CustomTokenAuthentication
from utils.utils import return_error_response, get_sort_and_filter_by_cols, update_request, get_emp_by_emp_id, \
    get_team_ids, tz

logger = logging.getLogger(__name__)


# Create your views here.
@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_change_mgmt(request):
    try:
        usr = request.user
        chng_mgmt_doc_no = MiscellaneousMiniFields.objects.filter(field="change_mgmt_number").last()
        if chng_mgmt_doc_no is None:
            raise ValueError("Inform cc team to update change_mgmt_number in misc")
        data = request.data
        implemented_by = get_emp_by_emp_id(data.get("implemented_by"))
        initiated_by = get_emp_by_emp_id(data.get("initiated_by"))
        data = update_request(data, document_number=chng_mgmt_doc_no.content, implemented_by=implemented_by.id,
                              initiated_by=initiated_by.id, created_by=usr.id)
        serializer = CreateChangeMgmtSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.create(serializer.validated_data)
        chng_mgmt_doc_no.content = int(chng_mgmt_doc_no.content) + 1
        chng_mgmt_doc_no.save()
        return HttpResponse(json.dumps({"message": "change management created successfully"}))
    except Exception as e:
        logger.info("exception at create_change_mgmt {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def edit_change_mgmt(request, cm_id):
    try:
        usr = request.user
        data = request.data
        change_mgmt = get_change_mgmt_instance(cm_id)
        if change_mgmt.change_status != "Rejected":
            raise ValueError("Only Rejected one can be edited")
        if change_mgmt.new_edit_exists:
            raise ValueError(
                "You cannot edit this one, there is already an edited change management is in review process")

        implemented_by = get_emp_by_emp_id(data.get("implemented_by")) if data.get(
            "implemented_by") else change_mgmt.implemented_by
        initiated_by = get_emp_by_emp_id(data.get("initiated_by")) if data.get(
            "initiated_by") else change_mgmt.initiated_by
        data = update_request(data, implemented_by=implemented_by.id, document_number=change_mgmt.document_number,
                              sub_doc_number=change_mgmt.sub_doc_number + 1,
                              initiated_by=initiated_by.id, created_by=usr.id)
        serializer = UpdateChangeMgmtSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.create(serializer.validated_data)
        change_mgmt.new_edit_exists = True
        change_mgmt.save()

        return HttpResponse(json.dumps({"message": "change management updated successfully"}))
    except Exception as e:
        logger.info("exception at create_change_mgmt {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_change_mgmt_instance(cm_id):
    change_mgmt = ChangeMgmt.objects.filter(id=cm_id).last()
    if change_mgmt is None:
        raise ValueError("Invalid change management id")
    return change_mgmt


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def approve_change_mgmt(request, cm_id):
    try:
        usr = request.user
        change_mgmt = get_change_mgmt_instance(cm_id)
        if change_mgmt.change_approved_by:
            raise ValueError(
                f"It is already approved by {change_mgmt.change_approved_by.full_name}( {change_mgmt.change_approved_by.emp_id} )")

        change_status = request.data.get("change_status")
        if change_status == "Rejected":
            change_mgmt.change_status = "Rejected"
            change_mgmt.rejected_by = usr
            change_mgmt.rejected_date = tz.localize(datetime.now())

        change_mgmt.change_approved_by = usr
        change_mgmt.change_approved_date = tz.localize(datetime.now())
        change_mgmt.save()
        return HttpResponse(json.dumps({"message": "change management approval is done successfully"}))
    except Exception as e:
        logger.info("exception at create_change_mgmt {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_next_document_reference_number(request):
    try:
        chng_mgmt_doc_no = MiscellaneousMiniFields.objects.filter(field="change_mgmt_number").last()
        if chng_mgmt_doc_no is None:
            raise ValueError("there is no chng_mgmt_doc_no in miscellaneous mini fields inform cc-team")
        return HttpResponse(json.dumps({"document_number": chng_mgmt_doc_no.content}))
    except Exception as e:
        logger.info("exception at create_change_mgmt {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def review_change_mgmt(request, cm_id):
    try:
        usr = request.user
        change_mgmt = get_change_mgmt_instance(cm_id)
        if change_mgmt.reviewed_by:
            raise ValueError(
                f"It is already reviewed_by by {change_mgmt.reviewed_by.full_name}( {change_mgmt.reviewed_by.emp_id} )")
        change_status = request.data.get("change_status")
        if change_status == "Rejected":
            change_mgmt.change_status = "Rejected"
            change_mgmt.rejected_by = usr
            change_mgmt.rejected_date = tz.localize(datetime.now())
        else:
            change_mgmt.change_status = "Accepted"
        change_mgmt.reviewed_by = usr
        change_mgmt.reviewed_date = tz.localize(datetime.now())
        change_mgmt.save()
        return HttpResponse(json.dumps({"message": "change management review is done successfully"}))
    except Exception as e:
        logger.info("exception at create_change_mgmt {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


change_mgmt_col_map = {"initiated_by_emp_id": "initiated_by__emp_id",
                       "initiated_by_name": "initiated_by__full_name",
                       "implemented_by_emp_id": "implemented_by__emp_id",
                       "implemented_by_name": "implemented_by__full_name",
                       "change_approved_by_emp_id": "change_approved_by__emp_id",
                       "change_approved_by_name": "change_approved_by__full_name",
                       "created_by_emp_id": "created_by__emp_id",
                       "created_by_name": "created_by__full_name",
                       "reviewed_by_emp_id": "reviewed_by__emp_id",
                       "reviewed_by_name": "reviewed_by__full_name",
                       "rejected_by_emp_id": "rejected_by__emp_id",
                       "rejected_by_name": "rejected_by__full_name"
                       }


class GetAllChangeMgmt(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllChangeMgmtSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            emp = request.user

            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=change_mgmt_col_map)
            team = get_team_ids(emp)
            if team is None:
                team = [emp.team.id]
            else:
                team = team + [emp.team.id]

            self.queryset = ChangeMgmt.objects.filter(created_by__team__id__in=team).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info("exception at GetAllChangeMgmt {0}".format(traceback.format_exc(5)))
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllApprovalsChangeMgmt(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllChangeMgmtSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            emp = request.user
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=change_mgmt_col_map)
            if emp.designation.name == "System Architect":
                self.queryset = ChangeMgmt.objects.filter(change_status="Pending",
                                                          change_approved_by__isnull=True).filter(**filter_by).filter(
                    search_query).order_by(*order_by_cols)
            else:
                self.queryset = ChangeMgmt.objects.filter(change_status="Pending",
                                                          change_approved_by__isnull=True).filter(
                    Q(created_by__team__manager=emp) | Q(
                        created_by__team__manager__team__manager=emp) | Q(
                        created_by__team__manager__team__manager__team__manager=emp)).filter(
                    **filter_by).filter(search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info("exception at GetAllChangeMgmt {0}".format(traceback.format_exc(5)))
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllReviewsChangeMgmt(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllChangeMgmtSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            emp = request.user

            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=change_mgmt_col_map)
            if emp.designation.name == "System Architect":
                self.queryset = ChangeMgmt.objects.filter(change_status="Pending", reviewed_by__isnull=True,
                                                          change_approved_by__isnull=False).filter(**filter_by).filter(
                    search_query).order_by(*order_by_cols)
            else:
                self.queryset = ChangeMgmt.objects.filter(change_status="Pending", reviewed_by__isnull=True,
                                                          change_approved_by__isnull=False).filter(
                    Q(created_by__team__manager__team__manager=emp) | Q(
                        created_by__team__manager__team__manager__team__manager=emp)).filter(**filter_by).filter(
                    search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info("exception at GetAllChangeMgmt {0}".format(traceback.format_exc(5)))
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetMyChangeMgmt(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllChangeMgmtSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=change_mgmt_col_map)

            self.queryset = ChangeMgmt.objects.filter(created_by=request.user).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info("exception at GetMyChangeMgmt {0}".format(traceback.format_exc(5)))
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
