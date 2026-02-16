import json
import logging

from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated

from hrms import settings
from mapping.views import HasUrlPermission
from powerbi.models import SOP, SOPSourceData
from powerbi.serializers import CreateSOPSerializer, GetSOPSerializer, GetAllSOPSerializer, \
    CreateSOPSourceDataSerializer
from team.models import Process
from utils.utils import update_request, return_error_response, get_sort_and_filter_by_cols, send_custom_email, \
    get_formatted_name, format_obj_data, format_dict_data, get_erf_email_message, send_email_message

logger = logging.getLogger(__name__)


# Create your views here.

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_sop(request):
    try:
        process = request.data.get('campaign')
        if not process:
            raise ValueError("Please provide campaign")
        process = Process.objects.filter(name=process, is_active=True).last()
        if process is None:
            raise ValueError("Please provide valid process information")
        data = update_request(request.data, campaign=process.id, created_by=request.user.id)
        serializer = CreateSOPSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        sop_source_data = request.data.get("sop_source_data")
        # logger.info("data = {0}".format(sop_source_data))
        if sop_source_data is None or not isinstance(sop_source_data, list) or len(
                sop_source_data) == 0 or not isinstance(sop_source_data[0], dict):
            raise ValueError("List of SOP Source data object is required")
        for sop_s_data in sop_source_data:
            sop_serializer = CreateSOPSourceDataSerializer(data=sop_s_data)
            if not sop_serializer.is_valid():
                return return_error_response(sop_serializer)

        sop = serializer.create(serializer.validated_data)
        for sop_s_data in sop_source_data:
            _ = SOPSourceData.objects.create(**sop_s_data, sop=sop)

        data_source = SOPSourceData.objects.filter(sop=sop)
        data = {'campaign': sop.campaign.name, "type": sop.campaign_type, "process1": sop.process_type_one,
                "process2": sop.process_type_two, "process3": sop.process_type_three, "agents": None, "leaders": None,
                'created_by': sop.created_by.full_name,
                "campaign_type_other": sop.campaign_type_other if sop.campaign_type_other and str(
                    sop.campaign_type_other).strip() != "" else None,
                'created_id': sop.created_by.emp_id, 'status': sop.status, "date": sop.created_at, 'data': data_source,
                'report_format': sop.report_format, 'other': sop.other_info
                }
        subject = "New SOP Report Request"
        html_path = 'add_sop_old.html'
        try:
            email_template = get_template(html_path).render(data)
            email_msg = get_erf_email_message(subject, email_template, to=["cc@expertcallers.com"], reply_to=[])
            send_email_message(email_msg)
        except Exception as e:
            logger.info("exception failed to send email {0}".format(str(e)))

        return HttpResponse(json.dumps({"message": "SOP Created successfully"}))
    except Exception as e:
        logger.info("exception at create_sop {0}".format(str(e)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_sop(request, sop_id):
    try:
        sop = SOP.objects.filter(id=sop_id).last()
        if sop is None:
            raise ValueError("Invalid SOP-ID")
        sop_data = GetSOPSerializer(sop).data
        # logger.info("data={0}".format(sop_data))
        return HttpResponse(json.dumps(sop_data))
    except Exception as e:
        logger.info("exception at get_sop {0}".format(str(e)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_sop_status(request, sop_id):
    try:
        sop = SOP.objects.filter(id=sop_id).last()
        if sop is None:
            raise ValueError("Invalid SOP-ID")

        sop_status = request.data.get("status")
        sop_status_list = [i[0] for i in settings.SOP_STATUS]
        if sop_status not in sop_status_list:
            raise ValueError("Invalid sop status")
        sop.status = sop_status
        sop.save()
        return HttpResponse(json.dumps({"message": "SOP status updated successfully"}))
    except Exception as e:
        logger.info("exception at update_sop_status {0}".format(str(e)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllSOP(ListModelMixin, GenericAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllSOPSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                       "campaign": "campaign__name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        profile = request.user
        if profile.designation.department.dept_id == "cc":
            self.queryset = SOP.objects.filter(search_query).filter(**filter_by).order_by(*order_by_cols)
        else:
            self.queryset = SOP.objects.filter(created_by=request.user).filter(search_query).filter(
                **filter_by).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)
