import csv
import logging
from _datetime import datetime, timedelta
import json

from django.http import HttpResponse
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated

from headcount.models import HeadcountProcess, UpdateProcessRequest, Headcount, UpdateHeadcountRequest, \
    HeadcountReference
from headcount.serializers import CreateHeadcountProcessSerializer, HeadcountProcessSerializer, HeadcountSerializer, \
    CreateUpdateProcessRequestSerializer, UpdateProcessRequestSerializer, ApproveUpdateProcessRequestSerializer, \
    SubCampaignSerializer, UpdateHeadcountSerializer, GetUpdateHeadcountSerializer, ApproveUpdateHeadcountSerializer, \
    HeadcountReferenceSerializer, GetHeadcountRefSerializer, HeadcountReferenceIndivSerializer, \
    CreateHeadcountSubCampaignSerializer
from hrms import settings
from mapping.models import Profile
from mapping.views import HasUrlPermission
from utils.util_classes import CustomTokenAuthentication
from utils.utils import update_request, return_error_response, get_sort_and_filter_by_cols, get_formatted_date, \
    get_dates_range

logger = logging.getLogger(__name__)


def get_hc_process_by_id(proc_id):
    try:
        if not proc_id:
            raise ValueError("Please provide valid Process ID")
        process = HeadcountProcess.objects.filter(id=proc_id).last()
        return process
    except Exception as e:
        raise ValueError("Process with this ID not found")


def get_hc_by_id(hc_id):
    try:
        if not hc_id:
            raise ValueError("Please provide valid Headcount ID")
        headcount = Headcount.objects.filter(id=hc_id).last()
        return headcount
    except Exception as e:
        raise ValueError("Headcount with this ID not found")


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_process(request):
    try:
        data = update_request(request.data, created_by=request.user.id)
        sub_campaign = data.get("subcampaigns")
        existing = HeadcountProcess.objects.filter(name=data.get("name"))
        if existing:
            raise ValueError("Process with this name exists.")
        rm = data.get("rm")
        if not rm:
            raise ValueError("Please provide RM for this Process")
        rmgr = Profile.objects.filter(emp_id=rm).last()
        if not rmgr:
            raise ValueError("Please provide valid RM ID")
        data = update_request(data, rm=rmgr.id)
        serializer = CreateHeadcountProcessSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["approved_headcount"] = round(serializer.validated_data["approved_headcount"], 2)
        process = serializer.create(serializer.validated_data)
        if not sub_campaign or sub_campaign == []:
            sub = {"name": process.name, "created_by": process.created_by.id}
            serializer = CreateHeadcountSubCampaignSerializer(data=sub)
            if not serializer.is_valid():
                return return_error_response(serializer)
            sub_camp = serializer.create(serializer.validated_data)
            process.sub_campaign.add(sub_camp)
        else:
            for sub in sub_campaign:
                sub = update_request(sub, created_by=process.created_by.id)
                serializer = CreateHeadcountSubCampaignSerializer(data=sub)
                if not serializer.is_valid():
                    return return_error_response(serializer)
                sub_camp = serializer.create(serializer.validated_data)
                process.sub_campaign.add(sub_camp)
        return HttpResponse(json.dumps({"message": "Process created successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllProcess(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = HeadcountProcessSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        usr = request.user
        mapping_column_names = {"created_by_name": "created_by__full_name", 'created_by_emp_id': "created_by__emp_id",
                                "rm_name": "rm__full_name", "rm_emp_id": "rm__emp_id"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        if usr.designation.name == "Associate Director":
            self.queryset = HeadcountProcess.objects.all().filter(**filter_by).filter(search_query).order_by(
                *order_by_cols)
        else:
            self.queryset = HeadcountProcess.objects.filter(rm=usr).filter(**filter_by).filter(search_query).order_by(
                *order_by_cols)
        return self.list(request, *args, **kwargs)


class GetAllProcessRequest(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = UpdateProcessRequestSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"name": "process__name", "created_by_name": "created_by__full_name",
                                'created_by_emp_id': "created_by__emp_id", "rm_name": "process__rm__full_name",
                                "rm_emp_id": "process__rm__emp_id",
                                "approved_rejected_by_emp_id": "approved_rejected_by__emp_id",
                                "approved_rejected_by_name": "approved_rejected_by__full_name",
                                "approved_headcount": "process__approved_headcount",
                                "pricing": "process__pricing", "currency": "process__currency",
                                "pricing_type": "process__pricing_type",
                                "pricing_type_value": "process__pricing_type_value"
                                }

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        self.queryset = UpdateProcessRequest.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def request_for_update_process(request, proc_id):
    try:
        process = get_hc_process_by_id(proc_id)
        existing_req = UpdateProcessRequest.objects.filter(process=process, status="Pending").last()
        if existing_req:
            raise ValueError("There is a pending update-process-request exists for this process")
        data = update_request(request.data, process=process.id, created_by=request.user.id)
        serializer = CreateUpdateProcessRequestSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["status"] = "Pending"
        request = serializer.create(serializer.validated_data)
        return HttpResponse(json.dumps({"message": "Request created successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def approve_process(request, req_id):
    try:
        usr = request.user
        req = UpdateProcessRequest.objects.filter(id=req_id).last()
        if not req:
            raise ValueError("Please provide valid Approval ID")
        process = get_hc_process_by_id(req.process.id)
        if not req.status == "Pending":
            raise ValueError("This request has already been {0}.".format(req.status))
        data = update_request(request.data, approved_rejected_by=usr.id)
        if not usr.designation.name == "Associate Director":
            raise ValueError("You are not authorized to Approve/Reject the request.")
        serializer = ApproveUpdateProcessRequestSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        req.status = serializer.validated_data["status"]
        req.approved_rejected_by = serializer.validated_data["approved_rejected_by"]
        req.approved_rejected_comment = serializer.validated_data["approved_rejected_comment"]
        req.approved_rejected_at = datetime.now()
        req.save()
        if req.status == "Approved":
            process.approved_headcount = round(req.requested_approved_headcount, 2)
            process.currency = req.requested_currency
            process.pricing = req.requested_pricing
            process.pricing_type = req.requested_pricing_type
            process.pricing_type_value = req.requested_pricing_type_value
            process.save()
        return HttpResponse(json.dumps({"message": "Process updated successful."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_hc_process(request):
    try:
        name = request.data.get("name")
        if request.user.designation.name == "Associate Director":
            if name:
                processes = list(
                    HeadcountProcess.objects.filter(name__icontains=name).values_list("id", "name", named=True))
            else:
                processes = list(
                    HeadcountProcess.objects.all().values_list("id", "name", named=True))
        else:
            if name:
                processes = list(
                    HeadcountProcess.objects.filter(name__icontains=name, is_active=True).values_list("id", "name",
                                                                                                      named=True))
            else:
                processes = list(
                    HeadcountProcess.objects.filter(rm=request.user, is_active=True).values_list("id", "name",
                                                                                                 named=True))
        return HttpResponse(json.dumps({"result": processes}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_subcampaign_by_process(request, proc_id):
    try:
        process = get_hc_process_by_id(proc_id)
        date = request.data.get("date")
        if not date:
            raise ValueError("Please provide valid Date.")
        existing = HeadcountReference.objects.filter(process=process, date=date)
        if existing:
            raise ValueError("Headcount has already been updated for {0}".format(date))
        if not process.sub_campaign.count() > 0:
            raise ValueError("No Sub-Campaign found for this Process.")
        sub_camp = SubCampaignSerializer(process.sub_campaign, many=True).data
        return HttpResponse(
            json.dumps({"result": {"sub_campaigns": sub_camp, "approved_headcount": process.approved_headcount}}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def validate_headcounts(headcount, approved_headcount):
    count = 0
    for hc in headcount:
        if not float(hc["scheduled_hc"]) >= float(hc["present_hc"]):
            raise ValueError(
                "Present headcount can't be greater than Scheduled Headcount. Please validate the data entered.")
        count += float(hc["scheduled_hc"])
    if not count <= approved_headcount:
        raise ValueError("Scheduled headcount can't be more than Approved Headcount. Please validate the data entered.")


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_today_hc(request):
    try:
        data = request.data
        process_id = data.get("process")
        process = get_hc_process_by_id(process_id)
        if not process_id or not process:
            raise ValueError("Please provide valid Process ID")
        headcount = data.get("sub_campaign")
        if not headcount:
            raise ValueError("Please provide Headcount Information.")
        hc_date = data.get("date")
        if not hc_date:
            raise ValueError("Please provide valid Date.")
        existing = HeadcountReference.objects.filter(process=process, date=hc_date)
        if existing:
            raise ValueError("Headcount has already been updated for {0}".format(hc_date))
        data = update_request(data, created_by=request.user.id, approved_headcount=process.approved_headcount)
        ref_serializer = HeadcountReferenceSerializer(data=data)
        if not ref_serializer.is_valid():
            return return_error_response(ref_serializer)
        restricted_date = datetime.today().date() - timedelta(days=4)
        if not ref_serializer.validated_data["date"] > restricted_date:
            raise ValueError(
                "Action not allowed. You can't update headcount for {0} or before.".format(restricted_date))
        if ref_serializer.validated_data["date"] > datetime.today().date():
            raise ValueError(
                "Action not allowed. You can't update headcount for future.".format(restricted_date))
        validate_headcounts(headcount, process.approved_headcount)
        ref = ref_serializer.create(ref_serializer.validated_data)
        per_day_price = 0
        if process.pricing_type == "FTE":
            per_day_price = process.pricing / process.pricing_type_value
        else:
            per_day_price = process.pricing_type_value * process.pricing
        hc_hours = settings.HEADCOUNT_HOURS if process.pricing_type == "FTE" else process.pricing_type_value
        target_revenue = 0
        achieved_revenue = 0
        leakage_revenue = 0
        for hc in headcount:
            data_hc = update_request(hc, created_by=request.user.id)
            serializer = HeadcountSerializer(data=data_hc)
            if not serializer.is_valid():
                return return_error_response(serializer)
            serializer.validated_data["present_hc"] = serializer.validated_data["present_hc"]
            serializer.validated_data["scheduled_hc"] = serializer.validated_data["scheduled_hc"]

            serializer.validated_data["total_hours"] = serializer.validated_data["present_hc"] * hc_hours

            serializer.validated_data["deficit"] = (serializer.validated_data["scheduled_hc"] - \
                                                    serializer.validated_data["present_hc"])
            target_revenue += serializer.validated_data["scheduled_hc"] * per_day_price
            achieved_revenue += serializer.validated_data["present_hc"] * per_day_price
            leakage_revenue += serializer.validated_data["deficit"] * per_day_price

            hc_obj = serializer.create(serializer.validated_data)
            ref.headcount.add(hc_obj)
        ref.target_revenue = target_revenue
        ref.achieved_revenue = achieved_revenue
        ref.leakage_revenue = leakage_revenue
        ref.save()
        return HttpResponse(json.dumps({"message": "Headcount for {0} updated successfully.".format(hc_date)}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetHeadcountByProcess(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetHeadcountRefSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"name": "process__name", 'sub_campaign': "sub_campaign__name",
                                "approved_headcount": "process__approved_headcount"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        if request.user.designation.name == "Associate Director":
            self.queryset = HeadcountReference.objects.all().filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
        else:
            self.queryset = HeadcountReference.objects.filter(process__rm=request.user).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_headcount_info_for_update(request, ref_id):
    try:
        if not ref_id:
            raise ValueError("Please provide valid Headcount ID")
        ref = HeadcountReference.objects.filter(id=ref_id).last()
        if not ref:
            raise ValueError("Headcount details with this ID not found.")
        headcount = HeadcountReferenceIndivSerializer(ref.headcount.all(), many=True).data
        return HttpResponse(json.dumps({"result": headcount}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_headcount(request, hc_id):
    try:
        hc = get_hc_by_id(hc_id)
        data = update_request(request.data, created_by=request.user.id, headcount=hc.id,
                              old_scheduled_hc=hc.scheduled_hc, old_present_hc=hc.present_hc)
        existing_uhc = UpdateHeadcountRequest.objects.filter(headcount=hc, status="Pending").last()
        if existing_uhc:
            raise ValueError("There is a pending update-headcount-request")
        serializer = UpdateHeadcountSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        all_headcount = HeadcountReference.objects.filter(headcount=hc).last()
        hc_sum = 0
        for hc_obj in all_headcount.headcount.all():
            if not hc == hc_obj:
                hc_sum += hc_obj.scheduled_hc
        if serializer.validated_data["scheduled_hc"] > all_headcount.approved_headcount - hc_sum:
            raise ValueError("Sum of Scheduled HC can't be greater than Approved Headcount")
        if serializer.validated_data["present_hc"] > serializer.validated_data["scheduled_hc"]:
            raise ValueError("Present HC can't be greater than Scheduled HC.")
        serializer.validated_data["status"] = "Pending"
        req = serializer.create(serializer.validated_data)
        return HttpResponse(json.dumps({"message": "Request to update Headcount is created successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def approve_update_headcount(request, req_id):
    try:
        usr = request.user
        req = UpdateHeadcountRequest.objects.filter(id=req_id).last()
        if not req:
            raise ValueError("Please provide valid Approval ID")
        if not req.status == "Pending":
            raise ValueError("This request has already been {0}.".format(req.status))
        data = update_request(request.data, approved_rejected_by=usr.id)
        if not usr.designation.name == "Associate Director":
            raise ValueError("You are not authorized to Approve/Reject the request.")
        serializer = ApproveUpdateHeadcountSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        req.status = serializer.validated_data["status"]
        req.approved_rejected_by = serializer.validated_data["approved_rejected_by"]
        req.approved_rejected_comment = serializer.validated_data["approved_rejected_comment"]
        req.approved_rejected_at = datetime.now()
        req.save()
        if req.status == "Approved":
            hc = get_hc_by_id(req.headcount.id)
            hc.scheduled_hc = req.scheduled_hc
            hc.present_hc = req.present_hc
            hc.deficit = hc.scheduled_hc - hc.present_hc

            hc_ref = HeadcountReference.objects.filter(headcount=hc).last()
            hc_hours = settings.HEADCOUNT_HOURS if hc_ref.process.pricing_type == "FTE" else hc_ref.process.pricing_type_value

            hc.total_hours = hc.present_hc * hc_hours
            hc.save()

            if hc_ref.process.pricing_type == "FTE":
                per_day_price = hc_ref.process.pricing / hc_ref.process.pricing_type_value
            else:
                per_day_price = hc_ref.process.pricing_type_value * hc_ref.process.pricing
            target_revenue = 0
            achieved_revenue = 0
            leakage_revenue = 0

            for hc_obj in hc_ref.headcount.all():
                target_revenue += hc_obj.scheduled_hc * per_day_price
                achieved_revenue += hc_obj.present_hc * per_day_price
                leakage_revenue += hc_obj.deficit * per_day_price
            hc_ref.target_revenue = target_revenue
            hc_ref.achieved_revenue = achieved_revenue
            hc_ref.leakage_revenue = leakage_revenue

            hc_ref.save()

        return HttpResponse(json.dumps({"message": "Headcount updated successfully."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllHeadcountRequest(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetUpdateHeadcountSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        mapping_column_names = {"name": "process__name", "sub_campaign": "headcount__sub_campaign__name",
                                "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name",
                                "approved_rejected_by_emp_id": "approved_rejected_by__emp_id",
                                "approved_rejected_by_name": "approved_rejected_by__full_name",
                                "process": "headcount__process__name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                             fields_look_up=mapping_column_names)
        self.queryset = UpdateHeadcountRequest.objects.all().filter(**filter_by).filter(
            search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


def get_all_column_names(process):
    column_names = ["Date", "Approved Headcount"]
    for sub_campaign in process.sub_campaign.all():
        column_names.append(sub_campaign.name + " " + "Scheduled HC")
    for sub_campaign in process.sub_campaign.all():
        column_names.append(sub_campaign.name + " " + "Present HC")
    for sub_campaign in process.sub_campaign.all():
        column_names.append(sub_campaign.name + " " + "Deficit HC")
    column_names.append("Total Hours")
    return column_names


def get_row_data(row_data, hc, app_hc, hc_hours):
    row_data.append(app_hc)
    sub_camp = hc.headcount.all()
    present_count = 0
    for camp in sub_camp:
        row_data.append(camp.scheduled_hc)
    for camp in sub_camp:
        row_data.append(camp.present_hc)
        present_count += camp.present_hc
    for camp in sub_camp:
        row_data.append(camp.deficit)
    row_data.append(present_count * hc_hours)
    return row_data


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def export_headcount(request):
    try:
        data = request.data
        today = datetime.today().date()
        start_date = data.get('start_date', today)
        end_date = data.get('end_date', today)
        process_id = data.get('process')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Attendance_report.csv"'
        writer = csv.writer(response)
        date_range = get_dates_range(datetime.fromisoformat(start_date).date(),
                                     datetime.fromisoformat(end_date).date())

        if not process_id:
            raise ValueError("Please provide a valid Process.")
        elif process_id == "__all_":
            if request.user.designation.name == "Associate Director":
                process = HeadcountProcess.objects.all()
                headcount = HeadcountReference.objects.filter(date__gte=start_date, date__lte=end_date)

            else:
                process = HeadcountProcess.objects.filter(rm=request.user)
                headcount = HeadcountReference.objects.filter(date__gte=start_date, date__lte=end_date,
                                                              process__rm=request.user)
            if not process:
                return response
            for proc in process:
                writer.writerow([proc.name])
                column_names = get_all_column_names(proc)
                column_names += ["Target Revenue", "Achieved Revenue", "Leakage Revenue"]
                writer.writerow(column_names)
                hc_hours = settings.HEADCOUNT_HOURS if proc.pricing_type == "FTE" else proc.pricing_type_value

                for date in date_range:
                    row = [date]
                    hc = headcount.filter(date=date, process=proc).last()
                    if hc:
                        row = get_row_data(row, hc, hc.approved_headcount, hc_hours)
                        row.append(round(hc.target_revenue, 2))
                        row.append(round(hc.achieved_revenue, 2))
                        row.append(round(hc.leakage_revenue, 2))
                    else:
                        row.extend([0] * (len(column_names) - 1))

                    writer.writerow(row)
                writer.writerow([""])

        else:
            try:
                process = get_hc_process_by_id(process_id)
            except Exception as e:
                raise ValueError(str(e))
            headcount = HeadcountReference.objects.filter(date__gte=start_date, date__lte=end_date, process=process)

            column_names = get_all_column_names(process)
            column_names += ["Target Revenue", "Achieved Revenue", "Leakage Revenue"]
            writer.writerow(column_names)
            hc_hours = settings.HEADCOUNT_HOURS if process.pricing_type == "FTE" else process.pricing_type_value

            for date in date_range:
                row = [date]
                hc = headcount.filter(date=date).last()
                if hc:
                    row = get_row_data(row, hc, hc.approved_headcount, hc_hours)
                    row.append(round(hc.target_revenue, 2))
                    row.append(round(hc.achieved_revenue, 2))
                    row.append(round(hc.leakage_revenue, 2))
                else:
                    row.extend([0] * (len(column_names) - 1))
                writer.writerow(row)

        return response

    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
