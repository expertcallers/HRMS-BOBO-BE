import json
import math
import traceback
import logging
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated

from hrms import settings
from mapping.views import HasUrlPermission
from payroll.models import Salary
from tax.models import IT, HouseRentInfo, HouseRentAllowance, MedicalSec80D, HousePropertyIncomeLoss, HouseProperty, \
    IT80C, OtherChapVIADeductions
from tax.serializers import *
from utils.util_classes import CustomTokenAuthentication
from utils.utils import update_request, return_error_response, get_column_names, parse_boolean_value, \
    get_decrypted_value

logger = logging.getLogger(__name__)


# Create your views here.

@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def initiate_it_declaration(request):
    try:
        profile = request.user
        data = update_request(request.data, profile=profile.id)
        serializer = CreateITSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer, raise_exception=True)
        try:
            it = IT.objects.get(from_year=serializer.validated_data['from_year'], profile=profile,
                                to_year=serializer.validated_data['to_year'])
        except Exception as e:
            it = serializer.create(serializer.validated_data)
        it = GetITSerializer(it).data
        return HttpResponse(json.dumps({"it": it}))
    except Exception as e:
        logger.info("exception at initiate_it_declaration {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_month_list(from_year, to_year):
    l1 = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    l2 = ["Jan", "Feb", "Mar"]
    return [i + " " + from_year for i in l1] + [i + " " + to_year for i in l2]


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_it_declaration(request):
    try:
        profile = request.user
        from_year = request.data.get('from_year')  # TODO handle it properly
        to_year = request.data.get('to_year')  # TODO handle it properly
        salary = Salary.objects.filter(profile=profile).first()
        if salary is None:
            return HttpResponse(json.dumps({"message": "The employee onboard information is incomplete, contact HR"}))

        try:
            it = IT.objects.get(from_year=from_year, to_year=to_year, profile=profile)
        except Exception as e:
            logger.info(f"get_it_declaration get exception {str(e)} ")
            return HttpResponse(json.dumps({"it": None}))
        if it.acknowledged:
            return HttpResponse(
                json.dumps({f"message": f"IT Declaration for the financial year {from_year}-{to_year} is completed"}))
        it = GetITSerializer(it).data
        return HttpResponse(json.dumps({"it": it, "month_list": get_month_list(from_year, to_year)}))
    except Exception as e:
        logger.info("exception at get_it_declaration {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_it_instance(it_id):
    try:
        it = IT.objects.get(id=it_id)
    except Exception as e:
        raise ValueError(f"IT Record doesn't exist for id {it_id}")
    return it


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_update_80c(request, it_id):
    try:
        it = get_it_instance(it_id)
        data = request.data
        if it.it_80c is None:
            serializer = CreateIT80CSerializer(data=data)
        else:
            serializer = CreateIT80CSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["total_declared"] = sum(serializer.validated_data.values())
        if it.it_80c is None:
            serializer.validated_data["it"] = it
            it.it_80c = serializer.create(serializer.validated_data)
        else:
            serializer.update(it.it_80c, serializer.validated_data)
        it.save()
        it = GetITSerializer(it).data
        return HttpResponse(json.dumps({"it": it}))
    except Exception as e:
        logger.info("exception at create_80c {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_update_other_chap_vi_deductions(request, it_id):
    try:
        it = get_it_instance(it_id)
        data = request.data
        if it.other_chap_vi_deductions is None:
            serializer = CreateOtherChapVIADeductionsSerializer(data=data)
        else:
            serializer = CreateOtherChapVIADeductionsSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["total_declared"] = sum(serializer.validated_data.values())
        if it.other_chap_vi_deductions is None:
            serializer.validated_data["it"] = it
            it.other_chap_vi_deductions = serializer.create(serializer.validated_data)
        else:
            serializer.update(it.other_chap_vi_deductions, serializer.validated_data)
        it.save()
        it = GetITSerializer(it).data
        return HttpResponse(json.dumps({"it": it}))
    except Exception as e:
        logger.info("exception at create_update_other_chap_vi_deductions {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_update_house_rent_allowance(request, it_id):
    try:
        '''
        create/update house_rent_info
        '''
        it = get_it_instance(it_id)
        house_rent_allowance_data = request.data.get("house_rent_allowance", [])
        if not isinstance(house_rent_allowance_data, list):
            raise ValueError("Please provide list of house rent allowance data")
        objs_data = []
        total_annual_rent_amount = 0
        existing_house_objs = {}
        new_house_objs = []
        create = False
        month_list = get_month_list(it.from_year, it.to_year)
        existing_month_range = []
        # iterate through house_rent_obj_data and create new if it is new or update if id is present in the data
        for house in house_rent_allowance_data:
            hupdate = False
            if not isinstance(house, dict):
                raise ValueError("Invalid house format, must be key-value based")
            if 'id' not in house.keys():
                house_serializer = CreateHouseRentInfoSerializer(data=house)
            else:
                house_serializer = CreateHouseRentInfoSerializer(data=house, partial=True)
                hupdate = True
            if not house_serializer.is_valid():
                return return_error_response(house_serializer)
            if hupdate:
                try:
                    existing_house_objs[house['id']] = HouseRentInfo.objects.get(id=house['id'])
                    house_serializer.validated_data['id'] = house['id']
                except Exception as e:
                    raise ValueError("Invalid house id is provided")

            objs_data.append(house_serializer.validated_data)
            total_annual_rent_amount += house_serializer.validated_data["annual_rent_amount"]
            try:
                start_month_rng_no = month_list.index(house['start_date'])
                end_month_rng_no = month_list.index(house['end_date'])
            except Exception as e:
                raise ValueError(
                    f"Invalid month has been selected, start-month {house['start_date']}, end-month {house['end_date']}, "
                    f"accepted months are from Apr {it.from_year} - Mar {it.to_year}")
            if start_month_rng_no in existing_month_range or end_month_rng_no in existing_month_range:
                raise ValueError("From date overlaps with To date. Kindly select the appropriate date.")
            existing_month_range += range(start_month_rng_no, end_month_rng_no + 1)

        if it.house_rent_allowance is None:
            it.house_rent_allowance = HouseRentAllowance.objects.create(total_declared=total_annual_rent_amount, it=it)
            create = True
        else:
            it.house_rent_allowance.total_declared = total_annual_rent_amount
            it.house_rent_allowance.save()
        for HouseRentData in objs_data:
            if 'id' not in HouseRentData:
                HouseRentData['it'] = it
                HouseRentData['house_rent_allowance'] = it.house_rent_allowance
                new_house_objs.append(HouseRentInfo.objects.create(**HouseRentData))
            else:
                lobj = existing_house_objs[HouseRentData['id']]
                for key, val in HouseRentData.items():
                    setattr(lobj, key, val)
                lobj.save()

        if create:
            for house_rent in new_house_objs:
                it.house_rent_allowance.house_rent_info.add(house_rent)
        else:
            for existing_hobj in it.house_rent_allowance.house_rent_info.all():
                if existing_hobj.id not in existing_house_objs.keys():
                    existing_hobj.delete()
            for new_hobj in new_house_objs:
                it.house_rent_allowance.house_rent_info.add(new_hobj)

        it.save()
        it = GetITSerializer(it).data
        return HttpResponse(json.dumps({"it": it}))
    except Exception as e:
        logger.info("exception at create_house_rent_allowance {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_update_medical_sec_80d(request, it_id):
    try:
        it = get_it_instance(it_id)
        data = update_request(data=request.data, it=it_id)
        if it.medical_sec_80d is None:
            serializer = CreateMedicalSec80DSerializer(data=data)
        else:
            serializer = CreateMedicalSec80DSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["total_declared"] = sum(
            serializer.validated_data[i] for i in serializer.validated_data.keys() if
            i not in ["medical_ins_pre_age", "medical_ins_pre_dep_parents_age"])

        if it.medical_sec_80d is None:
            serializer.validated_data["it"] = it
            it.medical_sec_80d = serializer.create(serializer.validated_data)
        else:
            serializer.update(it.medical_sec_80d, serializer.validated_data)
        it.save()
        it = GetITSerializer(it).data
        return HttpResponse(json.dumps({"it": it}))
    except Exception as e:
        logger.info("exception at create_update_medical_sec_80d {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_update_house_property_income_loss(request, it_id):
    try:
        it = get_it_instance(it_id)
        house_property_data = request.data.get("house_property", [])
        valid_house_data = []
        existing_house_data = {}
        newly_added_house_obj = []
        if type(house_property_data) != list:
            raise ValueError("Please provide list of house property data")

        for house_property in house_property_data:
            update = False
            if 'id' not in house_property:
                house_serializer = CreateHousePropertySerializer(data=house_property)
            else:
                house_serializer = CreateHousePropertySerializer(data=house_property, partial=True)
                update = True
            if not house_serializer.is_valid():
                raise return_error_response(house_serializer, raise_exception=True)
            if update:
                existing_house_data[house_property['id']] = HouseProperty.objects.filter(
                    id=house_property['id']).first()
                if existing_house_data[house_property['id']] is None:
                    return ValueError("Invalid house-property id is provided")
                house_serializer.validated_data['id'] = house_property['id']
            valid_house_data.append(house_serializer.validated_data)
        if it.house_property_inc_loss is None:
            serializer = CreateHousePropertyIncomeLossSerializer(data=request.data)
        else:
            serializer = CreateHousePropertyIncomeLossSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        create_house_property = False
        if it.house_property_inc_loss is None:
            create_house_property = True
            serializer.validated_data["it"] = it
            it.house_property_inc_loss = serializer.create(serializer.validated_data)
        else:
            serializer.update(it.house_property_inc_loss, serializer.validated_data)
        for house in valid_house_data:
            if 'id' not in house.keys():
                house['house_property_inc_loss'] = it.house_property_inc_loss
                house['it'] = it
                newly_added_house_obj.append(HouseProperty.objects.create(**house))
            else:
                for key, value in house.items():
                    setattr(existing_house_data[house['id']], key, value)
                existing_house_data[house['id']].save()

        if not create_house_property:
            remove_objs = []
            for ex_hobj in it.house_property_inc_loss.house_property.all():
                if ex_hobj.id not in existing_house_data.keys():
                    remove_objs.append(ex_hobj)
            for rem_obj in remove_objs:
                it.house_property_inc_loss.house_property.remove(rem_obj)
                rem_obj.delete()
        for new_hobj in newly_added_house_obj:
            it.house_property_inc_loss.house_property.add(new_hobj)

        it.save()
        it = GetITSerializer(it).data
        return HttpResponse(json.dumps({"it": it}))
    except Exception as e:
        logger.info("exception at create_house_property_income_loss {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_update_other_income(request, it_id):
    try:
        it = get_it_instance(it_id)
        if it.other_inc is None:
            serializer = CreateOtherIncomeSerializer(data=request.data)
        else:
            serializer = CreateOtherIncomeSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return return_error_response(serializer)
        oth_inc_1 = serializer.validated_data.get('oth_inc_1_declared_amount', 0)
        oth_inc_2 = serializer.validated_data.get('oth_inc_2_declared_amount', 0)
        serializer.validated_data["total_declared"] = oth_inc_1 + oth_inc_2
        if it.other_inc is None:
            serializer.validated_data["it"] = it
            it.other_inc = serializer.create(serializer.validated_data)
        else:
            serializer.update(it.other_inc, serializer.validated_data)
        it.save()
        it = GetITSerializer(it).data
        return HttpResponse(json.dumps({"it": it}))
    except Exception as e:
        logger.info("exception at create_update_other_income {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def remove_col_names(column_names, rem_cols=[]):
    for col in ["total_declared", "created_at", "updated_at", "id"] + rem_cols:
        if col in column_names:
            column_names.remove(col)
    return column_names


def calculate_80c(it):
    column_names, related_cols = get_column_names(IT80C)
    column_names = remove_col_names(column_names)
    max_it_80c = settings.INCOME_TAX_MAX_VALUES.get('it_80c')
    it_80c_calc_values = {}
    cumulative_total = 0
    cumulative_total_new_reg = 0
    # logger.info(f"column_names {column_names}")
    for col in column_names:
        value = getattr(it.it_80c, col)
        old_regime = 0
        new_regime = 'NA'
        if value > 0:
            if cumulative_total < max_it_80c:
                # logger.info(
                #     f"col {col} cumulative_total {cumulative_total}, old_reg {old_regime}")
                if value > max_it_80c:
                    if cumulative_total == 0:
                        old_regime = max_it_80c
                        cumulative_total = max_it_80c
                    else:
                        old_regime = max_it_80c - cumulative_total
                        cumulative_total = max_it_80c
                else:
                    current_diff = max_it_80c - cumulative_total
                    if value >= current_diff:
                        old_regime = current_diff
                        cumulative_total = max_it_80c
                    else:
                        old_regime = value
                        cumulative_total += value
                        # logger.info(
                        #     f"cumulative_total {cumulative_total}, current_diff {current_diff}, old_reg {old_regime}")
            if new_regime != "NA":
                cumulative_total_new_reg += new_regime
            it_80c_calc_values[col] = {"declared": value, "old_regime": old_regime, "new_regime": new_regime}
    return it_80c_calc_values, cumulative_total, cumulative_total_new_reg


def calc_old_regime_value(value, max_value):
    if value > max_value:
        old_regime = max_value
    else:
        old_regime = value
    return old_regime


def calculate_chapter_6(it):
    column_names, related_cols = get_column_names(OtherChapVIADeductions)
    column_names = remove_col_names(column_names)
    chap_6_vals = {}
    cumulative_total = 0
    date_value = datetime.today().date() - it.profile.dob
    year = int(date_value.days / 365)
    is_senior = year > 60
    cumulative_total_new_reg = 0
    for col in column_names:
        value = getattr(it.other_chap_vi_deductions, col)
        new_regime = 'NA'
        old_regime = 0
        max_value = settings.INCOME_TAX_MAX_VALUES.get(col)
        if value > 0:

            if col == "super_exem_10_13":
                new_regime = value
                old_regime = value
            elif col == "add_int_80eea_house_loan_bor_1apr2019":
                # 80EEA - Additional Interest on Housing loan borrowed as on 1st Apr 2019
                pass
            elif col == "int_dep_sav_acc_fd_po_co_so_sen_cit_80ttb":
                # 80TTB - Interest on Deposits in Savings Account, FDs, Post Office And Cooperative Society for Senior Citizen
                if is_senior:
                    old_regime = calc_old_regime_value(value, max_value)
            elif col == "med_treat_ins_hand_dep_80dd":
                # 80DD - Medical Treatment / Insurance of handicapped Dependant (self)
                pass
            elif col == "med_treat_spec_dis_80ddb":
                # 80DDB - Medical Treatment ( Specified Disease only )(self)
                pass
            else:
                old_regime = calc_old_regime_value(value, max_value)
            cumulative_total += old_regime
            if new_regime != "NA":
                cumulative_total_new_reg += new_regime

            chap_6_vals[col] = {"declared": value, "old_regime": old_regime, "new_regime": new_regime}
    return chap_6_vals, cumulative_total, cumulative_total_new_reg


def calculate_other_inc(it):
    other_inc_val = {}
    columns = ["oth_inc_1_declared_amount", "oth_inc_2_declared_amount"]
    cumulative = 0
    for col in columns:
        value = getattr(it.other_inc, col)
        if value > 0:
            cumulative += value
            other_inc_val[col] = {"declared": value, "old_regime": value, "new_regime": value}
    return other_inc_val, cumulative


def calculate_medical_80d(it):
    column_names, related_cols = get_column_names(MedicalSec80D)
    column_names = remove_col_names(column_names, ["medical_ins_pre_age", "medical_ins_pre_dep_parents_age"])
    medic_80d_vals = {}
    cumulative_total = 0
    cumulative_total_new_reg = 0
    for col in column_names:
        value = getattr(it.medical_sec_80d, col)
        new_regime = 'NA'
        old_regime = 0
        max_value = settings.INCOME_TAX_MAX_VALUES.get(col)
        if col == "prev_hlth_checkup_dependant_parents":
            pass
        elif col == "medical_ins_pre_dep_parents_amount":
            pass
        elif col == "prev_hlth_checkup":
            pass
        else:
            old_regime = calc_old_regime_value(value, max_value)
        cumulative_total += old_regime
        if new_regime != "NA":
            cumulative_total_new_reg += new_regime
        medic_80d_vals[col] = {"declared": value, "old_regime": old_regime, "new_regime": new_regime}
    return medic_80d_vals, cumulative_total, cumulative_total_new_reg


def get_old_tax(salary):
    # Lies under tax rebate limit
    if salary < 250000:
        return 0
    elif salary < 500000:
        return (salary - 250000) * 0.05
    elif salary < 1000000:
        return (salary - 500000) * 0.2 + 12500
    elif salary > 1000000:
        return (salary - 1000000) * 0.3 + 112500


def get_new_tax(salary):
    # lies under tax rebate limit
    if salary < 300000:
        return 0
    elif salary < 600000:
        return (salary - 300000) * 0.05
    elif salary < 900000:
        return (salary - 600000) * 0.1 + 15000
    elif salary < 1200000:
        return (salary - 900000) * 0.15 + 45000
    elif salary < 1500000:
        return (salary - 1200000) * 0.20 + 90000
    elif salary > 1500000:
        return (salary - 1500000) * 0.3 + 150000


def calculate_hra(it):
    # TODO
    onboard = it.profile.onboard
    one_year_hra = onboard.hra * 12
    rent_minus_ten_percent_basic_da = it.house_rent_allowance.total_declared - (onboard.basic * 0.1)
    if rent_minus_ten_percent_basic_da < 0:
        rent_minus_ten_percent_basic_da = 0
    forty_percent_basic_da = onboard.basic * 0.4
    min_value_list = [one_year_hra, forty_percent_basic_da, rent_minus_ten_percent_basic_da]
    return min(min_value_list)


def get_salary_from_it(it):
    salary = Salary.objects.filter(profile=it.profile).first()
    return salary


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def calculate_tax(request, it_id):
    try:
        old_reg_tax_inc = 0
        new_reg_tax_inc = 0
        old_regime_deductions = 0
        new_regime_deductions = 0

        out_response = {}
        it = get_it_instance(it_id)
        salary = get_salary_from_it(it)
        if salary is None:
            raise ValueError("Employee onboard information is incomplete, contact HR")
        if it.it_80c:
            section_80c, c_total, c_total_new = calculate_80c(it)
            if len(section_80c.keys()) > 0:
                out_response["it_80c"] = section_80c
                old_regime_deductions += c_total

        if it.other_chap_vi_deductions:
            other_vi_ded, c_total, c_total_new = calculate_chapter_6(it)
            if len(other_vi_ded.keys()) > 0:
                out_response["other_chap_vi_deductions"] = other_vi_ded
                old_regime_deductions += c_total
                new_regime_deductions += c_total_new
                logger.info(f"new_regime_deductions {new_regime_deductions}")
        if it.medical_sec_80d:
            medic_80d_val, c_total, c_total_new = calculate_medical_80d(it)
            if len(medic_80d_val.keys()) > 0:
                out_response["medical_sec_80d"] = medic_80d_val
                old_regime_deductions += c_total

        if it.other_inc:
            other_inc_val, total = calculate_other_inc(it)
            if len(other_inc_val.keys()) > 0:
                out_response["other_inc"] = other_inc_val
                new_reg_tax_inc += total
                old_reg_tax_inc += total
        if it.house_rent_allowance:
            if it.house_rent_allowance.total_declared > 0:
                hra_deductions = calculate_hra(it)
                logger.info(f"hra_deductions {hra_deductions}")
                out_response["house_rent_allowance"] = {"declared": it.house_rent_allowance.total_declared,
                                                        "old_regime": hra_deductions, "new_regime": "NA"}
                old_regime_deductions += hra_deductions

        if it.house_property_inc_loss:
            if abs(it.house_property_inc_loss.total_exemption) > 0:
                old_reg_tax_inc += it.house_property_inc_loss.total_exemption
                new_reg_tax_inc += it.house_property_inc_loss.tot_inc_loss_frm_let_out_property
                out_response["house_property_inc_loss"] = {"declared": it.house_property_inc_loss.total_exemption,
                                                           "old_regime": it.house_property_inc_loss.total_exemption,
                                                           "new_regime": it.house_property_inc_loss.tot_inc_loss_frm_let_out_property}
        salary = Salary.objects.filter(profile=it.profile).first()

        old_reg_tax_inc = old_reg_tax_inc - old_regime_deductions - float(get_decrypted_value(salary.pt)) * 12 - 50000
        new_reg_tax_inc = new_reg_tax_inc - new_regime_deductions - 50000
        old_reg_tax_inc = old_reg_tax_inc
        ctc = float(get_decrypted_value(salary.ctc))
        old_reg_tax_inc += ctc
        new_reg_tax_inc += ctc
        logger.info(f"ctc {ctc}, old_reg_tax_inc {old_reg_tax_inc} new_reg_tax_inc {new_reg_tax_inc}")
        out_response["old_reg_net_tax"] = get_old_tax(old_reg_tax_inc) if old_reg_tax_inc > 500000 else 0

        out_response["new_reg_net_tax"] = get_new_tax(new_reg_tax_inc) if new_reg_tax_inc > 700000 else 0

        # Add: Education +Health Cess @4%
        out_response["new_reg_net_tax"] += round(out_response["new_reg_net_tax"] * 0.04, 0)
        out_response["old_reg_net_tax"] += round(out_response["old_reg_net_tax"] * 0.04, 0)

        out_response["old_reg_tax_inc"] = old_reg_tax_inc
        out_response["new_reg_tax_inc"] = new_reg_tax_inc
        it.new_reg_net_tax = out_response["new_reg_net_tax"]
        it.old_reg_net_tax = out_response["old_reg_net_tax"]
        it.new_reg_tax_inc = out_response["new_reg_tax_inc"]
        it.old_reg_tax_inc = out_response["old_reg_tax_inc"]
        it.save()
        return HttpResponse(json.dumps(out_response))
    except Exception as e:
        logger.info("exception at create_update_other_income {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_tax_calc(request, it_id):
    try:
        it = get_it_instance(it_id)
        it_calc = GetITCalcSerializer(it).data
        return HttpResponse(json.dumps(it_calc))
    except Exception as e:
        logger.info("exception at get_tax_calc {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def select_regime(request, it_id):
    try:
        it = get_it_instance(it_id)
        acknowledged = parse_boolean_value(request.data.get("acknowledged"))
        data = update_request(request.data, acknowledged=acknowledged)
        serializer = SelectRegimeSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.update(it, serializer.validated_data)
        return HttpResponse(json.dumps({"message": "IT Declaration is complete"}))
    except Exception as e:
        logger.info("exception at get_tax_calc {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
