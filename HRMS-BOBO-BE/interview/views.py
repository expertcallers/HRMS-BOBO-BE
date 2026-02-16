import base64
import csv
import hashlib
import json
import os
import time
import re
import openai
import traceback
import uuid
from copy import deepcopy
from random import random, choices
from smtplib import SMTPAuthenticationError

from django.core.files.storage import FileSystemStorage
from django.db import IntegrityError
from django.http import HttpResponse
from django.core.validators import validate_email
from rest_framework import status, mixins, authentication, permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
import re
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db.models import Count, Q

import logging

from erf.models import ERF
from hrms import settings
from interview.models import Candidate, Interviewer, CandidateOTPTest, FieldsOfExperience, Application, \
    ToAppliedCandidateStatus, InternPosition, InternQuestion, InternAnswer, InternApplication
from interview.serializers import GetCandidateSerializer, GetAllCandidateSerializer, CreateCandidateSerializer, \
    CreateInterviewerSerializer, GetAllInterviewerSerializer, UpdateCandidateSerializer, UpdateInterviewSerializer, \
    CandidateOTPTestSerializer, AddFieldsOfExpSerializer, CreateApplicationSerializer, form_document_url, \
    DocumentSerializer, UpdateApplicationSerializer, PositionSerializer, QuestionSerializer, \
    InternApplicationSerializer, AnswerSerilizer
from interview_test.models import TestSection, CandidateQASection
from mapping.models import Department, EmployeeReferral, Profile, MiscellaneousMiniFields
from mapping.views import HasUrlPermission
from interview.models import Document
from onboarding.models import OfferAppointmentLetter, Onboard
from transport.serializers import CabAddressDetailUpdateSerializer
from utils.util_classes import CustomTokenAuthentication
from utils.utils import unhash_value, return_error_response, hash_value, update_request, document_response, hash_file, \
    get_sort_and_filter_by_cols, validate_files, validate_input_date, get_formatted_name, get_emp_by_emp_id, \
    create_candidate_test_section, get_candidate_interview_timing, is_management, get_full_name, tz, \
    get_careers_email_message, update_email, validate_model_field, check_for_integrity_error, validate_aadhaar_no, \
    valid_email_and_aadhaar, send_email_message, verify_candidate_email_otp_info, format_text_answer, \
    evaluate_essay_by_chat_gpt_in_json_format, get_gpt, validate_answers

logger = logging.getLogger(__name__)


def return_candidate_response(candidate):
    cur_app = candidate.current_application
    applied_for = cur_app.job_position if cur_app else ""
    return Response(
        {"job_position": applied_for, "status": candidate.status, 'id': hash_value(candidate.id, 'cd'),
         'first_name': candidate.first_name, "middle_name": candidate.middle_name, "last_name": candidate.last_name,
         'email': candidate.email})


def update_or_create_file(field, file, candidate, is_filehash=False, user=None):
    emp_id = user.emp_id if user else None
    name = get_formatted_name(user) if user else None
    if is_filehash:
        file_hash_val = hash_file(file)
        document = Document.objects.filter(filehash=file_hash_val, field=field, candidate_id=candidate.id)
        if document.count() > 0:
            return None
        document = Document(filehash=file_hash_val, field=field, candidate_id=candidate.id,
                            file=file, uploaded_by_emp_id=emp_id, uploaded_by_name=name,
                            file_name=file.name)
        return document

    try:
        document = Document.objects.get(field=field, candidate_id=candidate.id)
        document.file.delete(save=False)
        document.uploaded_by_name = name
        document.uploaded_by_emp_id = emp_id
        document.file = file
        document.file_name = file.name
        document.save()
    except Exception as e:
        document = Document.objects.create(field=field, candidate_id=candidate.id,
                                           file=file, uploaded_by_name=name, uploaded_by_emp_id=emp_id,
                                           file_name=file.name)
    return document


@api_view(['POST'])
def get_candidate_status(request):
    try:
        email = request.data.get('email') or None
        try:
            validate_email(email)
        except Exception as e:
            raise ValueError("Please provide valid email address")
        mobile = request.data.get("mobile")
        if mobile is None or mobile == "" or len(mobile) != 10 or not str(mobile).isdecimal():
            raise ValueError("Please enter a valid mobile number")
        aadhaar_no = request.data.get("aadhaar_no")
        if aadhaar_no is None or aadhaar_no == "" or len(aadhaar_no) != 12 or not str(aadhaar_no).isdecimal():
            raise ValueError("Please enter a valid aadhaar-no")

        candidate = Candidate.objects.filter(aadhaar_no=aadhaar_no).last()
        candidate_email = Candidate.objects.filter(email=email).last()
        candidate_mobile = Candidate.objects.filter(mobile=mobile).last()
        if candidate:
            if candidate.email != email:
                raise ValueError("Existing aadhaar-number with given email is not matching")
            if candidate.mobile != mobile:
                raise ValueError("Existing aadhaar-number with given mobile-number is not matching")
            # cur_app = candidate.current_application
            # candidate = GetCandidateSerializer(candidate).data
            # candidate["job_position"] = cur_app.job_position if cur_app else ""
            return HttpResponse(json.dumps({"request_for_otp": True}))

        else:
            if candidate_email:
                raise ValueError("Someone with this email already registered under a different aadhaar-number")
            if candidate_mobile:
                raise ValueError("Someone with this mobile number already registered under a different aadhaar-number")
            return HttpResponse(json.dumps({"request_for_otp": False}))
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    # return return_candidate_response(candidate)


@api_view(['POST'])
def get_candidate_status_otp(request):
    try:
        email = request.data.get('email') or None
        try:
            validate_email(email)
        except Exception as e:
            raise ValueError("Please provide valid email address")
        candidate = Candidate.objects.filter(email=email).last()
        req_otp = False
        if candidate:
            req_otp = True
        return HttpResponse(json.dumps({"req_otp": req_otp}))
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def get_candidate_info_by_id(cd_id):
    if cd_id is None or str(cd_id).strip() == "":
        raise ValueError('please provide the valid id')
    id = unhash_value(cd_id, 'cd')
    if not str(id).isnumeric() or id is None:
        raise ValueError('{0} is invalid, please provide the valid id'.format(cd_id))
    try:
        candidate = Candidate.objects.get(id=id)
    except Exception as e:
        raise ValueError('Candidate record not found')
    return candidate


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_candidate(request, id):
    try:
        candidate = get_candidate_info_by_id(id)
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
    usr = request.user
    ta_status = ["Not Applied", 'Applied', 'Selected For Next Round', "Selected for Final TA Round"]
    if candidate.status in ta_status and usr.designation.department.dept_id == "ta":
        is_editable = True
    elif candidate.status not in ta_status and usr.designation.department.dept_id == "hr":
        is_editable = True
    else:
        is_editable = False
    candidate = GetCandidateSerializer(candidate).data
    return HttpResponse(json.dumps({'candidate': candidate, 'is_editable': is_editable}))


def get_time_by_duration(val):
    val_ = datetime.now() - timedelta(minutes=val)
    return val_


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_count_by_waiting_duration(request):
    out = {}
    candidate = Candidate.objects.filter(~Q(status__in=["Rejected", "Attrition", "Bench", "NCNS"])).exclude(
        is_employee=True)
    out["below_30"] = candidate.filter(last_interview_at__gte=get_time_by_duration(30),
                                       last_interview_at__lte=get_time_by_duration(0)).count()
    out["btw_30_60"] = candidate.filter(last_interview_at__lte=get_time_by_duration(30),
                                        last_interview_at__gte=get_time_by_duration(60)).count()
    out["above_60"] = candidate.filter(last_interview_at__lte=get_time_by_duration(60)).count()
    return HttpResponse(json.dumps({"waiting_count": out}))


class GetAllFeedbackHistory(mixins.ListModelMixin,
                            GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetAllInterviewerSerializer
    model = serializer_class.Meta.model

    def get(self, request, cd_id, *args, **kwargs):
        candidate_id = unhash_value(cd_id, 'cd')
        fields_look_up = {"to_department": "to_department__name", "from_department": "from_department__name",
                          "to_person_id": "to_person__emp_id", "to_person_name": "to_person__full_name",
                          "application": "application__id", "job_position": "application__job_position",
                          "interviewer_emp_id": "interview_emp__emp_id", "interviewer_name": "interview_emp__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)

        self.queryset = Interviewer.objects.filter(candidate_id=candidate_id).exclude(current_round=-1).filter(
            **filter_by).filter(search_query).order_by(*order_by_cols)

        return self.list(request, *args, **kwargs)


get_all_candidate_fields_lookup = {"job_position": "current_application__job_position",
                                   "position_applied": "current_application__position_applied__designation__name",
                                   "to_department": "current_application__to_department__name",
                                   "interviewer_emp_id": "current_application__interviewer__emp_id",
                                   "interviewer_name": "current_application__interviewer__full_name",
                                   "branch": "current_application__branch",
                                   "process_name": "current_application__position_applied__process__name",
                                   "erf_id": "current_application__position_applied__id",
                                   "transport_admin_app_rej_by_name": "transport_admin_app_rej_by__full_name",
                                   "transport_admin_app_rej_by_emp_id": "transport_admin_app_rej_by__emp_id"}


class GetAllCandidateInfo(mixins.ListModelMixin,
                          GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllCandidateSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        profile = request.user
        fields_look_up = get_all_candidate_fields_lookup
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)

        if profile.designation.department.dept_id in ["ta", "hr", "cc"] or is_management(profile):
            self.queryset = Candidate.objects.filter(current_application__isnull=False).filter(**filter_by).filter(
                search_query).order_by(*order_by_cols)
        elif profile.interview:
            self.queryset = Candidate.objects.filter(Q(
                current_application__all_interview_persons=profile, current_application__isnull=False)).filter(
                **filter_by).filter(search_query).order_by(*order_by_cols)
        else:
            self.queryset = []

        return self.list(request, *args, **kwargs)


class GetAllTransportApprovalCandidateInfo(mixins.ListModelMixin,
                                           GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllCandidateSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        fields_look_up = get_all_candidate_fields_lookup
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)

        self.queryset = Candidate.objects.filter(is_inactive=False, is_transport_required=True,
                                                 status="Selected For Onboarding").filter(
            **filter_by).filter(search_query).order_by(*order_by_cols)
        logger.info(f"self.queryset {self.queryset}")

        return self.list(request, *args, **kwargs)


# HRMS-5
@api_view(["POST"])
def send_email_otp(request):
    try:
        email = request.data.get('email').lower() if request.data.get('email') else None
        if email is None:
            raise ValueError("Email is Required")
        if settings.DEBUG and re.search(settings.DEV_EMAIL_OTP_PATTERN, email):
            hash_val = '123456'
        else:
            hash_val = str(hashlib.shake_256((email + str(uuid.uuid4())).encode("utf-8")).hexdigest(3)).upper()

        data = {'verify_otp': hash_val,
                'email': email}
        serializer = CandidateOTPTestSerializer(data=data)
        if not serializer.is_valid():
            return_error_response(serializer, raise_exception=True)
        logger.info("came to send email")
        if not (settings.DEBUG and re.search(settings.DEV_EMAIL_OTP_PATTERN, email)):
            logger.info("sending email...")
            subject = "Otp to register/update candidate form"
            email_template = "{0} is the otp generated by ECPL for candidate update/registration".format(hash_val)
            email_msg = get_careers_email_message(subject, email_template, to=[email], reply_to=[])
            send_email_message(email_msg)

        cnd_otp_obj, created = CandidateOTPTest.objects.update_or_create(email=email,
                                                                         defaults=data)
    except Exception as e:
        logger.info("exception at send_email_otp {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)

    logger.info("otp {0} created for email {1}".format(hash_val, email))
    return HttpResponse(json.dumps({"message": "Otp is sent check email"}))


@api_view(["POST"])
def verify_candidate_email_otp(request):
    try:
        otp, email, cand_otp_obj = verify_candidate_email_otp_info(request)
        try:
            candidate = Candidate.objects.get(email=email)
        except Exception as e:
            raise ValueError("Candidate with this email does not exist")
        onboard = Onboard.objects.filter(candidate=candidate).first()
        candidate = GetCandidateSerializer(candidate).data
        from onboarding.serializer import GetOnboardSerializer
        candidate["onboard"] = GetOnboardSerializer(onboard).data if onboard else None
        return HttpResponse(
            json.dumps({'message': "user can edit the form", 'candidate': candidate}))
    except Exception as e:
        logger.info(f"exception at verify_candidate_email_otp {traceback.format_exc(5)}")
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def update_candidate_files(request, candidate):
    resume = request.FILES.get('rsume') or None
    if resume:
        candidate.resume_id = update_or_create_file('resume', resume, candidate).id
    rel_letter = request.FILES.get('relieving') or None
    if rel_letter:
        candidate.relieving_letter_id = update_or_create_file('relieving_letter', rel_letter, candidate).id
    candidate.save()
    return candidate


def handle_update_candidate(request, cd_id, admin=False):
    email = request.data.get("email")
    if email is None or str(email) == "":
        raise ValueError("Email is Required")
    aadhaar_no = request.data.get("aadhaar_no")
    if aadhaar_no is None or str(aadhaar_no).strip() == "":
        raise ValueError("aadhaar number is required")
    candidate = get_candidate_info_by_id(cd_id)
    if candidate.status == "Active" and not admin:
        raise ValueError("You are already an active employee, changes are not accepted please login to the HRMS")
    data = update_request(request.data)
    serializer_class = UpdateCandidateSerializer(data=data, partial=True)
    if not serializer_class.is_valid():
        return_error_response(serializer_class, raise_exception=True)
    validate_files(request.FILES)
    candidate = valid_email_and_aadhaar(email, aadhaar_no, candidate)
    serializer_class.validated_data['total_work_exp'] = get_computed_tot_work_exp(serializer_class)
    serializer_class.update(candidate, serializer_class.validated_data)
    onboard = Onboard.objects.filter(candidate=candidate).last()
    if onboard:
        onboard.aadhaar_no = aadhaar_no
        onboard.dob = candidate.dob
        onboard.save()
    if candidate.is_transport_required and candidate.transport_approval_status == "NA" and candidate.status not in [
        "Onboard", "Active"]:
        candidate.transport_approval_status = "Pending"
    candidate.full_name = get_formatted_name(candidate)
    candidate.save()
    candidate = update_candidate_files(request, candidate)
    candidate = GetCandidateSerializer(candidate).data
    return candidate


@api_view(["POST"])
def update_candidate_otp(request, cd_id):
    try:
        otp, email, cand_otp_obj = verify_candidate_email_otp_info(request)
        candidate = handle_update_candidate(request, cd_id)
        return HttpResponse(json.dumps(candidate))
    except Exception as e:
        logger.info("in the exception : {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def update_candidate(request, cd_id):
    try:
        candidate = handle_update_candidate(request, cd_id)
        return HttpResponse(json.dumps(candidate))
    except Exception as e:
        logger.info("in the exception : {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def update_employee_referral_if_emp_created(data):
    source_ref = data.get("source_ref")
    if data["source"] == "Referral":
        try:
            emp_ref = EmployeeReferral.objects.get(id=source_ref)
            emp_ref.status = "Interview"
            emp_ref.save()
        except Exception as e:
            raise ValueError("invalid source_ref is provided {0}".format(source_ref))


def verify_candidate_against_employee_referral_email(email, data):
    source = data.get('source')
    source_ref = data.get("source_ref")
    if source != "Referral":
        return
    try:
        emp_ref = EmployeeReferral.objects.get(id=source_ref)
    except Exception as e:
        raise ValueError("Invalid source reference {0} for referral".format(source_ref))
    if emp_ref.email != email:
        raise ValueError("Input email does not match with the referral-email")


def get_computed_tot_work_exp(serializer_class):
    prev_comp_exp = serializer_class.validated_data['prev_comp_exp']
    if prev_comp_exp == "" or prev_comp_exp is None:
        return 0
    return sum([int(i) for i in serializer_class.validated_data['prev_comp_exp'].split(",")])


def handle_create_candidate(request, email):
    data = request.data

    aadhaar_no = data.get('aadhaar_no')
    if aadhaar_no and len(data.get('aadhaar_no')) != 12:
        raise ValueError("Please provide valid aadhar number")
    resume = request.data.get('rsume')
    # if resume is None:
    #     raise ValueError("Please upload proper resume document")
    data = update_request(data, email=email)
    serializer_class = CreateCandidateSerializer(data=data)

    if not serializer_class.is_valid():
        return_error_response(serializer_class, raise_exception=True)
    serializer_class.validated_data['total_work_exp'] = get_computed_tot_work_exp(serializer_class)
    validate_files(request.FILES)
    if serializer_class.validated_data["is_transport_required"]:
        serializer_class.validated_data["transport_approval_status"] = "Pending"
    candidate = Candidate.objects.create(**serializer_class.validated_data)
    candidate = update_candidate_files(request, candidate)
    candidate = GetCandidateSerializer(candidate).data
    return candidate


@api_view(['POST'])
def create_candidate_otp(request):
    try:
        otp, email, cand_otp_obj = verify_candidate_email_otp_info(request)
        candidate = handle_create_candidate(request, email)
        return HttpResponse(json.dumps(candidate))
    except Exception as e:
        logger.info("in the exception : {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def handle_create_application(data, cd_id):
    candidate = get_candidate_info_by_id(cd_id)
    if candidate.status == "Active":
        raise ValueError("you cannot apply as you are an existing employee")
    if candidate.status not in ["Not Applied", "Rejected", "Attrition"]:
        raise ValueError("Your current application is under processing with status {0}".format(candidate.status))
    from_department = Department.objects.get(dept_id='sup')
    to_department = Department.objects.get(dept_id='ta')
    data = update_request(data=data, to_department=to_department.id, candidate=candidate.id)
    serializer = CreateApplicationSerializer(data=data)
    if not serializer.is_valid():
        return return_error_response(serializer)
    verify_candidate_against_employee_referral_email(candidate.email, data)
    update_employee_referral_if_emp_created(serializer.validated_data)
    application = serializer.create(serializer.validated_data)
    application.all_to_departments.add(to_department)
    candidate.last_interview_at = tz.localize(datetime.now())
    candidate.is_interview_completed = False
    candidate.current_application = application
    candidate.all_applications.add(application)
    candidate.status = "Applied"
    candidate.save()
    erf = application.position_applied
    total_rounds = 1
    if erf:
        total_rounds = erf.no_of_rounds

    _ = Interviewer.objects.create(application=application, candidate=candidate, status="Applied",
                                   feedback="System generated", to_department=to_department,
                                   from_department=from_department, result=True, is_dept_specific=True,
                                   total_rounds=total_rounds, current_round=-1)
    erf = application.position_applied
    if erf and erf.test.all().count() > 0:
        application.test = choices(erf.test.all())[0]
        application.save()
    return candidate


@api_view(["POST"])
def create_application_otp(request, cd_id):
    try:
        otp, email, cand_otp_obj = verify_candidate_email_otp_info(request)
        candidate = handle_create_application(request.data, cd_id)
        cand_otp_obj.delete()
        candidate = GetCandidateSerializer(candidate).data
        return HttpResponse(json.dumps({"candidate": candidate}))
    except Exception as e:
        logger.info("in the exception : {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


# @api_view(["POST"])
# def update_application(request, app_id):
#     try:
#         try:
#             application = Application.objects.get(id=app_id)
#         except Exception as e:
#             raise ValueError("Invalid Application id {0}".format(app_id))
#         serializer = CreateApplicationSerializer(data=request.data, partial=True)
#         if not serializer.is_valid():
#             return return_error_response(serializer)
#         update_employee_referral_if_emp_created(request.data)
#         serializer.update(application, serializer.validated_data)
#     except Exception as e:
#         logger.info("in the exception : {0}".format(traceback.format_exc(5)))
#         return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def raise_exception_if_to_department_does_not_belongs_to_current_user_or_if_not_previous_user(interviewer, profile):
    raise_exception = True
    logger.info(
        "interviewer.from_department={0}, profile_dept = {1} ".format(interviewer.from_department,
                                                                      profile.designation.department))
    logger.info("inter_emp {0}, profile_emp={1}".format(interviewer.interview_emp, profile))
    if interviewer.to_department.id != profile.designation.department.id:
        if interviewer.to_person and interviewer.to_person.emp_id == profile.emp_id:
            raise_exception = False

        if raise_exception:
            raise ValueError("You cannot make any changes as it currently doesn't belong to your department")


def get_next_to_department(request, current_round, total_rounds, profile, interviewer, cur_app):
    try:
        is_dept_specific = False
        if current_round == total_rounds:
            dept_id = 'ta'
            to_department = Department.objects.get(dept_id=dept_id)
            is_dept_specific = True
        elif current_round <= 0 and profile.designation.department.dept_id == 'ta':
            to_department = cur_app.position_applied.department
        else:
            to_department = interviewer.to_department
        return to_department, is_dept_specific
    except Exception as e:
        logger.info("exception {0}".format(str(e)))
        raise ValueError(
            'given department is invalid, please provide the valid department')


def validate_status_and_feedback_completion(request, candidate):
    if candidate.is_interview_completed:
        raise ValueError(
            "Feedback for this candidate is not accepted, Candidate has completed the interview process")

    stat = request.data.get('status')
    if stat is None:
        raise ValueError("status cannot be empty")

    if stat.lower() == 'applied':
        raise ValueError("Please change the status, status cannot be applied")
    return stat


def check_if_feedback_exists_and_set_last_round_for_hr_or_raise_exception_and_handle_if_rejected(
        stat, interviewer, profile, last_round, current_round, total_rounds):
    if current_round == total_rounds:  # if current_round is equal to total round and user is HR dept /
        if profile.designation.department.dept_id == "ta":  # then allow the user to create a final feedback entry.
            last_round = True

            if stat not in ["Selected For Onboarding", "Rejected"]:
                raise ValueError("The final status must be Selected For Onboarding or Rejected")
        else:
            raise ValueError("Candidate has already completed all the rounds.")

    if interviewer.status.lower() == "rejected" and not last_round:
        raise ValueError("Candidate is already rejected")
    return last_round


def get_round_name(last_round, current_round, cur_app):
    round_names = str("TA Round," + cur_app.position_applied.round_names + ",TA Round").split(",")
    if last_round:
        r_name = round_names[-1]
    else:
        r_name = round_names[current_round]
    return r_name


def update_referral_rejected_status(cur_app, int_status, usr):
    source_ref = cur_app.source_ref
    if int_status.lower() == "rejected" and cur_app.source == "Referral":
        try:
            emp_ref = EmployeeReferral.objects.get(id=source_ref)
            emp_ref.status = "Rejected"
            emp_ref.is_open = False
            emp_ref.comment = "Auto Closed, Candidate is rejected during interview"
            emp_ref.updated_by = usr
            emp_ref.save()
        except Exception as e:
            logger.info("invalid source_ref is provided {0}".format(source_ref))


def send_accepted_rejected_mail_to_candidate(candidate, feedback, position_applied, selected=False,
                                             erf_hc_reached=False):
    if not selected:
        email_template = '<p>Your application has been rejected with the following feedback</p><br>' + \
                         f'<p style="color:blue">{feedback}</p>'
        # if erf_hc_reached:
        #     email_template += '<br>' + \
        #                       '<p> You may re-apply for the same position if there is a new opening for the respective position</p>'
    else:
        email_template = '<p>Congratulations</p><br>' + \
                         f'<p style="color:green"> You have been selected for the {position_applied.designation.name} role</p>'
    try:
        if settings.SEND_EMAIL:
            if not re.search(settings.DEV_EMAIL_OTP_PATTERN, candidate.email):
                subject = "Interview at ECPL"
                email_msg = get_careers_email_message(subject, email_template, to=[candidate.email], reply_to=[])
                email_msg.content_subtype = 'html'
                email_msg.send()
    except Exception as e:
        logger.info("exception at send_accepted_rejected_mail_to_candidate {0}".format(traceback.format_exc(5)))


def check_if_candidate_need_to_complete_test(candidate, cur_app, stat):
    erf = cur_app.position_applied
    if erf is None:
        raise ValueError("Please assign an erf to candidate application")
    test = cur_app.test
    if test and str(stat).lower() != "rejected":
        cd_int_tm = get_candidate_interview_timing(candidate, cur_app, test)
        if cd_int_tm is None or cd_int_tm.test_status == "Started":
            raise ValueError("Candidate need to complete the assessment {0}".format(test.test_name))
        if cd_int_tm.result == "Fail":
            raise ValueError("Please Reject, Candidate has failed in the assessment")


def check_erf_status_required_hc(erf, profile, interview_rounds_stage=False):
    if erf.always_open:
        return
    if not erf.is_erf_open:
        raise ValueError("The assigned erf is already closed")
    cur_hc = erf.profiles.all().count()
    if cur_hc >= erf.hc_req:
        erf.closed_by = profile
        erf.closure_date = datetime.today().date()
        erf.is_erf_open = False
        erf.save()
        raise ValueError("The erf is closed, head-count is fulfilled")

    sel_cd_count = Candidate.objects.filter(current_application__position_applied=erf, is_inactive=False,
                                            status__in=["Selected For Onboarding", "Onboard"]).count()
    req_hc = erf.hc_req - cur_hc
    if sel_cd_count >= req_hc:
        if interview_rounds_stage:
            raise ValueError(
                "{0} candidates already selected for onboarding for the respective erf".format(sel_cd_count))
        else:
            raise ValueError(
                "This erf cannot be selected, {0} candidates already selected for onboarding".format(sel_cd_count))


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def candidate_interview_feedback(request, cd_id):
    try:
        profile = request.user
        print("Profile:",profile)
        candidate = get_candidate_info_by_id(cd_id)
        stat = validate_status_and_feedback_completion(request, candidate)
        cur_app = candidate.current_application
        interviewer = Interviewer.objects.filter(application=cur_app).latest('created_at')

        current_round = interviewer.current_round
        total_rounds = interviewer.total_rounds
        if total_rounds == 0:
            raise ValueError("total rounds is zero contact cc team")
        rejected_reason_erf_hc_reached = False
        if stat.lower() != "rejected":
            check_erf_status_required_hc(cur_app.position_applied, profile, interview_rounds_stage=True)
        else:
            try:
                check_erf_status_required_hc(cur_app.position_applied, profile, interview_rounds_stage=True)
            except Exception as e:
                rejected_reason_erf_hc_reached = True

        # interviewer can edit the record only if it is the latest submission
        last_round = False
        raise_exception_if_to_department_does_not_belongs_to_current_user_or_if_not_previous_user(interviewer, profile)

        last_round = check_if_feedback_exists_and_set_last_round_for_hr_or_raise_exception_and_handle_if_rejected(
            stat, interviewer, profile, last_round, current_round, total_rounds)
        print("Candidate: ",candidate)
        print("Curr Appl: ",cur_app)
        print("Stat: ",stat)
        print("Current Round: ",current_round)
        print("Total Rounds: ",total_rounds)
        check_if_candidate_need_to_complete_test(candidate, cur_app, stat)

        r_person = None
        print("...start")
        if current_round < total_rounds and current_round + 1 < total_rounds:
            print("came here")
            r_person_emp_id = cur_app.position_applied.interview_persons.split(",")[current_round + 1]
            print("Interview Persons:",r_person_emp_id)
            r_person = Profile.objects.filter(emp_id=r_person_emp_id).last()
            print("Persons:",r_person)
            if r_person is None:
                raise ValueError("The linked employee {0} in the erf does not exist".format(r_person_emp_id))

        if not last_round:
            current_round = current_round + 1  # increment the current_round as it is a new_record

        rating = request.data.get('rating')
        if current_round == 0:
            if not rating:
                raise ValueError("Please provide TA Rating")
            cur_app.ta_rating = rating
        if not last_round and total_rounds - current_round == 0:
            if not rating:
                raise ValueError("Please provide ops Rating")
            cur_app.ops_rating = rating
        to_department, is_dept_specific = get_next_to_department(request, current_round, total_rounds, profile,
                                                                 interviewer, cur_app)
        round_name = get_round_name(last_round, current_round, cur_app)
        r_person_id = r_person.id if r_person else None
        data = update_request(request.data, application=cur_app.id, total_rounds=total_rounds,
                              current_round=current_round, interview_emp=profile.id, candidate=candidate.id,
                              round_name=round_name, to_department=to_department.id, is_dept_specific=is_dept_specific,
                              from_department=profile.designation.department.id, to_person=r_person_id)

        serializer_class = CreateInterviewerSerializer(data=data)
        if not serializer_class.is_valid():
            return return_error_response(serializer_class)

        new_interviewer = serializer_class.create(serializer_class.validated_data)
        if not is_dept_specific:
            new_interviewer.editable = True
        interviewer.editable = False
        candidate.status = stat

        # update_employee_referral_if_rejected(stat, candidate)
        if last_round:
            new_interviewer.editable = False
            candidate.is_interview_completed = True
            if stat in ["Selected For Onboarding"]:
                _ = OfferAppointmentLetter.objects.update_or_create(candidate=candidate, application=cur_app, defaults={
                    "spoc_name": None, "spoc_contact_no": None,
                    "appointment_letter": None, "offer_letter": None, "date_of_joining": None})
                send_accepted_rejected_mail_to_candidate(candidate, data.get('feedback'), cur_app.position_applied,
                                                         selected=True)

        if stat.lower() == "rejected":
            send_accepted_rejected_mail_to_candidate(candidate, data.get('feedback'), cur_app.position_applied,
                                                     erf_hc_reached=rejected_reason_erf_hc_reached)
            cur_app.status = False
            candidate.is_interview_completed = True
        else:
            cur_app.to_department = to_department
            if r_person:
                cur_app.interviewer = r_person
                cur_app.all_interview_persons.add(r_person)
            else:
                cur_app.interviewer = None
                cur_app.all_to_departments.add(to_department)
        update_referral_rejected_status(cur_app, stat, profile)
        candidate.last_interview_at = tz.localize(datetime.now())
        candidate.save()
        cur_app.save()
        new_interviewer.save()
        interviewer.save()

    except Exception as e:
        logger.info("exception at {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)

    return HttpResponse(json.dumps({}), status=status.HTTP_200_OK)


def handle_interview_rounds(request, candidate):
    cur_app = candidate.current_application
    data = Interviewer.objects.filter(application_id=cur_app.id).order_by('id')[1:]
    first_round = False
    last_round = False
    initial_round_name = "TA Round"
    temp = None
    if len(list(data)) == 0:
        current_round = 0
        first_round = True
        round_names = [initial_round_name]
    else:
        temp = list(data)[-1]
        round_names = str(initial_round_name + "," + cur_app.position_applied.round_names + ",TA Round").split(",")
        if temp.current_round == temp.total_rounds:
            last_round = True
        current_round = temp.current_round + 1
    try:
        r_name = round_names[current_round]
    except:
        r_name = round_names[-1]

    last_ops_round = False
    if not first_round and temp.total_rounds - temp.current_round == 1:
        last_ops_round = True
    fields_of_experience = cur_app.position_applied.fields_of_experience if cur_app.position_applied else None
    feed_b_round = {"round_name": r_name, "skill_set": fields_of_experience, "first_round": first_round,
                    "last_round": last_round, "last_ops_round": last_ops_round}
    return current_round, temp, feed_b_round, data


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_feedback(request, cd_id):
    try:
        candidate = get_candidate_info_by_id(cd_id)
        cur_app = candidate.current_application
        data = Interviewer.objects.filter(application_id=cur_app.id).order_by('id')[1:]
        int_data = GetAllInterviewerSerializer(data, many=True).data
        return HttpResponse(json.dumps({'feedback': int_data}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_interview_round(request, cd_id):
    try:
        candidate = get_candidate_info_by_id(cd_id)
        current_round, temp, feed_b_round, data = handle_interview_rounds(request, candidate)
        if candidate.is_interview_completed or (
                current_round != 0 and temp.to_person != request.user and not temp.is_dept_specific) or (
                current_round != 0 and temp.to_department != request.user.designation.department and temp.is_dept_specific):
            return HttpResponse(json.dumps({}))
        return HttpResponse(json.dumps({"round": feed_b_round}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])  # TODO handle permission
def update_candidate_erf(request, cnd_id):
    try:
        cnd_id = unhash_value(cnd_id, 'cd')
        erf_id = request.data.get('erf_id')
        try:
            erf = ERF.objects.get(id=erf_id)
            candidate = Candidate.objects.get(id=cnd_id)
        except:
            raise ValueError("Record not found")
        cur_app = candidate.current_application
        check_erf_status_required_hc(erf, request.user)
        if erf.test.count() > 0:
            erf = ERF.objects.filter(id=erf_id).last()
            cur_app.test = choices(erf.test.all())[0]
        else:
            cur_app.test = None
        cur_app.position_applied = erf
        inter = Interviewer.objects.filter(application_id=cur_app.id).order_by('id')
        inter.update(total_rounds=erf.no_of_rounds)
        cur_app.save()
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
    return HttpResponse(json.dumps({}))


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_fields_of_exp(request):
    try:
        serializer = AddFieldsOfExpSerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        # serializer.validated_data['created_by'] = request.user
        _, _ = FieldsOfExperience.objects.get_or_create(category=serializer.validated_data["category"],
                                                        subcategory=serializer.validated_data["subcategory"],
                                                        defaults=serializer.validated_data)
        # serializer.create(serializer.validated_data)
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
    return HttpResponse(json.dumps({}))


@api_view(['GET'])
# @authentication_classes([CustomTokenAuthentication])
# @permission_classes([IsAuthenticated])
def get_document(request, doc_id):
    return document_response(Document, doc_id)


def get_interview_by_int_id(int_id):
    try:
        interview = Interviewer.objects.get(id=int_id)
    except Exception as e:
        raise ValueError("Invalid interview id")
    return interview


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def add_interview_doc(request, feedback_id):
    try:
        usr = request.user
        interview = get_interview_by_int_id(feedback_id)
        inter_files = request.FILES.getlist('interview_doc')
        if inter_files and type(inter_files) == list:
            int_files = []
            for i in inter_files:
                document = update_or_create_file('interview_files', i, interview.candidate, is_filehash=True,
                                                 user=usr)
                if document:
                    int_files.append(document)
            for doc in int_files:
                doc.save()
                interview.interview_files.add(doc)
                interview.uploaded_by = usr
                interview.save()
            return HttpResponse(json.dumps({"message": "Document uploaded successfully"}))
        return HttpResponse(json.dumps({"message": "nothing updated"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_interview_docs(request, feedback_id):
    try:
        interview = get_interview_by_int_id(feedback_id)
        # docs = [{"path": form_document_url(i.id), "name": i.file.name.split("/")[::-1][0],
        #          "uploaded_by_emp_id": i.uploaded_by_emp_id, "uploaded_by_name": i.uploaded_by_name,
        #          "created_at": i.created_at} for i in
        #         interview.interview_files.all()]
        docs = interview.interview_files.all()
        doc_data = DocumentSerializer(docs, many=True).data
        return HttpResponse(json.dumps({"interview_files": doc_data}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def edit_next_interviewer(request, feedback_id):
    try:
        new_interviewer = request.data.get("new_interviewer")
        profile = get_emp_by_emp_id(new_interviewer)
        interview = get_interview_by_int_id(feedback_id)
        if interview.status == "Rejected":
            raise ValueError("The candidate is already rejected")
        if not interview.to_person:
            raise ValueError("No interview person exists for this record")
        old_interviewer = interview.to_person
        interview.application.all_interview_persons.remove(old_interviewer)
        candidates = Candidate.objects.filter(Q(
            current_application__all_interview_persons=old_interviewer, current_application__isnull=False))
        if candidates.count() == 0:
            old_interviewer.interview = False
        interview.application.interviewer = profile
        interview.to_person = profile
        profile.interview = True
        interview.application.all_interview_persons.add(profile)

        interview.application.save()
        interview.save()
        profile.save()
        old_interviewer.save()
        data = Interviewer.objects.filter(application_id=interview.application.id).order_by('id')[1:]
        int_data = GetAllInterviewerSerializer(data, many=True).data
        return HttpResponse(json.dumps({'feedback': int_data}))

    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def edit_candidate(request, cd_id):
    try:
        candidate = handle_update_candidate(request, cd_id, admin=True)
        return HttpResponse(json.dumps(candidate))
    except Exception as e:
        logger.info("in the exception : {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def edit_job_application(request, cd_id):
    try:
        data = request.data
        candidate = get_candidate_info_by_id(cd_id)
        if candidate.status == "Active":
            raise ValueError(
                "The candidate is already an Active Employee. Please contact HR Team for any changes in Employee details.")
        serializer_class = UpdateApplicationSerializer(data=data, partial=True)
        if not serializer_class.is_valid():
            return_error_response(serializer_class, raise_exception=True)
        application = candidate.current_application
        verify_candidate_against_employee_referral_email(candidate.email, data)
        update_employee_referral_if_emp_created(serializer_class.validated_data)
        serializer_class.update(application, serializer_class.validated_data)
        application = UpdateApplicationSerializer(application).data
        return HttpResponse(json.dumps(application))
    except Exception as e:
        logger.info("in the exception : {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def save_file_from_public_server(request):
    try:
        path = "media/" + request.data.get("path")
        file_content = request.data.get("file")
        file_content_bytes = base64.b64decode(file_content)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as file:
            file.write(file_content_bytes)
        logger.info("came to save_file_from_public_server file is saved")
    except Exception as e:
        logger.info("exception at save_file_from_public_server {0} ".format(traceback.format_exc(5)))
    return HttpResponse(json.dumps({"message": "uploaded successfully"}))


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_pending_interviews(request):
    try:
        usr = request.user
        interview_count = Candidate.objects.filter(current_application__interviewer=usr,
                                                   is_interview_completed=False).count()
        return Response({"Pending_Interviews": interview_count})
    except Exception as e:
        logger.info("exception at get_pending_interviews: {0}".format(traceback.format_exc(5)))
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def send_back_candidate_to_applied_status(request, cd_id):
    try:
        usr = request.user
        candidate = get_candidate_info_by_id(cd_id)
        # if candidate.status == "Applied":
        #     raise ValueError("The candidate is already in applied status")
        candidate.status = "Rejected"
        candidate.save()
        old_application = candidate.current_application
        attributes = deepcopy(old_application.__dict__)
        attributes.pop('pk', None)
        attributes["position_applied"] = None

        candidate = handle_create_application(attributes, cd_id)
        _ = ToAppliedCandidateStatus.objects.create(candidate=candidate, old_application=old_application,
                                                    new_application=candidate.current_application, created_by=usr)
        logger.info("{0}".format(old_application.__dict__))

        return HttpResponse(json.dumps({"message": "candidate's status changed to applied"}))
    except Exception as e:
        logger.info("in the exception : {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def get_positions(request):
    try:
        position = InternPosition.objects.all()
        serializer = PositionSerializer(position, many=True)
        return Response({"positions": serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.info("exception at intern position {0}".format(traceback.format_exc(5)))
        return Response({"error": f"{str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_questions(request, position_id):
    try:
        questions = InternQuestion.objects.filter(position__id=position_id)
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.info("exception at intern position {0}".format(traceback.format_exc(5)))
        return Response({"error": f"{str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def submit_intern_application(request):
    try:
        data = request.data
        logger.info(f"data{data}")
        position_id = request.data.get("position_id")
        application_data = update_request(request.data, position=position_id)
        serializer = InternApplicationSerializer(data=application_data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        intern_application = InternApplication.objects.filter(position__id=position_id,
                                                              phone_no=data.get(
                                                                  "phone_no")).first() or InternApplication.objects.filter(
            position__id=position_id,
            email=data.get("email")).first()

        if intern_application:
            raise ValueError("Answers already submitted")
        else:
            intern_application = serializer.create(serializer.validated_data)
        answers = data["answers"]
        logger.info(f"answers {answers}")
        answer_list = []
        for answer in answers:
            answer_text = answer.get("answer")
            question_text = InternQuestion.objects.filter(id=answer.get("id")).first().question_text
            score = validate_answers(answer_text, question_text)

            answer_data = {
                "intern": intern_application.id,
                "question": answer.get("id"),
                "answer_text": answer_text,
                "score": score
            }
            answer_serializer = AnswerSerilizer(data=answer_data)
            if not answer_serializer.is_valid():
                return return_error_response(answer_serializer)
            answer_exists = InternAnswer.objects.filter(intern__id=intern_application.id,
                                                        question__id=answer.get("id")).last()
            if answer_exists:
                continue
            answer_list.append(InternAnswer(**answer_serializer.validated_data))
        if len(answer_list) > 0:
            message = "Answers created successfully"
            InternAnswer.objects.bulk_create(answer_list)
        return Response({"message": message}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Exception at intern application submission: {traceback.format_exc(5)}")
        return Response({"error": f"{str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasUrlPermission])
def export_intern_applications(request):
    start_date = request.data["start_date"]
    end_date = request.data["end_date"]
    intern_data = InternAnswer.objects.filter(created_at__lte=end_date, created_at__gte=start_date)
    total_data = []
    for dt in intern_data:
        single_ansr = [dt.intern.name, dt.intern.position, dt.intern.phone_no]
        question_text = InternQuestion.objects.filter(id=dt.question.id).first().question_text
        single_ansr.append(question_text)
        single_ansr.append(dt.answer_text)
        single_ansr.append(dt.score)
        total_data.append(single_ansr)

    column_names = ["Candidate Name", "Position", "Phone Number", "Question", "Answers", "Score"]
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Intern_application.csv"'
    writer = csv.writer(response)

    writer.writerow(column_names)

    for row in total_data:
        writer.writerow(row)

    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasUrlPermission])
def transport_approval(request, cd_id):
    try:
        usr = request.user
        update_perm = MiscellaneousMiniFields.objects.filter(field="allow_any_transport_approval").first()
        update_perm = update_perm.allow_any_transport_approval if update_perm else None
        if usr.designation.department.dept_id != "admin" or update_perm:
            raise ValueError("Only administration team can approve/reject the transport option")
        transport_approval_status = request.data.get("transport_approval_status")
        transport_approval_comment = request.data.get("transport_approval_comment")
        if transport_approval_status not in [i[0] for i in settings.TRANSPORT_APPROVAL_STATUS]:
            raise ValueError("Invalid transport status given")
        candidate = get_candidate_info_by_id(cd_id)
        if not candidate.is_transport_required:
            raise ValueError("Candidate not opted for transportation requirement")
        if candidate.transport_admin_app_rej_by and candidate.status != "Selected For Onboarding":
            raise ValueError(
                f"Admin {candidate.transport_admin_app_rej_by.emp_id}-{candidate.transport_admin_app_rej_by.full_name} has already {candidate.transport_approval_status} the request")
        if not transport_approval_comment or str(transport_approval_comment).strip() == "":
            raise ValueError("Please provide the comment")

        candidate.transport_approval_status = transport_approval_status
        candidate.transport_admin_app_rej_by = usr
        candidate.transport_approval_comment = transport_approval_comment
        cab_serializer = CabAddressDetailUpdateSerializer(data=candidate.__dict__)
        if cab_serializer.is_valid():
            pass
        cab_serializer.validated_data["candidate"] = candidate
        candidate.cab_address = cab_serializer.create(cab_serializer.validated_data)
        candidate.save()
        return Response({"message": "Transport approval status updated successfully"})
    except Exception as e:
        logger.error(f"Exception at transport_approval: {traceback.format_exc(5)}")
        return Response({"error": f"{str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
