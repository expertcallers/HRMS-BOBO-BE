import csv
import json
import logging
import traceback
from datetime import datetime
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated

from appraisal.models import *
from appraisal.serializers import SearchParameterSerializer, GetAllEmpAppraisalSerializer, \
    CreatePartDAppraiseeSerializer, DevtActionRespSerializer, TrainingTimeSerializer, GetPartDAppraiseeSerializer, \
    UpdatePartDAppraiseeSerializer, GetAllEligibleAppraisalListSerializer
from mapping.models import Profile, MiscellaneousMiniFields
from mapping.views import HasUrlPermission
from team.models import Team
from team.serializer import AppendNameEmpIDSerializer
from utils.util_classes import CustomTokenAuthentication
from utils.utils import get_emp_by_emp_id, get_sort_and_filter_by_cols, update_request, return_error_response, \
    parse_boolean_value, get_team_ids, tz, check_appraisal_last_date, get_appraisal_eligible_date, \
    get_exclude_appraisal_emps

logger = logging.getLogger(__name__)


def check_appraisal_eligibility(emp):
    app_date = get_appraisal_eligible_date()
    logger.info(f"date_of_joining, {emp.date_of_joining}")
    if emp.date_of_joining > app_date:
        raise ValueError(
            f"You are not eligible for the appraisal, joining-date must be less than or equal to {app_date}")


# Create your views here.
@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_designation_mapping(request):
    try:
        usr = request.user
        teams = get_team_ids(usr)
        if teams is None:
            raise ValueError("There are no teams under you")
        app_date = get_appraisal_eligible_date()
        existing_emps = list(EmpAppraisal.objects.filter(
            year=datetime.now().year, employee__team__id__in=teams).values_list(
            "employee__emp_id", flat=True))
        exclude_emps = get_exclude_appraisal_emps()
        existing_emps += exclude_emps
        designation_to_be_added = Profile.objects.exclude(emp_id__in=existing_emps).filter(
            status="Active", date_of_joining__lte=app_date, team__id__in=teams).values_list(
            "designation__id", flat=True)
        names = []
        map_desi_dict = {}
        map_desi = DesiMap.objects.all()
        for md in map_desi:
            for desi in md.designations.all().values_list("id", flat=True):
                map_desi_dict[desi] = md.name

        for desi in designation_to_be_added:
            group = map_desi_dict.get(desi)
            if group:
                names.append(group)
        return HttpResponse(json.dumps({"desi_map": list(set(names))}))
    except Exception as e:
        logger.info("exception at get_designation_mapping {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_parameter_name(request):
    try:
        parameter_name = request.data.get("parameter_name")
        if parameter_name is None or str(parameter_name).strip() == "":
            return HttpResponse(json.dumps({"result": []}))
        parameters = Parameter.objects.filter(name__icontains=parameter_name, type="A").values_list("id", "name")
        return HttpResponse(json.dumps({"result": list(parameters)}))
    except Exception as e:
        logger.info("exception at get_parameter_name {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def add_parta_parameter(request):
    try:
        check_appraisal_last_date()
        usr = request.user
        emp_list = request.data.get("emp_list")
        parameter_list = request.data.get("parameter_list")
        para_obj_list = []
        emp_parameter_list = []
        update_emp_param_list = []
        emp_appraisals = []
        if len(emp_list) == 0:
            raise ValueError("Please select employees")

        # [{"parameter_id":None,"parameter_name":"abc","score":0}]
        if not isinstance(emp_list, list) or not isinstance(parameter_list, list):
            raise ValueError("emp_list and parameter_list are not in list format, contact cc-team")

        total_score = 0
        params_list = []
        params_id_list = []
        for parameter_dict in parameter_list:

            if not isinstance(parameter_dict, dict):
                raise ValueError("parameter data not in dictionary format, contact cc-team")
            if parameter_dict["parameter_name"] is None and parameter_dict["parameter_id"] is None:
                raise ValueError("parameter name is not provided")
            if not str(parameter_dict["score"]).isdigit():
                raise ValueError("score should be numeric")
            if parameter_dict["parameter_name"] in params_list or parameter_dict["parameter_id"] in params_id_list:
                raise ValueError("duplicate parameters are not allowed")
            if parameter_dict["parameter_name"]:
                params_list.append(str(parameter_dict["parameter_name"]).strip())
            if parameter_dict["parameter_id"]:
                params_id_list.append(parameter_dict["parameter_id"])
            total_score += int(parameter_dict["score"])

        if total_score != 100:
            raise ValueError("Total weightage must be 100")
        employees = Profile.objects.filter(emp_id__in=emp_list)
        for emp in employees:
            emp_appraisals.append(EmpAppraisal.objects.create(employee=emp))

        for parameter_dict in parameter_list:
            param_name = parameter_dict["parameter_name"]
            param_name = str(param_name).strip() if param_name else None
            score = parameter_dict["score"]
            param_id = parameter_dict["parameter_id"]
            para_obj = None
            if param_id:
                para_obj = Parameter.objects.filter(id=param_id, type="A").last()
            if para_obj is None and param_name:
                para_obj = Parameter.objects.filter(name__iexact=param_name, type="A").last()
            if para_obj is None:
                para_obj = Parameter.objects.create(name=param_name, type="A")
            para_obj_list.append({"para_obj": para_obj, "score": score})

        for emp_app in emp_appraisals:
            for para_obj_dict in para_obj_list:
                emp_param = EmployeeParameter.objects.filter(emp_appraisal=emp_app,
                                                             parameter=para_obj_dict["para_obj"]).first()

                if emp_param is None:
                    emp_parameter_list.append(
                        EmployeeParameter(parameter=para_obj_dict["para_obj"], emp_appraisal=emp_app, created_by=usr,
                                          score=para_obj_dict["score"]))
                else:
                    if emp_param.score != int(para_obj_dict["score"]):
                        emp_param.score = int(para_obj_dict["score"])
                        update_emp_param_list.append(emp_param)
        if len(emp_parameter_list) > 0:
            EmployeeParameter.objects.bulk_create(emp_parameter_list)
        if len(update_emp_param_list) > 0:
            EmployeeParameter.objects.bulk_update(emp_parameter_list, ["score"])
        return HttpResponse(json.dumps({"message": "Added part-A parameters "}))
    except Exception as e:
        logger.info("exception at add_parta_parameter {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_employees_tobe_added(request):
    try:
        name = request.data.get("name")
        map_desi_name = request.data.get("map_desi_name")
        if map_desi_name is None or str(map_desi_name).strip() == "":
            raise ValueError("please provide designation mapping name")
        map_desi = DesiMap.objects.filter(name=map_desi_name).first()
        if map_desi is None:
            raise ValueError(f"designation mapping {map_desi} does not exist")
        teams = get_team_ids(request.user)
        if teams is None:
            raise ValueError("there are no teams under you")
        existing_emps = list(EmpAppraisal.objects.filter(
            year=datetime.now().year, employee__team__id__in=teams).values_list(
            "employee__emp_id", flat=True))
        app_date = get_appraisal_eligible_date()
        # exclude the employees from the exclude list
        exclude_emps = get_exclude_appraisal_emps()
        existing_emps += exclude_emps
        profiles = Profile.objects.exclude(emp_id__in=existing_emps).filter(
            status="Active", date_of_joining__lte=app_date, team__id__in=teams).filter(
            designation__id__in=[desi.id for desi in map_desi.designations.all()])
        if name:
            profiles = profiles.filter(
                Q(emp_id__icontains=name) | Q(first_name__icontains=name) | Q(middle_name__icontains=name) | Q(
                    last_name__icontains=name)).order_by("id")

        profiles = AppendNameEmpIDSerializer(profiles, many=True).data
        return HttpResponse(json.dumps({"result": profiles}))
    except Exception as e:
        logger.info("exception at get_employees_tobe_added {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_default_params(request, desi_map_name):
    try:
        if desi_map_name is None or str(desi_map_name).strip() == "":
            return HttpResponse(json.dumps({"result": []}))
        def_params = DefaultParams.objects.filter(desi_map__name=desi_map_name)
        param_list = []
        # [{"parameter_id":None,"parameter_name":"abc","score":0}]
        for dp in def_params:
            param_list.append({"parameter_id": dp.parameter.id, "parameter_name": dp.parameter.name, "score": dp.score})
        return HttpResponse(json.dumps({"result": param_list}))
    except Exception as e:
        logger.info("exception at get_default_params {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_self_appraisal_status(request):
    try:
        to_be_completed = []
        emp_appraisal = get_appraisal_obj(None, emp=request.user)
        if emp_appraisal is None:
            check_appraisal_last_date()
            return HttpResponse(json.dumps({"message": "Parameters are not added"}))
        if emp_appraisal.status not in ["Self Appraisal In Progress", "Parameters Added"]:
            if emp_appraisal.status in ["Self Appraisal Completed", "Manager Appraisal In Progress"]:
                check_appraisal_last_date()
                return HttpResponse(json.dumps(
                    {"message": "Self appraisal is done, waiting for manager rating, please check back later"}))
            else:
                return HttpResponse(json.dumps({"status": emp_appraisal.status}))

        parta = PartA_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        emp_param = EmployeeParameter.objects.filter(emp_appraisal=emp_appraisal, parameter__type='A').first()
        if emp_param is None:
            raise ValueError("Parameters are not added for you")

        partb = PartB_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        partc = PartC_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        if parta is None:
            to_be_completed.append("A")
        if partb is None:
            to_be_completed.append("B")
        if partc is None:
            to_be_completed.append("C")
        return HttpResponse(json.dumps({"result": to_be_completed}))
    except Exception as e:
        logger.info("exception at get_self_appraisal_status {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_appraisal_obj(appraisal_id, emp=None, check_only_obj_existence=False):
    emp_appraisal = None
    if appraisal_id:
        emp_appraisal = EmpAppraisal.objects.filter(id=appraisal_id).first()
        if emp_appraisal is None:
            raise ValueError("invalid appraisal id")
        emp = emp_appraisal.employee
        check_appraisal_eligibility(emp)

    if emp_appraisal is None and emp:
        emp_appraisal = EmpAppraisal.objects.filter(employee=emp, year=datetime.now().year).first()
        check_appraisal_eligibility(emp)
        if emp_appraisal is None:
            raise ValueError("Waiting for your manager to add parameters")
    return emp_appraisal


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_mgr_appraisal_status(request, appraisal_id):
    try:
        to_be_completed = []
        emp_appraisal = get_appraisal_obj(appraisal_id)
        emp_param = EmployeeParameter.objects.filter(emp_appraisal=emp_appraisal).first()
        if emp_param is None:
            raise ValueError("Parameters are not added for you")
        parta = PartA_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        partb = PartB_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        partc = PartC_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        partd = PartD_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        if parta is None:
            raise ValueError("PartA of self appraisal is not done")
        if partb is None:
            raise ValueError("PartB of self appraisal is not done")
        if partc is None:
            raise ValueError("PartC of self appraisal is not done")
        if parta.mgr_score is None or parta.mgr_score == "":
            to_be_completed.append("A")
        if partb.mgr_score is None or partb.mgr_score == "":
            to_be_completed.append("B")
        if partc.mgr_score is None or partc.mgr_score == "":
            to_be_completed.append("C")
        if partd is None:
            to_be_completed.append("D")
        if len(to_be_completed) == 0:
            return HttpResponse(json.dumps({"message": "Manager appraisal is done"}))
        return HttpResponse(json.dumps({"result": to_be_completed}))
    except Exception as e:
        logger.info("exception at get_mgr_appraisal_status {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_self_appraisal_parameters(request, param_type):
    try:
        usr = request.user
        param_list = []
        emp_appraisal = get_appraisal_obj(None, emp=usr)
        emp_parameters = EmployeeParameter.objects.filter(emp_appraisal=emp_appraisal, parameter__type=param_type)
        for eparam in emp_parameters:
            param_list.append({"parameter_id": eparam.parameter.id, "parameter_name": eparam.parameter.name,
                               "score": eparam.score})
        # partc = PartC_Appraisee.objects.filter(created_at__year=year, employee=usr).first()
        rm1 = emp_appraisal.employee.team.manager
        rm2 = rm1.team.manager
        return HttpResponse(
            json.dumps({"parameters": param_list, "reviewer_name": rm1.full_name, "reviewer_desi": rm1.designation.name,
                        "supervisor_name": rm2.full_name, "supervisor_desi": rm2.designation.name}))
    except Exception as e:
        logger.info("exception at get_self_appraisal_status {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_mgr_appraisal_parameters(request, appraisal_id):
    try:
        usr = request.user
        param_list = []
        partabc = None
        emp_appraisal = get_appraisal_obj(appraisal_id)
        param_type = request.data.get("param_type")
        if param_type == "A":
            partabc = PartA_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        elif param_type == "B":
            partabc = PartB_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        elif param_type == "C":
            partabc = PartC_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        elif param_type == "D":
            pass
        else:
            raise ValueError(f"Invalid Part {param_type}")
        if param_type != "D" and (partabc is None or partabc.emp_score is None or str(partabc.emp_score).strip() == ""):
            raise ValueError("Manager appraisal for partA is not done")
        emp_parameters = EmployeeParameter.objects.filter(emp_appraisal=emp_appraisal, parameter__type=param_type)
        for eparam in emp_parameters:
            param_list.append({"parameter_id": eparam.parameter.id, "parameter_name": eparam.parameter.name,
                               "score": eparam.score, "emp_rating": eparam.emp_rating,
                               "emp_comment": eparam.emp_comment})
        # partc = PartC_Appraisee.objects.filter(created_at__year=year, employee=usr).first()
        rm1 = emp_appraisal.employee.team.manager
        rm2 = rm1.team.manager
        response = {"parameters": param_list, "reviewer_name": rm1.full_name, "reviewer_desi": rm1.designation.name,
                    "supervisor_name": rm2.full_name, "supervisor_desi": rm2.designation.name}
        if param_type == "A":
            response["emp_special_comment"] = partabc.emp_special_comment
        return HttpResponse(
            json.dumps(response))
    except Exception as e:
        logger.info("exception at get_mgr_appraisal_parameters {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def add_partbc_self_appraisal_rating(parameters, PartBC_Appraisee, emp_appraisal, param_type, mgr_appraisal=False,
                                     created_by=None):
    partabc_list = []
    partabc_update_list = []
    total_score = 0
    partbc = PartBC_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
    if partbc is not None and not mgr_appraisal:
        raise ValueError(f"Part {param_type} self appraisal already done for this employee")

    paratb_params = Parameter.objects.filter(type=param_type)

    if (paratb_params.count() != 22 and param_type == "B") or (paratb_params.count() != 5 and param_type == "C"):
        raise ValueError(f"default parameters for part {param_type} are not added  properly in the backend")
    for eparam in parameters:
        if mgr_appraisal:
            total_score += float(eparam["mgr_rating"])
            emp_param = EmployeeParameter.objects.filter(
                parameter__name=eparam["parameter_name"], emp_appraisal=emp_appraisal,
                created_by=emp_appraisal.employee).last()
            emp_param.mgr_rating = float(eparam["mgr_rating"])
            emp_param.mgr_comment = eparam["mgr_comment"]
            emp_param.updated_at = datetime.now()
            partabc_update_list.append(emp_param)

        else:
            total_score += float(eparam["emp_rating"])
            emp_param = EmployeeParameter.objects.filter(
                parameter__name=eparam["parameter_name"], emp_appraisal=emp_appraisal,
                created_by=emp_appraisal.employee).last()
            if emp_param is None:
                partabc_list.append(
                    EmployeeParameter(parameter=paratb_params.filter(name=eparam["parameter_name"]).last(),
                                      emp_appraisal=emp_appraisal, emp_rating=float(eparam["emp_rating"]),
                                      emp_comment=eparam["emp_comment"], created_by=emp_appraisal.employee))
            else:
                emp_param.emp_rating = eparam["emp_rating"]
                emp_param.emp_comment = eparam["emp_comment"]
                emp_param.updated_at = datetime.now()
                partabc_update_list.append(emp_param)
    if param_type == "B":
        total_score = round(total_score / 22, 2)
    elif param_type == "C":
        total_score = round(total_score / 5, 2)
    else:
        raise ValueError(f"Invalid param type {param_type}")

    if not mgr_appraisal:
        if len(partabc_list) > 0:
            EmployeeParameter.objects.bulk_create(partabc_list)
        if len(partabc_update_list) > 0:
            EmployeeParameter.objects.bulk_update(partabc_update_list,
                                                  ["emp_rating", "emp_comment", "updated_at"])

        PartBC_Appraisee.objects.create(emp_score=total_score, emp_appraisal=emp_appraisal)
    else:

        EmployeeParameter.objects.bulk_update(partabc_update_list,
                                              ["mgr_rating", "mgr_comment", "updated_at"])
        partbc.mgr_score = total_score
        partbc.save()


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def add_self_appraisal(request, param_type):
    try:
        check_appraisal_last_date()
        emp_appraisal = get_appraisal_obj(None, emp=request.user)
        if emp_appraisal.status not in ["Self Appraisal In Progress", "Parameters Added"]:
            return HttpResponse(json.dumps({"message": emp_appraisal.status}))
        parameters = request.data.get("parameters")
        if parameters is None or not isinstance(parameters, list):
            raise ValueError("please send list of parameters")
        if param_type == "A":
            partabc_list = []

            parta = PartA_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
            if parta is not None:
                raise ValueError("PartA is already done")
            total_score = 0
            for eparam in parameters:
                emp_param_obj = EmployeeParameter.objects.filter(parameter__id=eparam["parameter_id"],
                                                                 emp_appraisal=emp_appraisal).last()
                emp_param_obj.emp_rating = int(eparam["emp_rating"])
                emp_param_obj.emp_comment = eparam["emp_comment"]
                total_score += round((int(eparam["emp_rating"]) * int(emp_param_obj.score)) / 100, 2)
                partabc_list.append(emp_param_obj)
            if len(partabc_list) > 0:
                EmployeeParameter.objects.bulk_update(partabc_list, ["emp_rating", "emp_comment"])
                PartA_Appraisee.objects.create(emp_appraisal=emp_appraisal,
                                               emp_special_comment=request.data.get("emp_special_comment"),
                                               emp_score=total_score)
                emp_appraisal.status = "Self Appraisal In Progress"
                emp_appraisal.save()

        elif param_type == "B":
            add_partbc_self_appraisal_rating(parameters, PartB_Appraisee, emp_appraisal, "B")
        elif param_type == "C":
            add_partbc_self_appraisal_rating(parameters, PartC_Appraisee, emp_appraisal, "C")

        parta = PartA_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        partb = PartB_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        partc = PartC_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        if parta and partb and partc:
            emp_score = round(parta.emp_score * 70 / 100 + partb.emp_score * 20 / 100 + partc.emp_score * 10 / 100, 2)
            emp_appraisal.emp_score = emp_score
            emp_appraisal.self_appraisal_date = tz.localize(datetime.now())
            emp_appraisal.status = "Self Appraisal Completed"
            emp_appraisal.save()
            return HttpResponse(json.dumps({"message": f"self appraisal for employee is done successfully"}))

        return HttpResponse(json.dumps({"message": f"self appraisal for Part {param_type} is done successfully"}))
    except Exception as e:
        logger.info("exception at get_self_appraisal_status {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def add_partD_parameters(request, emp_appraisal, emp):
    partd = PartD_Appraisee.objects.filter(emp_appraisal=emp_appraisal).last()
    if partd:
        raise ValueError("PartD Appraisal is already done")
    data = update_request(request.data, employee=emp.id, emp_appraisal=emp_appraisal.id)
    partd_serializer = CreatePartDAppraiseeSerializer(data=request.data)
    if not partd_serializer.is_valid():
        return return_error_response(partd_serializer, raise_exception=True)
    dev_act_dev_res = data.get("dev_act_dev_res")
    dev_act_res_des_list = []
    training_time_list = []
    for dev_data in dev_act_dev_res:
        serializer = DevtActionRespSerializer(data=dev_data)
        if not serializer.is_valid():
            return return_error_response(serializer, raise_exception=True)
        dev_act_res_des_list.append(serializer.validated_data)

    training_time_data = data.get("training_time")
    for training_data in training_time_data:
        serializer = TrainingTimeSerializer(data=training_data)
        if not serializer.is_valid():
            return return_error_response(serializer, raise_exception=True)
        training_time_list.append(serializer.validated_data)

    partd = partd_serializer.create(partd_serializer.validated_data)

    dev_act_objs = []
    training_obj = []
    for dev_act in dev_act_res_des_list:
        dev_act_objs.append(DevActResDes(employee=emp, partd_appraisee=partd, **dev_act))
    for training_data in training_time_list:
        training_obj.append(TrainingTime(employee=emp, partd_appraisee=partd, **training_data))
    if len(dev_act_objs) > 0:
        DevActResDes.objects.bulk_create(dev_act_objs)
    if len(training_obj) > 0:
        TrainingTime.objects.bulk_create(training_obj)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def add_mgr_apprisal(request, appraisal_id):
    try:
        check_appraisal_last_date()
        usr = request.user
        parameters = request.data.get("parameters")
        emp_appraisal = get_appraisal_obj(appraisal_id)
        emp = emp_appraisal.employee
        param_type = request.data.get('param_type')
        emp_appraisal.status = "Manager Appraisal In Progress"
        if param_type != "D" and (parameters is None or not isinstance(parameters, list)):
            raise ValueError("please send list of parameters")
        if param_type == "A":
            partabc_list = []

            parta = PartA_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
            if parta is None:
                raise ValueError("Part A self appraisal score not found")
            total_score = 0
            for eparam in parameters:
                emp_param_obj = EmployeeParameter.objects.filter(parameter__id=eparam["parameter_id"],
                                                                 emp_appraisal=emp_appraisal).last()
                emp_param_obj.mgr_rating = float(eparam["mgr_rating"])
                emp_param_obj.mgr_comment = eparam["mgr_comment"]
                total_score += round((float(eparam["mgr_rating"]) * int(emp_param_obj.score)) / 100, 2)
                partabc_list.append(emp_param_obj)
            if len(partabc_list) > 0:
                parta.mgr_special_comment = request.data.get("mgr_special_comment")
                parta.mgr_score = total_score
                EmployeeParameter.objects.bulk_update(partabc_list, ["mgr_rating", "mgr_comment", "updated_at"])
                emp_appraisal.status = "Manager Appraisal In Progress"
                parta.save()
        elif param_type == "B":
            add_partbc_self_appraisal_rating(parameters, PartB_Appraisee, emp_appraisal, "B", mgr_appraisal=True,
                                             created_by=usr)

        elif param_type == "C":
            add_partbc_self_appraisal_rating(parameters, PartC_Appraisee, emp_appraisal, "C", mgr_appraisal=True,
                                             created_by=usr)
        elif param_type == "D":
            add_partD_parameters(request, emp_appraisal, emp)

        parta = PartA_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        partb = PartB_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        partc = PartC_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()
        partd = PartD_Appraisee.objects.filter(emp_appraisal=emp_appraisal).first()

        if parta and partb and partc and partd:
            emp_appraisal.mgr_score = round(
                parta.mgr_score * 70 / 100 + partb.mgr_score * 20 / 100 + partc.mgr_score * 10 / 100, 2)
            if emp_appraisal.emp_score is None:
                emp_appraisal.emp_score = round(
                    parta.emp_score * 70 / 100 + partb.emp_score * 20 / 100 + partc.emp_score * 10 / 100,
                    2)
            rm1 = emp.team.manager
            rm2 = rm1.team.manager
            emp_appraisal.mgr_appraisal_date = tz.localize(datetime.now())
            emp_appraisal.reviewer_emp_id = rm1.emp_id
            emp_appraisal.reviewer_name = rm1.full_name
            emp_appraisal.reviewer_designation = rm1.designation.name
            emp_appraisal.supervisor_emp_id = rm2.emp_id
            emp_appraisal.supervisor_name = rm2.full_name
            emp_appraisal.supervisor_designation = rm2.designation.name
            emp_appraisal.status = "Manager Appraisal Completed"
        emp_appraisal.save()

        return HttpResponse(json.dumps({"message": f"manager appraisal for Part {param_type} is done successfully"}))
    except Exception as e:
        logger.info("exception at get_self_appraisal_status {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllAppraisal(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllEmpAppraisalSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            url_name = request.resolver_match.view_name
            mapping_column_names = {"emp_name": "employee__full_name", "emp_id": "employee__emp_id",
                                    "process": "employee__team__base_team__name"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=mapping_column_names)
            app_date = get_appraisal_eligible_date()
            if not url_name.endswith("mgmt"):
                my_team = get_team_ids(request.user)
                if my_team is None:
                    raise ValueError("There is no team under you")
                search_query &= Q(employee__team__id__in=my_team)
            exclude_emps = get_exclude_appraisal_emps()
            search_query &= ~Q(employee__emp_id__in=exclude_emps)
            self.queryset = EmpAppraisal.objects.filter(employee__date_of_joining__lte=app_date,
                                                        employee__status="Active", **filter_by).filter(
                search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info("exception at GetAllAppraisal {0}".format(traceback.format_exc(5)))
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllEligibleAppraisalEmployeesList(GenericAPIView, ListModelMixin):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllEligibleAppraisalListSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        try:
            url_name = request.resolver_match.view_name
            mapping_column_names = {"emp_name": "full_name",
                                    "process": "team__base_team__name",
                                    "designation": "designation__name"}
            order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET,
                                                                                 fields_look_up=mapping_column_names)
            app_date = get_appraisal_eligible_date()
            if not url_name.endswith("mgmt"):
                my_team = get_team_ids(request.user)
                if my_team is None:
                    raise ValueError("There are no teams under you")
                search_query &= Q(team__id__in=my_team)

            exclude_emps = get_exclude_appraisal_emps()
            search_query &= ~Q(emp_id__in=exclude_emps)
            self.queryset = Profile.objects.filter(date_of_joining__lte=app_date, status="Active", **filter_by).filter(
                search_query).order_by(*order_by_cols)
            return self.list(request, *args, **kwargs)
        except Exception as e:
            logger.info("exception at GetAllEligibleAppraisalEmployeesList {0}".format(traceback.format_exc(5)))
            return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_emp_parameters(request, appraisal_id):
    try:
        year = datetime.now().year

        if appraisal_id != "-1":
            appraisal = get_appraisal_obj(appraisal_id, check_only_obj_existence=True)
            emp = appraisal.employee
        else:
            emp = request.user
            appraisal = get_appraisal_obj(None, emp=emp)
        emp_params = EmployeeParameter.objects.filter(emp_appraisal=appraisal)
        rm1 = emp.team.manager
        rm2 = rm1.team.manager
        parameters = {"parta": {"parameters": []}, "partb": [], "partc": [], "partd": {},
                      "reviewer_name": rm1.full_name, "reviewer_desi": rm1.designation.name,
                      "supervisor_name": rm2.full_name, "supervisor_desi": rm2.designation.name,
                      "emp_score": appraisal.emp_score, "mgr_score": appraisal.mgr_score,
                      "emp_name": emp.full_name, "emp_id": emp.emp_id, "designation": emp.designation.name,
                      "doj": str(emp.date_of_joining)}
        for eparam in emp_params.filter(parameter__type="A"):
            parameters["parta"]["parameters"].append(
                ({"parameter_id": eparam.parameter.id, "parameter_name": eparam.parameter.name,
                  "score": eparam.score, "mgr_rating": eparam.mgr_rating, "mgr_comment": eparam.mgr_comment,
                  "emp_rating": eparam.emp_rating, "emp_comment": eparam.emp_comment}))
        for eparam in emp_params.filter(parameter__type="B"):
            parameters["partb"].append(
                ({"parameter_id": eparam.parameter.id, "parameter_name": eparam.parameter.name,
                  "mgr_rating": eparam.mgr_rating, "mgr_comment": eparam.mgr_comment,
                  "score": eparam.score, "emp_rating": eparam.emp_rating, "emp_comment": eparam.emp_comment}))
        for eparam in emp_params.filter(parameter__type="C"):
            parameters["partc"].append(
                ({"parameter_id": eparam.parameter.id, "parameter_name": eparam.parameter.name,
                  "mgr_rating": eparam.mgr_rating, "mgr_comment": eparam.mgr_comment,
                  "score": eparam.score, "emp_rating": eparam.emp_rating, "emp_comment": eparam.emp_comment}))
        partd_data = PartD_Appraisee.objects.filter(emp_appraisal=appraisal).last()
        if partd_data:
            parameters["partd"] = GetPartDAppraiseeSerializer(partd_data).data

        parta = PartA_Appraisee.objects.filter(emp_appraisal=appraisal).last()
        if parta:
            parameters["parta"]["mgr_special_comment"] = parta.mgr_special_comment
            parameters["parta"]["emp_special_comment"] = parta.emp_special_comment
        return HttpResponse(json.dumps(parameters))
    except Exception as e:
        logger.info("exception at get_all_emp_parameters {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def add_appraisee_partd(request):
    try:
        check_appraisal_last_date()
        emp = request.user
        emp_appraisal = get_appraisal_obj(None, emp=emp)
        if emp_appraisal.status == "Appraisal Completed":
            raise ValueError("Employee already completed partD")
        elif emp_appraisal.status != "Manager Appraisal Completed":
            raise ValueError(f"Employee status: {emp_appraisal.status}")

        partd = PartD_Appraisee.objects.filter(emp_appraisal=emp_appraisal).last()
        is_emp_agreed = parse_boolean_value(request.data.get("is_emp_agreed"))
        data = update_request(request.data, is_emp_agreed=is_emp_agreed)
        if partd is None:
            raise ValueError("PartD data does not exist")
        serializer = UpdatePartDAppraiseeSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        _ = serializer.update(partd, serializer.validated_data)
        emp_appraisal.status = "Appraisal Completed"
        emp_appraisal.agent_completed_date = tz.localize(datetime.now())
        emp_appraisal.save()

        return HttpResponse(json.dumps({"message": "PartD of the appraisee updated successfully"}))
    except Exception as e:
        logger.info("exception at add_appraisee_partd {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_appraisal_stats(request):
    try:
        teams = get_team_ids(request.user)
        if teams is None:
            raise ValueError("There are no teams under you")
        app_date = get_appraisal_eligible_date()
        exclude_emps = get_exclude_appraisal_emps()
        emp_appraisal = EmpAppraisal.objects.exclude(employee__emp_id__in=exclude_emps).filter(
            employee__team__id__in=teams, employee__status="Active", employee__date_of_joining__lte=app_date,
            year=timezone.now().year)
        profiles = Profile.objects.filter(team__id__in=teams, status="Active", date_of_joining__lte=app_date)
        appraisal_status = {"Total": profiles.count(),
                            "Parameters Added": emp_appraisal.count(),
                            "Self Appraisal Completed": emp_appraisal.filter(
                                Q(status__in=["Self Appraisal Completed", "Manager Appraisal In Progress"])).count(),
                            "Appraisal Completed": emp_appraisal.filter(
                                status__in=["Appraisal Completed", "Manager Appraisal Completed"]).count()}
        return HttpResponse(json.dumps({"result": appraisal_status}))
    except Exception as e:
        logger.info("exception at get_appraisal_stats {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_overall_appraisal_stats(request):
    try:
        app_date = get_appraisal_eligible_date()
        exclude_emps = get_exclude_appraisal_emps()

        emp_appraisal = EmpAppraisal.objects.exclude(employee__emp_id__in=exclude_emps).filter(
            employee__status="Active", employee__date_of_joining__lte=app_date, year=timezone.now().year)
        profiles = Profile.objects.exclude(emp_id__in=exclude_emps).filter(
            status="Active", date_of_joining__lte=app_date)
        appraisal_status = {"Total": profiles.count(),
                            "Parameters Added": emp_appraisal.count(),
                            "Appraisal Completed": emp_appraisal.filter(
                                status__in=["Appraisal Completed", "Manager Appraisal Completed"]).count(),
                            "Pending Mgr Appraisal": emp_appraisal.filter(
                                Q(status__in=["Self Appraisal Completed", "Manager Appraisal In Progress"])).count()
                            }
        return HttpResponse(json.dumps({"result": appraisal_status}))
    except Exception as e:
        logger.info("exception at get_overall_appraisal_stats {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_appraisal_report(request):
    try:
        app_date = get_appraisal_eligible_date()
        emp_appraisals = EmpAppraisal.objects.filter(employee__date_of_joining__lte=app_date,
                                                     status__in=["Appraisal Completed", "Manager Appraisal Completed"],
                                                     year=datetime.now().year)
        column_names = ["EID", "Name", "DOJ", "Status", "Department", "Designation", "Process", "Team", "Manager",
                        "LWD", "Final Score", "Self Appraisal Score", "PartA Mgr", "PartA Emp",
                        "PartB Mgr", "PartB Emp", "PartC Mgr", "PartC Emp"]
        appraisal_scores = []
        for emp_app in emp_appraisals:
            parta = PartA_Appraisee.objects.filter(emp_appraisal=emp_app).first()
            partb = PartB_Appraisee.objects.filter(emp_appraisal=emp_app).first()
            partc = PartC_Appraisee.objects.filter(emp_appraisal=emp_app).first()
            emp = emp_app.employee
            team = emp.team
            appraisal_scores.append(
                [emp.emp_id, emp.full_name, str(emp.date_of_joining), emp.status, emp.designation.department.name,
                 emp.designation.name, team.base_team.name, team.name, team.manager.full_name,
                 str(emp.last_working_day), emp_app.mgr_score, emp_app.emp_score, parta.mgr_score, parta.emp_score,
                 partb.mgr_score, partb.emp_score, partc.mgr_score, partc.emp_score])

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Appraisal Report.csv"'
        writer = csv.writer(response)

        writer.writerow(column_names)

        for row in appraisal_scores:
            writer.writerow(row)

        return response
    except Exception as e:
        logger.info("exception at get_appraisal_report {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
