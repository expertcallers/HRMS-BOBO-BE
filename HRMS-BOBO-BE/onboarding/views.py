import base64
import json
import re
import traceback
from datetime import datetime, date

from django.core.files.base import ContentFile, File
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.db import IntegrityError, models
from django.db.models import Q
from django.http import HttpResponse, FileResponse
from rest_framework import status, mixins, authentication, permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
import hashlib
from mimetypes import guess_type
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from erf.models import ERF
from hrms import settings
from interview.serializers import GetAllCandidateSerializer, GetAllSelectedForOnboardSerializer, \
    UpdateCandidateSerializer, CreateCandidateSerializer, CreateApplicationSerializer, UploadCreateApplicationSerializer
from mapping.models import Miscellaneous, Department, Profile, MiscellaneousMiniFields
from onboarding.serializer import GetOnboardSerializer, UpdateOnboardEmployeeSerializer, CreateOnboardSerializer, \
    AppointmentLetterSerializer, GetSalaryStructureSerializer, OfferLetterSerializer, PublicCreateOnboardSerializer
from interview.models import Candidate, Application, Interviewer
from onboarding.models import Onboard, Document, OfferAppointmentLetter
from payroll.models import UpdateSalaryHistory, Salary
from payroll.serializers import UpdateSalarySerializer
from utils.util_classes import CustomTokenAuthentication
from utils.utils import unhash_value, update_request, return_error_response, hash_file, hash_value, document_response, \
    get_sort_and_filter_by_cols, validate_files, get_formatted_name, get_emp_by_emp_id, read_file_format_output, \
    get_decrypted_name, get_full_name, update_email, valid_email_and_aadhaar, validate_model_field, \
    validate_bnk_account_no, check_for_integrity_error, validate_aadhaar_no, get_column_names, \
    verify_candidate_email_otp_info, tz, update_salary_history, get_decrypted_value, \
    handle_onboard_salary_account_number, check_server_status, update_profile_in_qms3
from django.core.files import File as DjangoFile
from interview.views import get_candidate_info_by_id, check_erf_status_required_hc
from mapping.views import HasUrlPermission
import logging

logger = logging.getLogger(__name__)


def update_or_create_file(field, file, onboard, is_filehash=False, user=None):
    emp_id = user.emp_id if user else None
    name = get_formatted_name(user) if user else None
    if is_filehash:
        file_hash_val = hash_file(file)
        document = Document.objects.filter(filehash=file_hash_val, field=field, onboard_id=onboard.id)
        if document.count() > 0:
            return None
        document = Document(filehash=file_hash_val, field=field, onboard_id=onboard.id,
                            file=file, uploaded_by_emp_id=emp_id, uploaded_by_name=name,
                            file_name=file.name)
        return document

    try:
        document = Document.objects.get(field=field, onboard_id=onboard.id)
        document.file.delete(save=False)
        document.uploaded_by_name = name
        document.uploaded_by_emp_id = emp_id
        document.file = file
        document.file_name = file.name
        document.save()
    except Exception as e:
        logger.info("exception at update_or_create_file {0} ".format(str(e)))
        document = Document.objects.create(field=field, onboard_id=onboard.id,
                                           file=file, uploaded_by_name=name, uploaded_by_emp_id=emp_id,
                                           file_name=file.name)
    return document


def get_onboard_by_id(ob_id):
    # try:
    #     ob_id = unhash_value(ob_id, 'ob')
    # except Exception as e:
    #     raise ValueError("Invalid Id {0}".format(str(e)))
    try:
        onboard = Onboard.objects.get(id=ob_id)
    except Exception as e:
        raise ValueError("Onboarding record not found")
    return onboard, ob_id


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_onboard(request, ob_id):
    try:
        onboard, ob_id = get_onboard_by_id(ob_id)
        onboard = GetOnboardSerializer(onboard).data
    except Exception as e:
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}),
                            status=status.HTTP_404_NOT_FOUND)

    return HttpResponse(json.dumps({'onboard': onboard}), status=status.HTTP_200_OK)


class GetAllSelectedForOnboardInfo(mixins.ListModelMixin,
                                   GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllSelectedForOnboardSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        fields_look_up = {"position_applied": "application__position_applied__designation__name",
                          "to_department": "candidate__current_application__to_department__name",
                          "candidate_id": "candidate__id", "dob": "candidate__dob",
                          "first_name": "candidate__first_name", "middle_name": "candidate__middle_name",
                          "last_name": "candidate__last_name", "email": "candidate__email",
                          "updated_at": "candidate__updated_at", "erf_id": "application__position_applied__id",
                          "full_name": "candidate__full_name", "reviewed_by_emp_id": "reviewed_by__emp_id",
                          "reviewed_by_name": "reviewed_by__full_name",
                          "process": "application__position_applied__process__name",
                          "transport_approval_status": "candidate__transport_approval_status"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)

        enable_transport = MiscellaneousMiniFields.objects.filter(field="enable_transport_approval").first()
        logger.info(f"enable_tranport {enable_transport}{enable_transport.yes_no if enable_transport else None}")
        if enable_transport and enable_transport.yes_no:
            self.queryset = OfferAppointmentLetter.objects.filter(candidate__status='Selected For Onboarding',
                                                                  application__status=True).filter(
                ~Q(candidate__transport_approval_status="Pending")).exclude(Q(
                candidate__is_employee=True) | Q(candidate__is_inactive=True)).filter(search_query).filter(
                **filter_by).order_by(*order_by_cols)
        else:
            self.queryset = OfferAppointmentLetter.objects.filter(candidate__status='Selected For Onboarding',
                                                                  application__status=True).exclude(Q(
                candidate__is_employee=True) | Q(candidate__is_inactive=True)).filter(search_query).filter(
                **filter_by).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


class GetAllOnboardInfo(mixins.ListModelMixin,
                        GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetOnboardSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        fields_look_up = {"full_name": "candidate__full_name",
                          "erf_id": "appointment_letter__application__position_applied__id",
                          "process": "appointment_letter__application__position_applied__process__name",
                          "email": "candidate__email", "onboarded_by_emp_id": "onboarded_by__emp_id",
                          "onboarded_by_name": "onboarded_by__full_name"}

        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=fields_look_up)

        self.queryset = Onboard.objects.filter(onboard_status=True).exclude(candidate__is_inactive=True).filter(
            search_query).filter(**filter_by).order_by(
            *order_by_cols)

        return self.list(request, *args, **kwargs)


def handle_basic_onboard_files(request, onboard, source="private"):
    usr = request.user if source == "private" else None
    education_documents = request.FILES.getlist('education') or []
    relieving_letters = request.FILES.getlist('relieving') or []
    edu_docs = []
    rel_docs = []
    for i in education_documents:
        document = update_or_create_file('education_documents', i, onboard, is_filehash=True, user=usr)
        if document:
            edu_docs.append(document)
    for i in relieving_letters:
        document = update_or_create_file('relieving_letters', i, onboard, is_filehash=True, user=usr)
        if document:
            rel_docs.append(document)
    if len(edu_docs) > 0:
        for doc in edu_docs:
            doc.save()
            onboard.education_documents.add(doc)
    if len(rel_docs) > 0:
        for doc in rel_docs:
            doc.save()
            onboard.relieving_letters.add(doc)

    photo = request.FILES.get('phto')
    if photo:
        onboard.photo_id = update_or_create_file('photo', photo, onboard, user=usr).id
    pancard = request.FILES.get('pan')
    if pancard:
        onboard.pancard_id = update_or_create_file('pancard', pancard, onboard, user=usr).id
    aadhaar = request.FILES.get('aadhaar')
    if aadhaar:
        onboard.aadhaar_card_id = update_or_create_file('aadhaar_card', aadhaar, onboard, user=usr).id

    copy_of_signed_nda = request.data.get('signed_nda')
    if copy_of_signed_nda:
        onboard.copy_of_signed_nda_id = update_or_create_file('copy_of_signed_nda', copy_of_signed_nda, onboard,
                                                              user=usr).id
    copy_of_signed_offer_letter = request.data.get('signed_offer_letter')
    if copy_of_signed_offer_letter:
        onboard.copy_of_signed_offer_letter_id = update_or_create_file('copy_of_signed_offer_letter',
                                                                       copy_of_signed_offer_letter, onboard,
                                                                       user=usr).id
    cheque_copy = request.data.get("cheque")
    if cheque_copy:
        onboard.cheque_copy_id = update_or_create_file('cheque_copy', cheque_copy, onboard, user=usr).id

    return onboard


def update_salary_details(request, salary, data=None):
    if data is None:
        account_number = request.data.get("account_number")
        if not account_number and str(account_number).strip() == "":
            account_number = None
        data = update_request(request.data, updated_by=request.user.id, account_number=account_number)

    salary_serializer = UpdateSalarySerializer(data=data, partial=True)
    if not salary_serializer.is_valid():
        return_error_response(salary_serializer)
    update_sal = update_salary_history(salary, request, salary_serializer.validated_data,
                                       request.user, "updating onboard information")
    if update_sal:
        UpdateSalaryHistory.objects.bulk_create([update_sal])

    salary_serializer.update(salary, salary_serializer.validated_data)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_onboard_employee(request, ob_id):
    try:
        onboard, ob_id = get_onboard_by_id(ob_id)
        validate_files(request.FILES, 'onboard')
        data = update_request(request.data, onboarded_by=request.user.id)
        serializer = UpdateOnboardEmployeeSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return_error_response(serializer, raise_exception=True)

        update_salary_details(request, onboard.salary)
        serializer.update(onboard, serializer.validated_data)
        onboard = handle_basic_onboard_files(request, onboard)
        onboard.save()

        onboard = GetOnboardSerializer(onboard).data
        onboard['message'] = "Updated onboard successfully"
        return Response(onboard)
    except Exception as e:
        logger.info("exception at update_onboard_employee {0}".format(traceback.format_exc(5)))

        return Response(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def check_onboard_files(request):
    aadhaar = request.FILES.get('aadhaar')
    if aadhaar is None:
        raise ValueError("Please upload valid aadhaar document")


def handle_onboard(request, cd_id, serializer_class, source):
    candidate = get_candidate_info_by_id(cd_id)
    aadhaar_no = get_decrypted_name(candidate.aadhaar_no)
    gender = candidate.gender
    dob = candidate.dob
    offer = OfferAppointmentLetter.objects.filter(application_id=candidate.current_application.id).last()
    message = "Updated the onboard-information successfully"
    if offer is None:
        raise ValueError("Offer letter not found for this candidate")
    if not offer.is_offer_letter_accepted:
        raise ValueError("Offer letter is not accepted for this candidate")
    logger.info("create onboard")
    # salary_structure = calculate_salary_structure(offer.pay_grade, offer.total_fixed_gross, offer.opting_for_pf)
    is_authenticated = request.user.is_authenticated
    user_details = {}
    if source == "public":
        user_details = {"created_by_candidate_at": tz.localize(datetime.now()),
                        "date_of_joining": offer.date_of_joining}
        # logger.info(f"user details {user_details}")
    user_details["onboarded_by"] = request.user.id if source == "private" else None
    data = update_request(request.data, aadhaar_no=aadhaar_no, gender=gender, dob=dob, **user_details)

    # data = update_request(request.data, candidate=candidate.id, onboarded_by=request.user.id,
    #                       aadhaar_no=aadhaar_no, gender=gender, dob=dob, pay_grade=offer.pay_grade, **salary_structure)
    onboard = Onboard.objects.filter(candidate=candidate).first()
    if onboard is None:
        serializer = serializer_class(data=data)
    else:
        serializer = serializer_class(data=data, partial=True)
    if not serializer.is_valid():
        return return_error_response(serializer, raise_exception=True)
    serializer.validated_data["onboard_status"] = True
    validate_files(request.FILES, 'onboard')
    serializer.validated_data["salary"] = offer.salary

    if onboard is None:
        check_onboard_files(request)
        serializer.validated_data["candidate"] = candidate
        onboard = serializer.create(serializer.validated_data)
        message = "Added the onboard-information successfully"
    else:
        onboard = serializer.update(onboard, serializer.validated_data)
    offer.is_onboard_created = True
    offer.save()
    update_salary_details(request, onboard.salary)
    candidate.status = 'Onboard'
    onboard.appointment_letter = offer
    validate_files(request.FILES, 'onboard')
    onboard = handle_basic_onboard_files(request, onboard, source=source)
    onboard.save()
    candidate.save()
    candidate.save()
    onboard.save()
    return GetOnboardSerializer(onboard).data, message


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_onboard(request, cd_id):
    # profile = request.user
    try:
        onboard, message = handle_onboard(request, cd_id, CreateOnboardSerializer, "private")
        return HttpResponse(json.dumps({'onboard': onboard, "message": message}))
    except Exception as e:
        logger.info("exception at create onboard {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({'error': str(e)}),
                            status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def public_create_onboard(request, cd_id):
    # profile = request.user
    try:
        otp, email, cand_otp_obj = verify_candidate_email_otp_info(request)
        onboard, message = handle_onboard(request, cd_id, PublicCreateOnboardSerializer, "public")
        return HttpResponse(json.dumps({'onboard': onboard, "message": message}))
    except Exception as e:
        logger.info("exception at create onboard {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({'error': str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_document(request, doc_id):
    return document_response(Document, doc_id)


def handle_delete_document(doc_id):
    try:
        doc_id = unhash_value(doc_id, 'doc')
    except Exception as e:
        logger.info("Invalid document id")
        raise ValueError("invalid document id")

    try:
        document = Document.objects.get(id=doc_id)
    except Exception as e:
        logger.info("exception at delete_document {0}".format(traceback.format_exc(5)))
        raise ValueError("Record not found")
    if document.field in ["aadhaar_card"]:
        raise ValueError("You cannot delete this file")

    document.file.delete()
    document.delete()


@api_view(['DELETE'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def delete_document(request, doc_id):
    try:
        handle_delete_document(doc_id)
        return HttpResponse(json.dumps({"message": "document deleted successfully"}))
    except Exception as e:
        logger.info("exception at delete_document {0}".format(traceback.format_exc(5)))

        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def public_delete_document(request, doc_id):
    try:
        otp, email, cand_otp_obj = verify_candidate_email_otp_info(request)
        try:
            candidate = Candidate.objects.get(email=email)
        except Exception as e:
            raise ValueError("Candidate with this email does not exist")
        handle_delete_document(doc_id)
        return HttpResponse(json.dumps({"message": "document deleted successfully"}))
    except Exception as e:
        logger.info("exception at delete_document {0}".format(traceback.format_exc(5)))

        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def send_appointment_letter(request, cd_id):
    try:
        usr = request.user
        candidate = get_candidate_info_by_id(cd_id)
        appointment_letter = request.data.get('appointment_doc')

        if appointment_letter is None:
            raise ValueError("Appointment Letter file is required.")
        a_data = appointment_letter.split(",")
        pdf_data = base64.b64decode(a_data[1] if len(a_data) > 1 else a_data[0])
        appointment_letter = ContentFile(pdf_data)

        validate_files(request.FILES, 'appointment_letter')
        offer = OfferAppointmentLetter.objects.filter(candidate_id=candidate.id,
                                                      application=candidate.current_application.id)
        # if offer.exists():
        #     if offer[0].is_onboard_created:
        #         raise ValueError("Candidate is already onboarded.")
        offer_data = request.data
        AppointmentLetter_serializer = AppointmentLetterSerializer(data=offer_data)
        if not AppointmentLetter_serializer.is_valid():
            return_error_response(AppointmentLetter_serializer, raise_exception=True)
        fname = f"{get_formatted_name(candidate)} appointment letter.pdf"
        # if not (settings.DEBUG and re.search(settings.DEV_EMAIL_OTP_PATTERN, candidate.email)):
        #     subject = "Appointment letter"
        #     email_template = "Congratulation We are happy to send you the Appointment letter"
        #     email_msg = EmailMessage(subject, email_template, to=[candidate.email], reply_to=[])
        #     email_msg.content_subtype = 'html'
        #     email_msg.attach(fname, pdf_data, 'application/pdf')
        #     email_msg.send()
        document = update_or_create_file("appointment_letter", File(appointment_letter, name=fname), candidate,
                                         user=usr)
        AppointmentLetter_serializer.validated_data["appointment_letter"] = document

        if offer.exists():
            offer.update(date_of_joining=offer_data['date_of_joining'], appointment_letter_id=document.id)
        else:
            offer = AppointmentLetter_serializer.create(AppointmentLetter_serializer.validated_data)


    except Exception as e:
        logger.info("Exception at send appointment letter {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)

    logger.info("appointment letter send for email {0}".format(candidate.email))
    return HttpResponse(json.dumps({"message": "appointment letter is sent"}))


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def send_offer_letter(request, cd_id):
    try:
        usr = request.user
        candidate = get_candidate_info_by_id(cd_id)
        offer_letter = request.data.get('offer_doc')

        if offer_letter is None:
            raise ValueError("Offer Letter file is required.")
        a_data = offer_letter.split(",")
        pdf_data = base64.b64decode(a_data[1] if len(a_data) > 1 else a_data[0])
        offer_letter = ContentFile(pdf_data)

        validate_files(request.FILES, 'offer_letter')
        offer = OfferAppointmentLetter.objects.filter(application_id=candidate.current_application.id).last()
        if offer:
            if offer.is_onboard_created:
                raise ValueError("Candidate's onboard already created")
            if offer.is_offer_letter_accepted:
                raise ValueError("Candidate has already accepted the previous offer letter")

        offer_data = update_request(request.data, reviewed_by=request.user.id, candidate=candidate.id,
                                    application=candidate.current_application.id)
        OfferLetter_serializer = OfferLetterSerializer(data=offer_data)
        if not OfferLetter_serializer.is_valid():
            return_error_response(OfferLetter_serializer, raise_exception=True)
        fname = f"{get_formatted_name(candidate)} offer letter.pdf"

        # logger.info("offer letter {0}".format(OfferLetter_serializer.validated_data))
        # if not (settings.DEBUG and re.search(settings.DEV_EMAIL_OTP_PATTERN, candidate.email)):
        #     subject = "Offer letter"
        #     email_template = "Congratulation We are happy to send you the offer letter"
        #     email_msg = EmailMessage(subject, email_template, to=[candidate.email], reply_to=[])
        #     email_msg.content_subtype = 'html'
        #     email_msg.attach(fname, pdf_data, 'application/pdf')
        #     email_msg.send()

        salary_data = update_request(offer_data, updated_by=request.user.id, last_update_reason="Onboard")
        salary_serializer = UpdateSalarySerializer(data=salary_data)
        if not salary_serializer.is_valid():
            return return_error_response(salary_serializer)
        # sal_calc = salary_serializer.validated_data
        # gross = sal_calc["basic"] + sal_calc["tds"] + sal_calc["health_insurance_deduction"] + sal_calc["ta"] + sal_calc["medical_allowance"] + \
        #         sal_calc["tel_allowance"] + sal_calc["oa"]
        document = update_or_create_file("offer_letter", File(offer_letter, name=fname), candidate, user=usr)
        OfferLetter_serializer.validated_data["offer_letter"] = document

        if offer:
            OfferLetter_serializer.update(offer, OfferLetter_serializer.validated_data)
        else:
            offer = OfferLetter_serializer.create(OfferLetter_serializer.validated_data)
        opting_for_pf = salary_serializer.validated_data.get("opting_for_pf")
        if opting_for_pf:
            pf_emp = salary_serializer.validated_data.get("pf_emp")
            pf_emr = salary_serializer.validated_data.get("pf_emr")
            if (pf_emp is None or not str(pf_emp).isnumeric() or int(pf_emp) <= 0) or (
                    pf_emr is None or not str(pf_emr).isnumeric() or int(pf_emr) <= 0):
                raise ValueError("please provide PF Emp Value")
        if offer.salary:
            update_sal = update_salary_history(offer.salary, request, salary_serializer.validated_data, usr,
                                               "update offer-salary")
            if update_sal:
                UpdateSalaryHistory.objects.bulk_create([update_sal])
            salary_serializer.update(offer.salary, salary_serializer.validated_data)
        else:
            offer.salary = salary_serializer.create(salary_serializer.validated_data)
        offer.save()


    except Exception as e:
        logger.info("Exception at send appointment letter {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)

    logger.info("appointment letter send for email {0}".format(candidate.email))
    return HttpResponse(json.dumps({"message": "appointment letter is sent"}))


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def update_offer_response(request, cd_id):
    try:
        candidate = get_candidate_info_by_id(cd_id)
        offer_letter = OfferAppointmentLetter.objects.filter(
            application_id=candidate.current_application.id).last()
        if offer_letter is None:
            raise ValueError("{0}, Candidate  offer letter is not generated".format(candidate.id))
        is_offer_letter_accepted = request.data.get('is_offer_letter_accepted')
        if is_offer_letter_accepted is None:
            raise ValueError("Please provide the offer letter acceptance value")
        # salary_data = update_request(request.data, candidate=candidate.id, updated_by=request.user.id,
        #                              last_update_reason="Onboard")
        # salary_serializer = UpdateSalarySerializer(data=salary_data, partial=True)
        # if not salary_serializer.is_valid():
        #     return return_error_response(salary_serializer)
        # salary_serializer.update(offer_letter.salary, salary_serializer.validated_data)
        logger.info("is_offer_letter_accepted {0}".format(is_offer_letter_accepted))
        offer_letter.is_offer_letter_accepted = is_offer_letter_accepted
        offer_letter.save()

    except Exception as e:
        logger.info("Exception at update_appointment_response {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)

    logger.info("updated {0}'s offer letter  acceptance to {0}".format(str(candidate.id)))
    return HttpResponse(json.dumps({"message": "offer letter status is updated"}))


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def upload_health_card(request):
    try:
        usr = request.user
        health_cards = request.FILES.getlist('health_card') or []
        uploaded = "No Changes Done"
        for card in health_cards:
            logger.info("name={0}".format(card))
            profile = get_emp_by_emp_id(card.name[:-4])
            if card.name[-3:] != "pdf":
                raise ValueError("Please upload pdf files only")
            onboard = profile.onboard
            if onboard:
                document = update_or_create_file('health_card', card, onboard, user=usr)
                onboard.health_card = document
                onboard.save()
                uploaded = "Uploaded Successfully"
        return HttpResponse(json.dumps({"message": "{0}".format(uploaded)}))
    except Exception as e:
        logger.info("exception at upload_health_card {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def create_candidate_application_interviewer(data, i, profile, erf):
    # cols = ['status', 'first_name', 'middle_name', 'last_name', 'email', 'dob', 'mobile',
    #         'highest_qualification', 'aadhaar_no', 'gender', "source", "branch"]
    model_fields = Candidate._meta.get_fields()
    cols = [field.name for field in model_fields if field.concrete and not isinstance(field, (
        models.FileField, models.ManyToManyField, models.ForeignKey))]
    appl_fields, _ = get_column_names(Application)
    cols = cols + appl_fields
    cnd_data = {"is_employee": True, "is_interview_completed": True}
    for col in cols:
        cnd_val = data.get(col)
        if cnd_val:
            cnd_data[col] = cnd_val[i]
            cnd_data[col] = str(cnd_data[col]).strip() if isinstance(cnd_data[col], str) else cnd_data[col]
    if profile.first_name:
        cnd_data["first_name"] = profile.first_name if profile.first_name else None
    if profile.middle_name:
        cnd_data["middle_name"] = profile.middle_name if profile.middle_name else None
    if profile.last_name:
        cnd_data["last_name"] = profile.last_name if profile.last_name else None

    if cnd_data['first_name'] is None:
        raise ValueError(f"First name of {profile.emp_id} is not given")
    cnd_data["full_name"] = get_full_name(cnd_data)

    default_zero = ['current_ctc', "expected_ctc"]
    for col in default_zero:
        current_ctc = data.get(col)
        cnd_data[col] = current_ctc[i] if current_ctc else 0

    cnd_data["status"] = profile.status
    created = False
    aadhaar_no = cnd_data.get('aadhaar_no')
    mobile = cnd_data.get("mobile")
    if mobile and len(str(mobile)) != 10 or not str(mobile).isnumeric():
        cnd_data["mobile"] = None
    if len(str(cnd_data["mobile"])) != 10:
        cnd_data["mobile"] = None
    if "mobile_alt" not in cnd_data or len(str(cnd_data["mobile_alt"])) != 10:
        cnd_data["mobile_alt"] = None
    email = cnd_data.get('email')
    if email:
        email = cnd_data['email'] = str(email).strip()
        try:
            validate_email(email)
        except Exception as e:
            email = cnd_data['email'] = None
    candidate = None
    if aadhaar_no is None:
        raise ValueError("Please provide the aadhaar_no")
    if mobile is None:
        raise ValueError("Please provide the mobile information")
    if email is None:
        raise ValueError("Please provide the email")

    if profile.onboard and profile.onboard.candidate:
        # logger.info("onboard candidate")
        candidate = profile.onboard.candidate

    if aadhaar_no and candidate is None:
        candidate = Candidate.objects.filter(aadhaar_no=aadhaar_no).last()
    dob = cnd_data.get('dob')
    if dob and isinstance(dob, datetime):
        cnd_data['dob'] = dob.date()
    if profile.dob:
        cnd_data['dob'] = profile.dob
    if not candidate:
        cnd_serializer = CreateCandidateSerializer(data=cnd_data, partial=True)
        if not cnd_serializer.is_valid():
            return_error_response(cnd_serializer, raise_exception=True)
        candidate = cnd_serializer.create(cnd_serializer.validated_data)
        created = True

    if not created:
        cnd_serializer = UpdateCandidateSerializer(data=cnd_data, partial=True)
        if not cnd_serializer.is_valid():
            return_error_response(cnd_serializer, raise_exception=True)
        for key, value in cnd_serializer.validated_data.items():
            setattr(candidate, key, value)
        if email:
            validate_model_field(email, validate_email)
            candidate = check_for_integrity_error("email", email.lower(), candidate)
        validate_model_field(aadhaar_no, validate_aadhaar_no)
        candidate = check_for_integrity_error("aadhaar_no", aadhaar_no, candidate)
        candidate.profile = profile

        candidate.save()
    to_department = Department.objects.get(dept_id='ta')
    cur_app = candidate.current_application
    cnd_data["branch"] = "HBR Layout"
    if not cur_app:
        cnd_data["to_department"] = to_department.id
        app_serializer = UploadCreateApplicationSerializer(data=cnd_data)
        if not app_serializer.is_valid():
            return_error_response(app_serializer, raise_exception=True)
        application = Application.objects.create(to_department=profile.designation.department, position_applied=erf,
                                                 job_position=profile.designation.name, source=cnd_data.get("source"),
                                                 branch=cnd_data.get("branch"), candidate=candidate)
        candidate.current_application = application
        candidate.all_applications.add(application)
        candidate.is_interview_completed = True
        candidate.save()

    else:
        app_serializer = UploadCreateApplicationSerializer(data=cnd_data, partial=True)
        if not app_serializer.is_valid():
            return_error_response(app_serializer, raise_exception=True)
        app_serializer.update(cur_app, app_serializer.validated_data)
    inter = Interviewer.objects.filter(application=candidate.current_application, candidate=candidate).last()
    if inter is None:
        _ = Interviewer.objects.create(application=candidate.current_application, candidate=candidate,
                                       status=cnd_data.get("status"), feedback="System generated", result=True,
                                       to_department=profile.designation.department, total_rounds=1,
                                       from_department=profile.designation.department, current_round=-1,
                                       is_dept_specific=True)

    # department, created = Department.objects.get(name=data.get("department"))  # TODO
    # designation, created = Department.objects.get_or_create(name=data.get("designation"), department=department)

    return candidate


def create_candidate_application_interviewer_by_emp(cnd_data, i, profile, erf):
    # cols = ['status', 'first_name', 'middle_name', 'last_name', 'email', 'dob', 'mobile',
    #         'highest_qualification', 'aadhaar_no', 'gender', "source", "branch"]

    cnd_data["is_employee"] = True
    cnd_data["is_interview_completed"] = True
    cnd_data["full_name"] = get_full_name(cnd_data)

    salary = profile.onboard.salary if profile.onboard else None
    # if salary is None:
    #     raise ValueError("There is no salary information contact HR")

    cnd_data["current_ctc"] = get_decrypted_value(salary.ctc) if salary else 0
    cnd_data["expected_ctc"] = cnd_data["current_ctc"]

    cnd_data["status"] = profile.status
    created = False
    aadhaar_no = cnd_data.get('aadhaar_no')
    mobile = cnd_data.get("mobile")
    email = cnd_data.get('email')
    if mobile is None:
        raise ValueError("Please provide the mobile information")
    if email is None:
        raise ValueError("Please provide the email")
    if aadhaar_no is None:
        raise ValueError("Please provide the aadhaar_no")

    candidate = None
    if profile.onboard and profile.onboard.candidate:
        candidate = profile.onboard.candidate
    if aadhaar_no and candidate is None:
        candidate = Candidate.objects.filter(aadhaar_no=aadhaar_no).last()
    if not candidate:
        cnd_serializer = CreateCandidateSerializer(data=cnd_data, partial=True)
        if not cnd_serializer.is_valid():
            return_error_response(cnd_serializer, raise_exception=True)
        candidate = cnd_serializer.create(cnd_serializer.validated_data)
        created = True

    if not created:
        cnd_serializer = UpdateCandidateSerializer(data=cnd_data, partial=True)
        if not cnd_serializer.is_valid():
            return_error_response(cnd_serializer, raise_exception=True)
        for key, value in cnd_serializer.validated_data.items():
            setattr(candidate, key, value)
        if email:
            validate_model_field(email, validate_email)
            candidate = check_for_integrity_error("email", email.lower(), candidate)
        validate_model_field(aadhaar_no, validate_aadhaar_no)
        candidate = check_for_integrity_error("aadhaar_no", aadhaar_no, candidate)
        candidate.save()
    to_department = Department.objects.get(dept_id='ta')
    cnd_data["branch"] = "Kothnur"
    cnd_data["source"] = "Walkin"
    if not candidate.current_application:
        cnd_data["to_department"] = to_department.id
        app_serializer = UploadCreateApplicationSerializer(data=cnd_data)
        if not app_serializer.is_valid():
            return_error_response(app_serializer, raise_exception=True)
        application = Application.objects.create(to_department=profile.designation.department, position_applied=erf,
                                                 job_position=profile.designation.name, source=cnd_data.get("source"),
                                                 branch=cnd_data.get("branch"), candidate=candidate)
        candidate.current_application = application
        candidate.all_applications.add(application)
        candidate.is_interview_completed = True
        candidate.save()

    else:
        app_serializer = UploadCreateApplicationSerializer(data=cnd_data, partial=True)
        if not app_serializer.is_valid():
            return_error_response(app_serializer, raise_exception=True)
        app_serializer.update(candidate.current_application, app_serializer.validated_data)
    inter = Interviewer.objects.filter(application=candidate.current_application, candidate=candidate).last()
    if inter is None:
        _ = Interviewer.objects.create(application=candidate.current_application, candidate=candidate,
                                       status=cnd_data.get("status"), feedback="System generated", result=True,
                                       to_department=profile.designation.department, total_rounds=1,
                                       from_department=profile.designation.department, current_round=-1,
                                       is_dept_specific=True)

    # department, created = Department.objects.get(name=data.get("department"))  # TODO
    # designation, created = Department.objects.get_or_create(name=data.get("designation"), department=department)

    return candidate


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def upload_onboard_details(request):
    emp_id = None
    obj_data = None
    try:
        map_columns = {}
        xl_file = request.data.get("onboard_details")
        if not xl_file:
            raise ValueError("Please upload onboard file")
        xl_data = read_file_format_output(xl_file)
        column_names, _ = get_column_names(Onboard)
        column_names.append("date_of_joining")
        i = 0
        required_cols = ["emp_id"]
        xl_data_keys = xl_data.keys()
        for col in required_cols:
            if col not in xl_data_keys:
                raise ValueError("{0} column is required".format(col))
        emp_id_list = xl_data.get("emp_id")
        while emp_id_list and i < len(emp_id_list):
            emp_id = xl_data['emp_id'][i]
            aadhaar_no = xl_data["aadhaar_no"][i]
            if aadhaar_no is None or str(aadhaar_no).strip() == "" or len(str(aadhaar_no)) != 12:
                i += 1
                continue

            if emp_id is None:
                i += 1
                continue
            profile = Profile.objects.filter(emp_id=emp_id).last()
            if not profile:
                logger.info("there is no profile with emp_id {0}".format(emp_id))
                i += 1
                continue
                # raise ValueError("there is no profile with emp_id {0}".format(emp_id))

            erf = get_empty_erf()
            obj_data = None
            candidate = create_candidate_application_interviewer(xl_data, i, profile, erf)
            obj_data = {"candidate": candidate.id}
            # logger.info(f"emp_id initial {emp_id}")

            for col_name in column_names:
                map_name = map_columns.get(col_name, col_name)
                xl_col = xl_data.get(map_name)
                if xl_col is None:
                    continue
                value = xl_col[i]
                # if str(emp_id) == "11554":
                #     logger.info(f" col_name {col_name} value {value}, {type(value)}")

                value = value.date() if isinstance(value, datetime) else value
                # if isinstance(value, date):
                #     logger.info(f"date {value}")

                obj_data[col_name] = str(value).strip() if isinstance(value, str) else value

            onboard = Onboard.objects.filter(candidate=candidate).last()

            if "emergency_contact_1" not in obj_data:
                obj_data["emergency_contact_1"] = None
            else:
                econtact1 = obj_data.get("emergency_contact_1")
                if len(str(econtact1).split("/")) > 1:
                    obj_data["emergency_contact_1"] = str(econtact1).split("/")[0]
                    obj_data["emergency_contact_2"] = str(econtact1).split("/")[1]
                    logger.info(f"came splitting {obj_data['emergency_contact_1']}")
            if len(str(obj_data["emergency_contact_1"])) != 10 or not str(
                    obj_data["emergency_contact_1"]).isnumeric():
                obj_data["emergency_contact_1"] = None
            if len(str(obj_data["emergency_contact_2"])) != 10 or not str(
                    obj_data["emergency_contact_2"]).isnumeric():
                obj_data["emergency_contact_2"] = None

            # ECPl
            # sal_structure = calculate_salary_structure(pay_grade, ctc, opting_for_pf)
            # for key, value in sal_structure.items():
            #     obj_data[key] = value
            # doj = None
            # if "date_of_joining" in obj_data.keys():
            #     doj = obj_data.get("date_of_joining")
            #     # if doj is None:
            #     #     raise ValueError("date_of_joining is required")
            #     if doj and isinstance(doj, datetime):
            #         obj_data['date_of_joining'] = doj.date()
            #         doj = doj.date()

            obj_data["onboard_status"] = False
            obj_data["dob"] = candidate.dob
            # if "salary_account_number" in obj_data:
            #     if (str(obj_data["salary_account_number"]).strip() == ""
            #             or len(str(obj_data["salary_account_number"])) < 11 or len(str(
            #                 obj_data["salary_account_number"])) > 16 or not str(
            #                 obj_data["salary_account_number"]).isnumeric()):
            #         obj_data["salary_account_number"] = None
            # if "salary_account_bank_ifsc" in obj_data:
            #     if str(obj_data["salary_account_bank_ifsc"]).strip() == "" or len(
            #             str(obj_data["salary_account_bank_ifsc"])) != 11:
            #         obj_data["salary_account_bank_ifsc"] = None

            if onboard:
                try:
                    # elif onboard.salary_account_number:
                    #     obj_data["salary_account_number"] = onboard.salary_account_number
                    # else:
                    #     obj_data["salary_account_number"] = None

                    # logger.info("onboard exists {0}, emp_id {1}".format(onboard.id, emp_id))
                    upd_ob_serializer = UpdateOnboardEmployeeSerializer(data=obj_data, partial=True)
                    if not upd_ob_serializer.is_valid():
                        return_error_response(upd_ob_serializer, raise_exception=True)
                    # if "salary_account_number" in obj_data and obj_data["salary_account_number"]:
                    #     validate_model_field(obj_data["salary_account_number"], validate_bnk_account_no)
                    #     onboard = check_for_integrity_error("salary_account_number", obj_data["salary_account_number"],
                    #                                         onboard)
                    upd_ob_serializer.validated_data["date_of_joining"] = profile.date_of_joining
                    upd_ob_serializer.validated_data["branch"] = "Kothnur"
                    upd_ob_serializer.update(onboard, upd_ob_serializer.validated_data)
                    profile.onboard = onboard
                    # logger.info("update profile done")
                except IntegrityError as e:
                    tmp_profile = Profile.objects.filter(onboard=onboard).last()
                    raise ValueError(
                        "There is a profile with emp_id {0} already linked with this onboard/candidate details".format(
                            tmp_profile.emp_id if tmp_profile else ""))
            else:
                # logger.info("enter create onboard, emp_id {0}".format(emp_id))
                onboard_serializer = CreateOnboardSerializer(data=obj_data)
                if not onboard_serializer.is_valid():
                    return_error_response(onboard_serializer)
                onboard_serializer.validated_data["candidate"] = candidate
                onboard_serializer.validated_data["date_of_joining"] = profile.date_of_joining
                onboard_serializer.validated_data["branch"] = "Kothnur"
                profile.onboard = Onboard.objects.create(**onboard_serializer.validated_data)
                # logger.info("onboard created {0}".format(profile.onboard))
            # if doj:
            #     profile.date_of_joining = doj
            if onboard and onboard.salary is None:
                onboard.salary = Salary.objects.filter(profile=profile).first()
                onboard.save()
            profile.dob = candidate.dob
            profile.full_name = candidate.full_name
            # profile.first_name = candidate.first_name
            # profile.middle_name = candidate.middle_name
            # profile.last_name = candidate.last_name or ""
            profile.save()
            erf.profiles.add(profile)
            i += 1
        return HttpResponse(json.dumps({"message": "onboard details updated"}))
    except Exception as e:
        logger.info("emp_id {0}".format(emp_id))
        logger.info(f"exception obj {obj_data}")
        logger.info("exception at upload_onboard_details {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_empty_erf():
    erf, created = ERF.objects.get_or_create(approval_status="Approved", requisition_date="2024-06-13", hc_req=0,
                                             no_of_rounds=0, round_names="migration", defaults=
                                             {"approval_status": "Approved", "requisition_date": "2024-06-13",
                                              "hc_req": 0, "pricing": 0,
                                              "salary_range_frm": 1, "salary_range_to": 2, "qualification": "Graduate",
                                              "fields_of_experience": "Other",
                                              "shift_timing": "Rotational", "type_of_working": "Rotational",
                                              "requisition_type": "Buffer",
                                              "no_of_rounds": 0, "round_names": "migration", "interview_persons": 9194,
                                              "deadline": "2024-06-13",
                                              "is_erf_open": False})
    return erf


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_candidate_onboard_details(request):
    data = None
    try:
        profile = request.user
        emp_id = profile.emp_id
        otp, email, cand_otp_obj = verify_candidate_email_otp_info(request)
        map_columns = {}
        column_names, _ = get_column_names(Onboard)
        column_names.append("date_of_joining")
        i = 0
        data = {}
        for key, val in request.data.items():
            data[key] = val
        erf = get_empty_erf()
        data["source"] = "Walkin"
        candidate = create_candidate_application_interviewer_by_emp(data, i, profile, erf)
        obj_data = data
        obj_data["candidate"] = candidate.id
        logger.info(f"emp_id initial {emp_id}")
        onboard = Onboard.objects.filter(candidate=candidate).last()

        obj_data["onboard_status"] = False
        obj_data["dob"] = candidate.dob

        if onboard:
            try:
                upd_ob_serializer = UpdateOnboardEmployeeSerializer(data=obj_data, partial=True)
                if not upd_ob_serializer.is_valid():
                    return_error_response(upd_ob_serializer, raise_exception=True)
                upd_ob_serializer.validated_data["date_of_joining"] = profile.date_of_joining
                if onboard.branch is None or str(onboard.branch).strip() == "":
                    branch = upd_ob_serializer.validated_data.get("branch")
                    if branch is None or str(branch).strip() == "":
                        upd_ob_serializer.validated_data["branch"] = "Kothnur"
                upd_ob_serializer.update(onboard, upd_ob_serializer.validated_data)
                profile.onboard = onboard
                # logger.info("update profile done")
            except IntegrityError as e:
                tmp_profile = Profile.objects.filter(onboard=onboard).last()
                raise ValueError(
                    "There is a profile with emp_id {0} already linked with this onboard/candidate details".format(
                        tmp_profile.emp_id if tmp_profile else ""))
        else:
            # logger.info("enter create onboard, emp_id {0}".format(emp_id))
            onboard_serializer = CreateOnboardSerializer(data=obj_data)
            if not onboard_serializer.is_valid():
                return_error_response(onboard_serializer)
            onboard_serializer.validated_data["candidate"] = candidate
            onboard_serializer.validated_data["date_of_joining"] = profile.date_of_joining
            onboard_serializer.validated_data["branch"] = "Kothnur"
            profile.onboard = Onboard.objects.create(**onboard_serializer.validated_data)
            # logger.info("onboard created {0}".format(profile.onboard))
        # if doj:
        #     profile.date_of_joining = doj
        if onboard and onboard.salary is None:
            onboard.salary = Salary.objects.filter(profile=profile).first()
            onboard.save()
        profile.dob = candidate.dob
        profile.full_name = candidate.full_name
        profile.first_name = candidate.first_name
        profile.middle_name = candidate.middle_name
        profile.last_name = candidate.last_name
        profile.email = email
        profile.save()
        erf.profiles.add(profile)
        if settings.ENABLE_QMS3_INTEGRATION and check_server_status(settings.QMS3_URL):
            update_profile_in_qms3(profile.emp_id)
        return HttpResponse(json.dumps({"message": "onboard details updated"}))
    except Exception as e:
        logger.info("emp_id {0}".format(emp_id))
        logger.info(f"data= {data}")
        logger.info("exception at upload_onboard_details {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def archive_candidate(request, cd_id):
    try:
        candidate = get_candidate_info_by_id(cd_id)
        data = request.data
        is_inactive = data.get("is_inactive")
        if is_inactive is None or is_inactive == "":
            raise ValueError("Please provide candidate status")
        if is_inactive:
            if candidate.status not in ["Selected For Onboarding", "Onboard"]:
                raise ValueError("You can only archive Selected candidates.")
            candidate.is_inactive = True
            candidate.save()
            return HttpResponse(json.dumps({"message": "Candidate is set to Inactive."}))
        if not candidate.is_inactive == True:
            raise ValueError("You can only un-archive Inactive candidates.")
        try:
            check_erf_status_required_hc(candidate.current_application.position_applied, request.user,
                                         interview_rounds_stage=True)
        except Exception as e:
            raise ValueError(
                "Candidate cannot be made active with the associated erf for the following reason {0}".format(str(e)))
        candidate.is_inactive = False
        candidate.save()
        return HttpResponse(json.dumps({"message": "Candidate is set to Selected for Onboarding."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_already_onboarded_candidate_status(request, op_id):
    try:
        appointment_letter = OfferAppointmentLetter.objects.filter(id=op_id).last()
        candidate = appointment_letter.candidate
        onboard = Onboard.objects.filter(candidate=candidate).last()
        if onboard:
            candidate.status = "Onboard"
            onboard.appointment_letter = appointment_letter
            onboard.date_of_joining = appointment_letter.date_of_joining
            if appointment_letter.date_of_joining is None:
                raise ValueError("Please provide valid date of joining")
            onboard.salary = appointment_letter.salary
            onboard.onboard_status = True
            onboard.save()
            candidate.save()
        return HttpResponse(json.dumps({"message": "Candidate status has been changed to onboard."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)
