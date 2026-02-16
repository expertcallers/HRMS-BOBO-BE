import json
import logging
import os.path
import traceback
from datetime import datetime
import numpy as np

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
import pandas as pd
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from mapping.views import HasUrlPermission
from report.models import *
from report.serializers import *
from team.models import Process
from utils.util_classes import CustomTokenAuthentication
from utils.utils import read_file_format_output, get_sort_and_filter_by_cols, parse_boolean_value, return_error_response

logger = logging.getLogger(__name__)


# Create your views here.

def fill_row(data, row_col_id, col_wise=False):
    value = None
    if not col_wise:
        for i, v in enumerate(data.iloc[row_col_id]):
            if not pd.isna(v):
                value = v
            if i != 0:
                data.at[row_col_id, i] = value
    else:
        for i, v in data[row_col_id].items():
            if not pd.isna(v):
                value = v
            data.at[i, row_col_id] = value
    return data


def convert_percentage(value):
    if isinstance(value, str) or pd.isna(value) or isinstance(value, int):
        return value
    else:
        return f"{round(value * 100, 2)}%"


class GetAllReportsFiles(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllReportsFilesSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET)
        self.queryset = ReportFile.objects.filter(search_query).filter(**filter_by).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


class GetMyReportsFile(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllReportsFilesSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET)
        self.queryset = ReportFile.objects.filter(uploaded_by=request.user.emp_id).filter(search_query).filter(
            **filter_by).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def delete_report_file(request, report_id):
    try:
        report = ReportFile.objects.filter(id=report_id).last()
        if report is None:
            raise ValueError("invalid report id")
        if report.uploaded_by != request.user.emp_id:
            raise ValueError("You did you not upload this file")
        report.delete()
        return HttpResponse(json.dumps({"message": "Report Deleted Successfully"}))
    except Exception as e:
        logger.info("exception at delete_report_file {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


def handle_file_import(request, process, model, sheet_variable=None, converters=None, header=None, consider_date=False):
    xl_file = request.data.get("report_file")
    if not xl_file:
        raise ValueError("Please upload excel report file")
    try:
        exl_file = pd.ExcelFile(xl_file)
    except Exception as e:
        raise ValueError("Invalid file, please upload an excel file")
    file_name = os.path.basename(xl_file.name)
    file_sheet_name = None
    sheet_variable_count = 0
    if len(exl_file.sheet_names) > 1:
        if sheet_variable is None or str(sheet_variable).strip() == "":
            raise ValueError("no sheet_variable provided")
        for sheet_name in exl_file.sheet_names:
            if sheet_variable.lower() in sheet_name.lower():
                file_sheet_name = sheet_name
                sheet_variable_count += 1
        if file_sheet_name is None:
            raise ValueError(
                "No matching sheetname for key-word {0}, upload excel with correct sheet name for process {1}".format(
                    sheet_variable, process))
        if sheet_variable_count > 1:
            raise ValueError(f"Expected One sheet with keyword {sheet_variable}, but found many sheets")
    if file_sheet_name:
        xl_data = pd.read_excel(xl_file, sheet_name=file_sheet_name, header=header, converters=converters)
    else:
        xl_data = pd.read_excel(xl_file, header=header, converters=converters)
    overwrite = parse_boolean_value(request.data.get("overwrite"))
    if consider_date:
        report_file = ReportFile.objects.filter(file_name=file_name, sheet_name=file_sheet_name, process=process,
                                                category=model.__name__, upload_date=datetime.now().date()).last()
    else:
        report_file = ReportFile.objects.filter(file_name=file_name, sheet_name=file_sheet_name, process=process,
                                                category=model.__name__).last()

    return xl_data, file_name, file_sheet_name, overwrite, report_file


def get_month_and_year(file_sheet_name):
    try:
        month, year = [str(i).strip() for i in file_sheet_name.split("-")[1].split(" ") if str(i).isdigit()]
        if len(str(year)) == 2:
            year = f"20{year}"
        return month, year
    except Exception as e:
        raise ValueError(
            'sheet name "{0}" must be of this format  "sheet_name - month_number year"'.format(file_sheet_name))


def handle_sla(request, process):
    usr = request.user
    metrics = {"target": 1, "target - 800/fte/day": 2, "target- 800/fte": 3, "overall": 4, "timeout hour": 5,
               "yes/no": 6, "achieved": 7, "achieved days": 8}
    xl_data, file_name, file_sheet_name, overwrite, report_file = handle_file_import(request, process, SLA,
                                                                                     sheet_variable="SLA")
    report_file, existing_content = get_existing_content(SLA, report_file, overwrite, usr, file_sheet_name, file_name,
                                                         process, year_month=True)

    for i in [0, 1]:
        xl_data = fill_row(xl_data, i)
    cols = xl_data.columns
    sla_list = []
    for col in cols[1:]:
        task = xl_data[col].iloc[0]
        index = xl_data[col].iloc[1]
        metric = xl_data[col].iloc[2]
        count = 3
        task_reference = SLATaskReference.objects.filter(name__iexact=task).last()
        if task_reference is None:
            task_reference = SLATaskReference.objects.create(name=task)

        for val in xl_data[col].iloc[3:]:
            metric_id = metrics.get(task.lower())
            date = xl_data[0].iloc[count]
            if not isinstance(date, datetime):
                break
            else:
                date = date.date()

            bigo_sla = SLA(task=task_reference, index=index, metric=metric, metric_id=metric_id, date=date,
                           value=val, report_file=report_file, created_by=usr.emp_id)
            serializer = CreateSLASerializer(data=bigo_sla.__dict__)
            if not serializer.is_valid():
                return return_error_response(serializer, raise_exception=True)
            sla_list.append(bigo_sla)
            count += 1
    message = "No changes Made"

    if len(sla_list) > 0:
        if overwrite and existing_content and existing_content.count() > 0:
            existing_content.delete()
        SLA.objects.bulk_create(sla_list)
        return 1, None
    return 0, message


def get_existing_content(model, report_file, overwrite, usr, file_sheet_name, file_name, process, year_month=False):
    existing_content = None
    month = None
    year = None
    if report_file:
        existing_content = model.objects.filter(report_file=report_file)
        if existing_content.count() > 0 and not overwrite:
            raise ValueError("This file already uploaded, select overwrite value to overwrite the existing content")
        report_file.uploaded_by = usr.emp_id
        report_file.uploaded_by_name = usr.full_name
        report_file.upload_date = datetime.now().date()
        report_file.save()
    else:
        if year_month:
            month, year = get_month_and_year(file_sheet_name)
        report_file = ReportFile.objects.create(file_name=file_name, sheet_name=file_sheet_name, month=month,
                                                category=model.__name__,
                                                upload_date=datetime.now().date(), year=year, uploaded_by=usr.emp_id,
                                                uploaded_by_name=usr.full_name, process=process)
    return report_file, existing_content


def handle_ta(request, process, main_task_dict=None, main_task=None):
    usr = request.user

    # Specify columns that should be treated as percentages
    percentage_columns = [2, 4, 7]  # Adjust these column indices based on your actual data

    # Create a dictionary of converters
    converters_dict = {col: convert_percentage for col in percentage_columns}

    xl_data, file_name, file_sheet_name, overwrite, report_file = handle_file_import(request, process, TA,
                                                                                     sheet_variable="target",
                                                                                     converters=converters_dict)
    xl_data = xl_data[(xl_data[0] != "Summary") & (xl_data[0] != "ID Management") & (xl_data[1] != "Total")]

    report_file, existing_content = get_existing_content(TA, report_file, overwrite, usr, file_sheet_name, file_name,
                                                         process, year_month=True)

    month, year = get_month_and_year(file_sheet_name)

    for i in [0, 1]:
        xl_data = fill_row(xl_data, i, col_wise=True)

    ta_list = []
    has_date = False
    if 8 in xl_data.columns:
        has_date = True

    main_task_id = None
    main_task_loc = main_task

    for index, row in xl_data[1:].iterrows():

        if main_task is None:
            main_task_loc = row[0]
            main_task_id = main_task_dict.get(main_task_loc.lower())

        date = None
        if has_date:
            try:
                date = row[8].date() if isinstance(row[8], datetime) else datetime.fromisoformat(row[8]).date()
            except Exception as e:
                date = None
        task_reference = SLATaskReference.objects.filter(name__iexact=row[1]).last()
        if task_reference is None:
            task_reference = SLATaskReference.objects.create(name=row[1])

        ta = TA(main_task=main_task_loc, main_task_id=main_task_id, task=task_reference, weight=row[2],
                index_for_the_whole_team=row[3], daily_target_of_the_whole_team=row[4], days=row[5],
                days_achieved_the_target=row[6], achieved_ratio=row[7], date=date, report_file=report_file,
                created_by=usr.emp_id, month=month, year=year)
        serializer = CreateTASerializer(data=ta.__dict__)
        if not serializer.is_valid():
            return return_error_response(serializer, raise_exception=True)
        ta_list.append(ta)
    message = "No changes Made"

    if len(ta_list) > 0:
        if overwrite and existing_content and existing_content.count() > 0:
            existing_content.delete()
        TA.objects.bulk_create(ta_list)
        return 1, None
    return 0, message


def check_and_get_process(name):
    process = Process.objects.filter(name=name).last()
    if process is None:
        raise ValueError("Please contact the CC-Team, {0} campaign name changed, update report-view-code".format(name))
    return process


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def import_bigo_sla(request):
    try:
        val, message = handle_sla(request, "bigo")
        if val:
            message = "Bigo SLA updated successfully"
        return HttpResponse(json.dumps({"message": message}))

    except Exception as e:
        logger.info("exception at import_bigo_sla {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def import_bigo_ta(request):
    try:
        main_task_dict = {"tiki": 1, "likee live": 2, "imo": 3, "hello yo": 4, "bigo": 5, "2nd recheck": 6,
                          "id management": 7, "ads": 8, "qa": 9}
        val, message = handle_ta(request, "bigo", main_task_dict=main_task_dict)
        if val:
            message = "BigoTA updated successfully"
        return HttpResponse(json.dumps({"message": message}))

    except Exception as e:
        logger.info("exception at import_bigo_ta {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def import_tiya_sla(request):
    try:
        # process = check_and_get_process("TIYA")
        val, message = handle_sla(request, "tiya")
        if val:
            message = "Tiya SLA updated successfully"
        return HttpResponse(json.dumps({"message": message}))

    except Exception as e:
        logger.info("exception at import_tiya_sla {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def import_tiya_ta(request):
    try:
        val, message = handle_ta(request, "tiya", main_task="tiya")
        if val:
            message = "Tiya TA updated successfully"
        return HttpResponse(json.dumps({"message": message}))

    except Exception as e:
        logger.info("exception at import_tiya_ta {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


def handle_normal_data_import(request, process, sheet_variable, model, serializer_object, date_cols=[], new_cols={},
                              map_cols={}):
    usr = request.user
    xl_data, file_name, file_sheet_name, overwrite, report_file = handle_file_import(
        request, process, model, sheet_variable=sheet_variable, header=0, consider_date=True)

    for key in map_cols.keys():
        if key in xl_data.columns:
            xl_data.rename(columns={key: map_cols[key]}, inplace=True)
    xl_data.columns = [str(i).lower().replace(" ", "_") for i in xl_data.columns]
    for ncol in new_cols.keys():
        xl_data[ncol] = new_cols[ncol]
    columns = xl_data.columns
    if len(date_cols):
        for col in date_cols:
            if col in columns:
                try:
                    xl_data[col] = xl_data[col].dt.date
                except:
                    raise ValueError("date columns must be in the format YYYY-MM-DD")
    for column in columns:
        xl_data[column] = xl_data[column].replace(np.nan, None)
    validated_data_list = []
    report_file, existing_content = get_existing_content(model, report_file, overwrite, usr, file_sheet_name, file_name,
                                                         process)

    for index, row in xl_data.iterrows():
        row_data = dict(zip(columns, row))
        serializer = serializer_object(data=row_data)
        if not serializer.is_valid():
            raise return_error_response(serializer, raise_exception=True)
        validated_data_list.append(model(**serializer.validated_data, report_file=report_file))
    message = "No changes made"
    if len(validated_data_list) > 0:
        if overwrite and existing_content and existing_content.count() > 0:
            existing_content.delete()
        message = "Data updated successfully"
        model.objects.bulk_create(validated_data_list)
    return message


# def update_serializers(report_dict):
#     for i in report_dict.keys():
#         report_dict[i]["serializer"] = create_serializer_class(report_dict[i]["class"])
#
#     return report_dict


def get_normal_report_data(report_name):
    if report_name is None:
        raise ValueError("Please provide valid report_name")

    report_dict = {"gbm_dialer": {"process": "GBM", "sheet_variable": "dialer", "class": GbmDialer,
                                  "serializer": GbmDialerSerializer, "date_cols": ["date"]},
                   "gbm_call": {"process": "GBM", "sheet_variable": "call", "class": GbmCall,
                                "serializer": GbmCallSerializer, "date_cols": ["date"]},
                   "gbm_lead": {"process": "GBM", "sheet_variable": "lead", "class": GbmLead,
                                "serializer": GbmLeadSerializer, "date_cols": ["date"]},
                   "gbm_email": {"process": "GBM", "sheet_variable": "email", "class": GbmEmail,
                                 "serializer": GbmEmailSerializer, "date_cols": ["date"]},
                   "aadhya_b2b": {"process": "Aadhya Solutions", "sheet_variable": "b2b", "class": AadyaSolutions,
                                  "serializer": AadyaSolutionsSerializer, "date_cols": ["date"]},
                   "insalvage": {"process": "Insalvage", "sheet_variable": "insalvage", "class": Insalvage,
                                 "serializer": InsalvageSerializer, "date_cols": ["date"]},
                   "medicare": {"process": "Medicare", "sheet_variable": "medicare", "class": Medicare,
                                "serializer": MedicareSerializer, "date_cols": ["date", "appt_date"]},
                   "sapphire_medical": {"process": "Sapphire Medicals", "sheet_varialble": "sapphire",
                                        "class": SapphireMedical,
                                        "serializer": SapphireMedicalSerializer, "date_cols": ["date_of_birth"]},
                   "capgemini": {"process": "Capgemini America", "sheet_variable": "iro list", "class": Capgemini,
                                 "serializer": CapgeminiSerializer, "date_cols": ["call_date"]},
                   "bbm": {"process": "Blue Book Milwaukee", "sheet_variable": "blue book milwaukee", "class": BBM,
                           "serializer": BBMSerializer, "date_cols": ["date"]}
                   }
    if report_dict.get(report_name) is None:
        raise ValueError(f"There is no report with report-name {report_name}")
    # report_dict = update_serializers(report_dict)
    rep_data = report_dict.get(report_name)
    process = rep_data.get("process")
    sheet_variable = rep_data.get("sheet_variable")
    class_name = rep_data.get("class")
    serializer_name = rep_data.get("serializer")
    date_cols = rep_data.get("date_cols")
    if process is None or sheet_variable is None or class_name is None or serializer_name is None or date_cols is None:
        raise ValueError(
            f"report-configuration data is not valid for report-name {report_name}, please update it to cc-team")
    return rep_data


def handle_import_normal_reports(request, report_name, **kwargs):
    rep_data = get_normal_report_data(report_name)
    message = handle_normal_data_import(request, rep_data["process"], rep_data["sheet_variable"],
                                        rep_data.get("class"), rep_data.get("serializer"),
                                        date_cols=rep_data["date_cols"], **kwargs)
    return message


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def import_gbm_reports(request, report_name):
    try:
        message = handle_import_normal_reports(request, report_name)
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at import_gbm_dialer {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def import_aadhya_reports(request, call_type):
    try:
        if call_type is None or str(call_type).strip() == "" or str(call_type).lower() not in ["b2b", "b2c"]:
            raise ValueError("please provide valid call_type as b2b or b2c")

        new_cols = {"call_type": str(call_type).lower()}
        map_cols = {"status": "connect_type", "dispositions": "status", "agent": "user"}
        message = handle_import_normal_reports(request, "aadhya_b2b", new_cols=new_cols, map_cols=map_cols)
        return HttpResponse(json.dumps({"message": message}))

    except Exception as e:
        logger.info("exception at import_gbm_dialer {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def import_insalvage(request):
    try:
        message = handle_import_normal_reports(request, "insalvage")

        return HttpResponse(json.dumps({"message": message}))

    except Exception as e:
        logger.info("exception at import_gbm_dialer {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def import_medicare(request):
    try:
        message = handle_import_normal_reports(request, "medicare")
        return HttpResponse(json.dumps({"message": message}))

    except Exception as e:
        logger.info("exception at import_gbm_dialer {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def import_sapphire_medical_reports(request):
    try:
        message = handle_import_normal_reports(request, "sapphire_medical")
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at import_gbm_dialer {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def import_capgemini_report(request):
    try:
        message = handle_import_normal_reports(request, "capgemini")
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at import_gbm_dialer {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def import_bbm_report(request):
    try:
        map_cols = {"EMP ID": "emp_id", "Date": "date", "Center": "center", "Agent Name": "agent_name",
                    "Disposition": "disposition", "Call Type": "call_type"}
        message = handle_import_normal_reports(request, "bbm", map_cols=map_cols)
        return HttpResponse(json.dumps({"message": message}))
    except Exception as e:
        logger.info("exception at import_gbm_dialer {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)
