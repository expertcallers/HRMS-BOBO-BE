import base64
import io
import logging
import re
import hashlib
import traceback
import uuid

import pyotp
import qrcode
from django.core.mail import EmailMessage
from rest_framework.mixins import ListModelMixin

from ams.serializers import CreateAttendanceScheduleSerializer
from erf.models import ERFHistory
from hrms import settings

from rest_framework import authentication, permissions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError, NotAcceptable
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework.authtoken.models import Token
from rest_framework.permissions import BasePermission, IsAuthenticated

from rest_framework.generics import GenericAPIView
from django.db.models import Q, Sum
from datetime import date, datetime, timedelta
import json

from ams.models import LeaveBalance, Attendance, Schedule, Leave, AttendanceCorrectionHistory, LeaveBalanceHistory, \
    MonthlyLeaveBalance
from hrms.settings import BRANCH_CHOICES
from interview.serializers import CandidateOTPTestSerializer
from mapping.models import Profile, Department, Designation, HrmsPermissionGroup, \
    ExceptionLog, Miscellaneous, EmployeeReferral, Category, Mapping, HrmsDeptPermissionGroup, MiscellaneousMiniFields, \
    UpdateEmployeeHistory, EmployeePermissions, MappedTeams, Document, PermissionsToBeRemoved, LoginOtp
from mapping.serializer import CreateProfileSerializer, HrmsGroupSerializer, GetAllProfileSerializer, \
    CreateEmployeeReferral, GetEmployeeReferralSerializer, UpdateEmployeeReferralSerializer, \
    EmployeeRefListSerializer, CreateDesignationSerializer, CreateProcessSerializer, CreateMappingSerializer, \
    GetAllMappingSerializer, ApproveMappingSerializer, UpdateEmployeeSerializer, QMSProfileSerializer, \
    GetBirthdaySerializer, LoginOtpSerializer
from team.models import Team, Process
from utils.util_classes import CustomTokenAuthentication
from utils.utils import hash_value, return_error_response, unhash_value, update_request, get_sort_and_filter_by_cols, \
    get_emp_by_emp_id, get_last_day_of_cur_month_and_first_day_of_next_month, get_team_ids, \
    get_start_date_end_date_week_offs_start_end_time, update_schedule, update_my_team, update_leave_balance, \
    create_att_list_upd_list_sch_list, create_mapped_teams, get_formatted_name, create_profile_in_qms, get_full_name, \
    update_profile_in_qms, parse_boolean_value, get_my_team, get_all_managers_include_emp, check_for_60th_day, tz, \
    check_server_status, get_limited_breaks, get_careers_email_message, send_email_message, update_profile_in_qms3
from interview.models import GENDER_CHOICES, QUALF_CHOICES, CANDIDATE_STATUS_CHOICES, SOURCE_CHOICES, LANG_CHOICES, \
    FieldsOfExperience, CandidateOTPTest
from asset.models import AssetCategory

logger = logging.getLogger(__name__)


def get_user_response(token, profile):
    user_id = hash_value(profile.id, 'user')
    # if profile.first_name is None or str(profile.first_name).strip() == "":
    #     raise ValueError("first-name cannot be empty, Please contact admin")
    return {'token': token.key,
            "user": {
                "name": profile.full_name,
                # "id": user_id,
                'base_team': profile.team.base_team.name if profile.team and profile.team.base_team else None,
                'team': profile.team.name if profile.team else None,
                'my_team': get_my_team(profile),
                "gender": profile.onboard.gender if profile.onboard else None,
                'emp_id': profile.username,
                'designation': profile.designation.name,
                'doj': str(profile.date_of_joining),
                "department": profile.designation.department.id if profile.designation.department else None,
                "department_name": profile.designation.department.dept_id if profile.designation.department else None,
                # "category": profile.designation.category,
                "profile_image": settings.MEDIA_URL + str(profile.image) if profile.image else ""}}


class CheckVersionPermission(BasePermission):
    """
    Allows access only to permitted users.
    """

    def has_permission(self, request, view):
        version = request.META.get("HTTP_X_VERSION")
        if settings.FRONT_END_VERSION != version:
            raise NotAcceptable({"error": "Refresh the browser"})
        return True
        # raise ValidationError({"error": "You do not have permissions"})


class HasUrlPermission(BasePermission):
    """
    Allows access only to permitted users.
    """

    def has_permission(self, request, view):
        usr = request.user
        view_name = request.resolver_match.view_name

        group_permissions = HrmsPermissionGroup.objects.filter(category=usr.designation.category)
        emp_permissions = EmployeePermissions.objects.filter(profile=usr).last()
        dept_perms = HrmsDeptPermissionGroup.objects.filter(department=usr.designation.department).last()

        perm = []
        for gperm in group_permissions:
            perm += [i.url_name for i in gperm.permissions.all()] if gperm else []
        dept_perm = [i.url_name for i in dept_perms.permissions.all()] if dept_perms else []
        emp_perm = [i.url_name for i in emp_permissions.permissions.all()] if emp_permissions else []

        perm = list(set(perm + dept_perm + emp_perm))
        if view_name in perm:
            return True
        else:
            raise ValidationError({"error": "You do not have permissions"})


@api_view(["POST"])
def send_login_email_otp(request):
    try:
        email = request.data.get('email').lower() if request.data.get('email') else None
        emp_id = request.data.get('emp_id')
        existing_login_otp = LoginOtp.objects.filter(emp_id=emp_id, is_email_verified=True).last()

        if not existing_login_otp:
            if email is None:
                raise ValueError("Email is Required")
            emp_otp_obj = LoginOtp.objects.filter(email=email).first()
            if emp_otp_obj and emp_otp_obj.is_email_verified and emp_otp_obj.emp_id != emp_id:
                raise ValueError(
                    f"You cannot use this email,  {email} is already linked with emp_id {emp_otp_obj.emp_id}")
        else:
            email = existing_login_otp.email
        if settings.DEBUG and re.search(settings.DEV_EMAIL_OTP_PATTERN, email):
            hash_val = '123456'
        else:
            hash_val = str(hashlib.shake_256((email + str(uuid.uuid4())).encode("utf-8")).hexdigest(3)).upper()

        data = {'otp': hash_val,
                'email': email,
                'emp_id': emp_id,
                'otp_datetime': tz.localize(datetime.now())}
        serializer = LoginOtpSerializer(data=data)
        if not serializer.is_valid():
            return_error_response(serializer, raise_exception=True)
        logger.info("came to send email")
        if not (settings.DEBUG and re.search(settings.DEV_EMAIL_OTP_PATTERN, email)):
            logger.info("sending email...")
            subject = "Otp to employee login"
            email_template = "Please use otp {0} for ECPL HRMS employee login".format(hash_val)
            email_msg = get_careers_email_message(subject, email_template, to=[email], reply_to=[])
            send_email_message(email_msg)

        cnd_otp_obj, created = LoginOtp.objects.update_or_create(email=email, emp_id=emp_id,
                                                                 defaults=data)
    except Exception as e:
        logger.info("exception at send_login_email_otp {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)

    logger.info("otp {0} created for email {1}".format(hash_val, email))
    return HttpResponse(json.dumps({"message": "Otp is sent check email"}))


def verify_emp_email_otp_info(request, emp_otp_obj):
    otp = request.data.get('email_otp') or None
    emp_id = request.data.get("username")

    if otp is None:
        raise ValueError("email-otp is Required")
    if otp != emp_otp_obj.otp:
        raise ValueError("Invalid otp is entered")
    if emp_otp_obj.emp_id != emp_id:
        raise ValueError(
            f"You cannot use this email,  {emp_otp_obj.email} is already linked with emp_id {emp_otp_obj.emp_id}")

    if emp_otp_obj is None:
        raise ValueError("Invalid otp/email data, request for otp verification again")
    one_minutes_earlier = datetime.now() - timedelta(minutes=1)
    if tz.localize(one_minutes_earlier) > emp_otp_obj.otp_datetime:
        raise ValueError("The OTP is expired, please request for new one")
    if not emp_otp_obj.is_email_verified:
        emp_otp_obj.is_email_verified = True
        emp_otp_obj.save()
        all_logins = LoginOtp.objects.filter(emp_id=emp_otp_obj.emp_id)
        if all_logins.count() > 1:
            all_logins.exclude(email=emp_otp_obj.email).delete()


class LoginUserView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        "error": "Invalid employee ID or password. Contact your reporting manager to reset your password.", },
                    status=status.HTTP_400_BAD_REQUEST)  # ECPL

            profile = serializer.validated_data['user']      
            is_policy_accepted = parse_boolean_value(request.data.get("policy_accepted"))
            if not profile.is_password_changed:
                return Response(
                    {"error": "Please reset your password", "action": "reset_password"},
                    status=status.HTTP_406_NOT_ACCEPTABLE)
            # if not profile.policy_accepted:
            #     if not is_policy_accepted:
            #         return Response(
            #             {"error": "Please accept the HRMS user guidelines to continue", "action": "accept_policy"},
            #             status=status.HTTP_406_NOT_ACCEPTABLE)
            #     else:
            #         profile.policy_accepted = True
            if not datetime.now().date() >= profile.date_of_joining:
                return Response(
                    {"error": f"Your can not login as your date-of-joining is {str(profile.date_of_joining)}"},
                    status=status.HTTP_400_BAD_REQUEST)
            email_otp = request.data.get("email_otp")
            user_totp = request.data.get("totp_token")
            login_otp = LoginOtp.objects.filter(emp_id=profile.emp_id).order_by('otp_datetime').last()
            email_exists = login_otp.is_email_verified if login_otp else None
            if settings.ENABLE_TOTP:
                if not email_otp:
                    if (not profile.otp_secret or not profile.last_totp) and not user_totp:
                        profile.otp_secret = pyotp.random_base32()
                        logger.info(f"otpsecret {profile.otp_secret}")
                        otp = pyotp.TOTP(profile.otp_secret)
                        provisioning_uri = otp.provisioning_uri(name=profile.username, issuer_name="ECPL HRMS")

                        # Generate QR code
                        qr = qrcode.make(provisioning_uri)
                        qr_code_io = io.BytesIO()
                        qr.save(qr_code_io, format='PNG')
                        qr_code_io.seek(0)
                        profile.last_totp = None
                        profile.save()

                        return Response({
                            "email_exists": email_exists,
                            "existing_email": login_otp.email if email_exists else None,
                            "action": "requires_totp",
                            'qr_code_url': 'data:image/png;base64,' + base64.b64encode(qr_code_io.getvalue()).decode(
                                'utf-8'),
                            'provisioning_uri': provisioning_uri
                        }, status=status.HTTP_406_NOT_ACCEPTABLE)
                    elif user_totp:
                        totp = pyotp.TOTP(profile.otp_secret)
                        if not totp.verify(user_totp):
                            return Response(
                                {'error': "Invalid otp provided", "action": "requires_totp",
                                 "email_exists": email_exists,
                                 "existing_email": login_otp.email if email_exists else None,
                                 },
                                status=status.HTTP_406_NOT_ACCEPTABLE)
                        profile.last_totp = user_totp
                        # logger.info(f"totp {totp}")
                    else:
                        return Response({"error": "Please provide otp information", "action": "requires_totp",
                                         "existing_email": login_otp.email if email_exists else None,
                                         "email_exists": email_exists},
                                        status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    verify_emp_email_otp_info(request, login_otp)
            token, created = Token.objects.get_or_create(user=profile)
            profile.last_login = tz.localize(datetime.now())
            profile.last_activity_at = tz.localize(datetime.now())
            profile.save()
            return Response(get_user_response(token, profile))
        except Exception as e:
            logger.info("exception at LoginUserView {0}".format(traceback.format_exc(5)))
            return Response({"error": f"{str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def reset_user_password(request):
    try:
        profile = request.user
        new_password = request.data.get('new_password')
        old_password = request.data.get('password')
        if not old_password:
            raise ValueError("please provide old password")
        if not profile.check_password(old_password):
            raise ValueError("Please provide your valid current password")

        if new_password is None or len(new_password) < 8:
            raise ValueError("please provide new_password of size greater than or equal to 8")
        if profile.check_password(new_password):
            raise ValueError("old password and new passwords are same")

        profile.is_password_changed = True
        profile.set_password(new_password)
        profile.save()
    except Exception as e:
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "User password reset is successful"})


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def clear_mfa_passkeys(request):
    try:
        emp_ids = request.data.get("emp_ids", [])
        profiles = Profile.objects.filter(emp_id__in=emp_ids)
        if profiles.count() > 0:
            profiles.update(otp_secret=None)
        return Response({"message": "Passkeys removed successfully"})
    except Exception as e:
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


class Logout(ObtainAuthToken):
    """Logout for an existing user"""

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponse(json.dumps({"error": "User is unauthorised"}), status=status.HTTP_401_UNAUTHORIZED)
        request.user.auth_token.delete()
        return HttpResponse(json.dumps({"message": "User is logged out"}), status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def user_image(request):
    img = request.FILES.get("image")
    profile = request.user
    profile.image.delete()
    profile.image = img
    profile.save()
    return HttpResponse(
        json.dumps({"message": "Profile photo updated", "profile_image": settings.MEDIA_URL + str(profile.image),
                    'status': status.HTTP_200_OK}))


@api_view(['DELETE'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def remove_profile_image(request):
    profile = request.user
    if profile.image:
        profile.image.delete()
    return HttpResponse(json.dumps({'status': status.HTTP_200_OK}))


def update_employee_reference(profile):
    if not profile.onboard:
        return
    cur_app = profile.onboard.candidate.current_application
    if cur_app.source != "Referral":
        return
    try:
        emp_ref = EmployeeReferral.objects.get(id=cur_app.source_ref)
        emp_ref.referred_emp = profile
        emp_ref.status = "Employee"
        emp_ref.save()

    except Exception as e:
        logger.info(
            "Contact tech team candidate source is Referral but source_ref = {0} is invalid application id = {1}".format(
                cur_app.source_ref, cur_app.id))


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_employee(request, ob_id):
    try:
        usr = request.user
        from onboarding.views import get_onboard_by_id
        onboard, ob_id = get_onboard_by_id(ob_id)
        if onboard.onboarded_by is None:
            raise ValueError("Candidate need to be verified by HR")
        date_now=tz.localize(datetime.now())
        if onboard and not onboard.onboard_status:
            profile = Profile.objects.filter(onboard=onboard).exclude(status="Attrition").last()
            if profile:
                raise ValueError("Profile already exists for this candidate")
            else:
                raise ValueError("The onboard status need to be changed for employee creation")

        erf = onboard.candidate.current_application.position_applied
        if not erf.is_erf_open:
            raise ValueError("This erf is closed, closed_on={0}".format(str(erf.closure_date)))

        is_training = bool(json.loads(request.data.get("is_training", "false")))

        # from django.db import connection
        # cursor = connection.cursor()
        # try:
        #     # for postgresql
        #     cursor.execute("SELECT MAX(CAST(CASE WHEN username ~ '^\d+$' THEN username END AS INTEGER)) FROM profile")
        # except Exception as e:
        #     cursor.execute('select max(username-0) from profile')  # sqlite

        # results = cursor.fetchall()
        # last_emp_id = 1
        # for result in results:
        #     for i in result:
        #         last_emp_id = i
        # new_emp_id = int(last_emp_id) + 1
        # ECPL
        new_emp_id = request.data.get("emp_id")
        if new_emp_id is None or str(new_emp_id).strip() == "":
            raise ValueError("Please provide the emp-id")
        new_emp_id = str(new_emp_id).strip()
        existing_profile = Profile.objects.filter(emp_id=new_emp_id).last()
        if existing_profile:
            raise ValueError("Employee with this emp-id already exists")
        first_name = onboard.candidate.first_name if onboard else "user" + str(new_emp_id)
        middle_name = onboard.candidate.middle_name if onboard else ""
        last_name = onboard.candidate.last_name if onboard else ""
        joining_date = onboard.date_of_joining
        if joining_date is None:
            raise ValueError("Please update the date of joining in the onboard details")

        data = update_request(request.data, first_name=first_name, middle_name=middle_name, last_name=last_name,
                              designation=erf.designation.id, emp_id=new_emp_id,
                              username=new_emp_id, onboard=ob_id, email=onboard.candidate.email,
                              date_of_joining=joining_date, dob=onboard.candidate.dob,
                              full_name=onboard.candidate.full_name)
        serializer = CreateProfileSerializer(data=data)
        if not serializer.is_valid():
            return_error_response(serializer, raise_exception=True)

        start_date, end_date, week_offs, start_time, end_time = get_start_date_end_date_week_offs_start_end_time(
            CreateAttendanceScheduleSerializer, request)
        if start_date < joining_date or end_date < joining_date:
            raise ValueError("Start-date and end-date should be greater than or equal to joining date")

        check_for_60th_day(end_date)
        profile = serializer.create(serializer.validated_data)
        profile.onboard = onboard
        profile.set_password(str(settings.PASS_PREFIX) + str(new_emp_id))
        if erf:
            erf.profiles.add(profile)
            if not erf.always_open and erf.profiles.count() >= erf.hc_req:
                erf.closed_by = usr
                erf.closure_date = datetime.today().date()
                erf.is_erf_open = False
                erf.save()

        if onboard:
            onboard.onboard_status = False
            onboard.candidate.status = "Active"
            onboard.candidate.is_employee = True
            onboard.salary.profile = profile
            onboard.salary.save()
            onboard.candidate.save()
            if onboard.appointment_letter:
                onboard.appointment_letter.date_of_joining = onboard.date_of_joining
                onboard.appointment_letter.save()
            onboard.save()
            #Adding sl for <=15 date joining emps
        if joining_date.day <=15:
            LeaveBalance.objects.create(sick_leaves=1, paid_leaves=0, total=1, profile=profile)
            LeaveBalanceHistory.objects.create(profile=profile, date=date_now, leave_type="SL",
                                pl_balance=0,
                                sl_balance=1, transaction="Leaves Earned", no_of_days=1,
                                total=1)
            MonthlyLeaveBalance.objects.create(profile=profile, date=date_now, leave_type="SL",
                                transaction="Leaves Earned", no_of_days=1,
                                total=1)

        else:
            LeaveBalance.objects.create(sick_leaves=0, paid_leaves=0, total=0, profile=profile)

        objs = []
        profile.save()
        att_list = []
        att_up_list = []
        sch_list = []
        att_list, att_up_list, sch_list = update_schedule(
            Attendance, usr, profile, start_date, end_date, week_offs, start_time, end_time,
            "new employee creation schedule", is_training, Schedule, joining_date=joining_date, att_list=att_list,
            att_up_list=att_up_list, sch_list=sch_list, create_type="PC")
        message = create_att_list_upd_list_sch_list(Attendance, Schedule, att_list, att_up_list, sch_list)

        # last_day = (datetime.today().replace(day=28) + timedelta(days=10)).replace(day=1) - timedelta(days=1)
        #
        # for day in range(datetime.today().day, last_day.day + 1):
        #     objs.append(Attendance(status="Scheduled", date=date(last_day.year, last_day.month, day), profile=profile))
        # Attendance.objects.bulk_create(objs)
        update_employee_reference(profile)
        if erf:
            _ = ERFHistory.objects.create(erf=erf, profile=profile, status="Linked", added_or_removed_by=usr)
        if check_server_status(settings.QMS_URL):
            create_profile_in_qms(profile.emp_id)
        if settings.ENABLE_QMS3_INTEGRATION and check_server_status(settings.QMS3_URL):
            update_profile_in_qms3(profile.emp_id)

        if profile.onboard and profile.onboard.candidate and profile.onboard.candidate.cab_address:
            profile.onboard.candidate.cab_address.employee = profile
            profile.onboard.candidate.cab_address.save()
        profile = CreateProfileSerializer(profile).data
        return HttpResponse(json.dumps(profile))

    except Exception as e:
        logger.info("exception ={0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": "{0}".format(str(e))}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def get_id_value(request, id_val, name):
    return HttpResponse(json.dumps({"result:": unhash_value(id_val, name)}))


@api_view(['GET'])
def get_pre_defined(request):
    is_authenticated = request.user.is_authenticated
    gender = [i[0] for i in GENDER_CHOICES]
    qualf = [i[0] for i in QUALF_CHOICES]
    source = [i[0] for i in SOURCE_CHOICES]
    branch = [i[0] for i in BRANCH_CHOICES]
    lang = LANG_CHOICES

    fieldsofexperience = list(
        FieldsOfExperience.objects.values_list("category", "subcategory", named=True).order_by('id'))
    fields_of_experience = {}
    # {label: 'Human Resources', options: [{value: 'Vanilla', label: 'Vanilla'}]},
    for field in fieldsofexperience:
        if field[0] in fields_of_experience:
            fields_of_experience[field[0]].append(field[1])
        else:
            fields_of_experience[field[0]] = [field[1]]
    foe_list = []
    for key, value in fields_of_experience.items():
        foe = {'label': key, 'options': []}
        for val in value:
            foe['options'].append({"value": val, "label": val})
        foe_list.append(foe)
    departments = list(
        Department.objects.values_list("id", "name", named=True).exclude(name='other').order_by('id'))

    designations = list(Designation.objects.values_list("name", flat=True).order_by('id').distinct())
    response_data = {"gender": gender, "qa_type": settings.QUESTION_TYPE, "qualf": qualf, "source": source,
                     "lang": lang, "fields_of_experience": foe_list, "branch": branch, "designations": designations,
                     "source_readonly": settings.SOURCE_READ_ONLY, "departments": departments}

    if is_authenticated:
        # TODO send data based on the designation
        profile = request.user
        candidate = profile.onboard.candidate if profile.onboard and profile.onboard.prmnt_zip_code else None

        # po_billing_office = MiscellaneousMiniFields.objects.filter(field="po_billing_office").first()
        # response_data["po_billing_office"] = po_billing_office.content if po_billing_office else "HBR Office"
        desi = request.user.designation
        ticketing_departments = list(
            Department.objects.filter(allow_ticketing=True).values_list("id", "name", named=True).exclude(
                name='other').order_by('id'))

        response_data["pop_up"] = {"message": "⚠️ Please fill the onboard information",
                                   "new_tab": False,
                                   "important": True,
                                   "link": "/hrms/settings?tab=employee-self-service"} if not candidate else None

        # response_data["pop_up"] = {"message": "⚠️ ECPL: Employee Satisfaction Survey 2024-2025",
        #                            "new_tab": False,
        #                            "important": True,
        #                            "link": "https://docs.google.com/forms/d/e/1FAIpQLSev6ROwWYmgjLLGKsZSANf-y17bCQO8NayE7rpye3vUgYKUCA/viewform"}

        # response_data["pop_up"] = {"message": "⚠️ Leave policy updated", "important": True, }
        is_appraisal_enabled = MiscellaneousMiniFields.objects.filter(field__iexact="is_appraisal_enabled").first()
        appraisal_last_date=MiscellaneousMiniFields.objects.filter(field__iexact="appraisal_last_date").first()
        response_data["is_appraisal_enabled"] = is_appraisal_enabled.yes_no if is_appraisal_enabled else None
        response_data["appraisal_last_date"]=appraisal_last_date.content
        response_data["article_categories"] = settings.ARTICLE_CATEGORIES
        response_data['ticketing_departments'] = ticketing_departments
        response_data["po_billing_office"] = "HBR Office"
        response_data["sop_status"] = settings.SOP_STATUS
        response_data["data_source"] = settings.DATA_SOURCE
        response_data["process_type"] = settings.PROCESS_TYPE
        response_data["hc_currency"] = settings.HC_CURRENCY
        response_data["hc_pricing_type"] = settings.HC_PRICING_TYPE
        response_data["ams_schedule_correction"] = settings.AMS_SCHEDULE_CORRECTION
        response_data["dept_id"] = desi.department.dept_id
        response_data["interview"] = request.user.interview
        response_data["category"] = list(
            Category.objects.values_list("id", "name", named=True).exclude(name="SuperUser").order_by('id'))
        response_data['process'] = list(Process.objects.values_list("name", flat=True).order_by('id'))
        response_data['candidate_status'] = [i[0] for i in CANDIDATE_STATUS_CHOICES]
        response_data['attendance_status'] = [i[0] for i in settings.ATTENDANCE_STATUS]
        response_data["readonly_attendance"] = settings.NOT_FOR_MARK_ATTENDANCE
        response_data["leave_types"] = [list(i) for i in settings.LEAVE_TYPES]
        response_data["leave_status"] = [i[0] for i in settings.LEAVE_STATUS]
        response_data["erf_history_status"] = settings.ERF_HISTORY_STATUS
        response_data["readonly_leave_status"] = settings.READ_ONLY_LEAVE_STATUS
        process_type_one = list(
            Miscellaneous.objects.filter(field="process_type_one").values_list("content", flat=True))
        response_data["process_type_one"] = [] if len(process_type_one) == 0 else [i.strip() for i in str(
            process_type_one[0]).split(",")]
        process_type_two = list(
            Miscellaneous.objects.filter(field="process_type_two").values_list("content", flat=True))
        response_data["process_type_two"] = [] if len(process_type_two) == 0 else [i.strip() for i in str(
            process_type_two[0]).split(",")]

        process_type_three = list(
            Miscellaneous.objects.filter(field="process_type_three").values_list("content", flat=True))
        response_data["process_type_three"] = [] if len(process_type_three) == 0 else [i.strip() for i in str(
            process_type_three[0]).split(",")]

        response_data["requisition_type"] = [i[0] for i in settings.REQUISITION_TYPE]
        response_data["type_of_working"] = [i[0] for i in settings.TYPE_OF_WORKING]
        response_data["shift_timing"] = [i[0] for i in settings.SHIFT_TIMING]
        response_data["erf_approval_status"] = [i[0] for i in settings.ERF_APPROVAL_STATUS]
        response_data["readonly_erf_approval_status"] = settings.READONLY_ERF_APPROVAL_STATUS
        response_data["employee_referral_status"] = settings.EMPLOYEE_REFERRAL_STATUS
        response_data["pay_grade_levels"] = settings.PAY_GRADE_LEVELS
        response_data["financial_years"] = settings.FINANCIAL_YEARS
        response_data["ijp_shift_timing"] = settings.IJP_SHIFT_TIMING
        response_data["ijp_candidate_status"] = settings.IJP_CANDIDATE_STATUS
        response_data["ams_correction_status"] = settings.AMS_CORRECTION_STATUS
        response_data["ams_correction_readonly_status"] = settings.AMS_CORRECTION_READ_ONLY_STATUS
        response_data["ams_att_cor_readonly_status"] = settings.AMS_MARK_ATT_CORRECTION_READ_ONLY_STATUS
        response_data["ams_mark_attendance_status"] = settings.MARK_ATTENDANCE_STATUS
        response_data["direct_mark_attendance_status"] = settings.DIRECT_ATTENDANCE_MARK_STATUS
        response_data["ams_mark_att_stat_non_hr_ro"] = settings.MARK_ATTENDANCE_NON_HR_READ_ONLY
        response_data["ams_mark_holiday"] = settings.AMS_MARK_HOLIDAY
        response_data["resignation_status"] = settings.RESIGNATION_STATUS
        response_data["read_only_resignation_status"] = settings.READ_ONLY_RESIGNATION_STATUS
        response_data["satisfaction_level"] = settings.SATISFACTION_LEVEL
        response_data["exit_feedback_rating"] = settings.EXIT_FEEDBACK_RATING
        response_data["exit_form_choices"] = settings.EXIT_FORM_CHOICES
        response_data["training_feedback_rating"] = settings.TRAINING_FEEDBACK_RATING
        response_data["age_80d"] = settings.AGE_80D
        exit_primary_reason = list(
            Miscellaneous.objects.filter(field='exit_primary_reason').values_list('content', flat=True))
        response_data['exit_primary_reason'] = [] if len(exit_primary_reason) == 0 else [i.strip() for i in str(
            exit_primary_reason[0]).split(",")]

        selection_criteria = list(
            Miscellaneous.objects.filter(field='selection_criteria').values_list('content', flat=True))
        response_data['selection_criteria'] = [] if len(selection_criteria) == 0 else [i.strip() for i in str(
            selection_criteria[0]).split(",")]

        selection_process = list(
            Miscellaneous.objects.filter(field='selection_process').values_list('content', flat=True))
        response_data['selection_process'] = [] if len(selection_process) == 0 else [i.strip() for i in str(
            selection_process[0]).split(",")]

        response_data["mapping_status"] = settings.MAPPING_STATUS
        response_data["profile_status"] = settings.PROFILE_STATUS
        response_data["readonly_profile_status"] = settings.READONLY_PROFILE_STATUS
        response_data["ticket_status"] = settings.TICKET_STATUS_CHOICES
        response_data["readonly_ticket_status"] = settings.READONLY_TICKET_STATUS_CHOICES
        response_data["ticket_priority"] = settings.TICKET_PRIORITY
        response_data["asset_category"] = list(AssetCategory.objects.values_list("name", flat=True))
        response_data["hard_disk_type"] = settings.HARD_DISK_TYPE
        response_data["asset_status"] = settings.ASSET_STATUS
        response_data["asset_allocation_status"] = settings.ASSET_ALLOCATION_CHOICES
        response_data["readonly_asset_status"] = settings.READONLY_ASSET_STATUS
        response_data["interview_test_status"] = settings.INTERVIEW_TEST_STATUS
        break_type_unlimited = list(
            MiscellaneousMiniFields.objects.filter(field='break_type_unlimited').values_list('content', flat=True))
        response_data['break_type_unlimited'] = [] if len(break_type_unlimited) == 0 else [i.strip() for i in str(
            break_type_unlimited[0]).split(",")]
        response_data['break_type_limited'] = get_limited_breaks()
        response_data["po_office_choices"] = settings.PO_OFFICE_CHOICES
        response_data["po_category"] = settings.PO_CATEGORY
        response_data["hc_status"] = settings.HEADCOUNT_STATUS_CHOICES
        response_data["hc_readonly_status"] = settings.HEADCOUNT_STATUS_READONLY_CHOICES
        response_data["change_mgmt_type"] = settings.CHANGE_MGMT_TYPE
        response_data["application_system"] = settings.APPLICATION_SYSTEM
        response_data["change_impact"] = settings.CHANGE_IMPACT
        response_data["device_name"] = settings.DEVICE_NAME
        response_data["change_mgmt_site"] = settings.CHANGE_SITE
        response_data["change_status"] = settings.CHANGE_STATUS
        response_data["appraisal_status"] = settings.APPRAISAL_STATUS
        response_data["tax_regime"] = settings.TAX_REGIME
        response_data["yes_no"] = settings.YES_NO
        response_data["salary_update_reason"] = settings.SALARY_UPDATE_REASON
        response_data["transport_approval_readonly_status"] = settings.TRANSPORT_APPROVAL_STATUS
        response_data["transport_approval_status"] = settings.TRANSPORT_APPROVAL_STATUS_ALL
    return Response(response_data)


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_permissions(request):
    usr = request.user
    category = usr.designation.category if usr.designation else None
    if category is None:
        return HttpResponse(json.dumps({"error": "category doesn't exist for this designation contact admin"}),
                            status=status.HTTP_404_NOT_FOUND)
    designation = request.user.designation

    emp_permissions = EmployeePermissions.objects.filter(profile=usr).last()
    group_permissions = HrmsPermissionGroup.objects.filter(category=designation.category)
    dept_perms = HrmsDeptPermissionGroup.objects.filter(department=designation.department).last()

    dept_perm = [i.url_name for i in dept_perms.permissions.all()] if dept_perms else []
    perm = []
    for gperm in group_permissions:
        perm += [i.url_name for i in gperm.permissions.all()] if gperm else []
    emp_perm = [i.url_name for i in emp_permissions.permissions.all()] if emp_permissions else []

    perm = list(set(perm + dept_perm + emp_perm))
    return HttpResponse(json.dumps({"permissions": perm}))


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_birthdays(request):
    today = datetime.today().date()
    # last_day, next_mon_1st_day = get_last_day_of_cur_month_and_first_day_of_next_month()
    # next_mon_days = list(range(1, today.day))
    # cur_mon_days = list(range(today.day, last_day.day + 1))

    # profile = Profile.objects.filter(status="Active").filter(
    #     Q(onboard__candidate__dob__month=today.month, onboard__candidate__dob__day__in=cur_mon_days) | Q(
    #         onboard__candidate__dob__month=next_mon_1st_day.month, onboard__candidate__dob__day__in=next_mon_days))
    profile = Profile.objects.filter(status="Active").filter(Q(dob__day=today.day) & Q(dob__month=today.month))
    data = GetBirthdaySerializer(profile, many=True).data
    return Response({"profile": data})


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_new_hires(request):
    today = datetime.today().date()
    new_hires = Profile.objects.filter(is_superuser=False, date_of_joining__lte=today).order_by("-date_of_joining")[:20]
    data = GetAllProfileSerializer(new_hires, many=True).data
    return Response({"profile": data})


@api_view(["POST"])
def send_email_otp_forgot_password(request):
    try:
        email = request.data.get('email') or None
        if email is None:
            raise ValueError("Email is Required")
        profile = Profile.objects.filter(email=email).first()
        if not profile:
            raise ValueError("User with this email id is not registered")
        if not profile.is_active:
            raise ValueError("User with this email is not active")
        hash_val = str(hashlib.shake_256((email + str(uuid.uuid4())).encode("utf-8")).hexdigest(3)).upper()
        subject = "Otp to Reset Password"
        email_template = "{0} is the otp generated by ECPL to reset the Employee password.".format(hash_val)
        email_msg = get_careers_email_message(subject, email_template, to=[email], reply_to=[])
        send_email_message(email_msg)

        data = {'verify_otp': hash_val, 'email': email}
        serializer = CandidateOTPTestSerializer(data=data)
        if not serializer.is_valid():
            return_error_response(serializer, raise_exception=True)
        pwd_otp, created = CandidateOTPTest.objects.update_or_create(email=email, defaults=data)
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)

    logger.info("otp {0} created for email {1}".format(hash_val, email))
    return HttpResponse(json.dumps({"message": "Otp is sent check email"}))


def verify_otp_forgot_password(request):
    otp = request.data.get('email_otp')
    email = request.data.get('email')
    if email is None or otp is None:
        raise ValueError("Email and otp is Required")
    try:
        cand_otp_obj = CandidateOTPTest.objects.filter(verify_otp=otp, email=email).first()
        if cand_otp_obj is None:
            raise ValueError("Invalid otp/email data, request for otp verification again")
        ninty_minutes_earlier = datetime.now() - timedelta(minutes=90)
        if tz.localize(ninty_minutes_earlier) > cand_otp_obj.updated_at:
            raise ValueError("The OTP is expired, please request for new one")
        return otp, email, cand_otp_obj
    except Exception as e:
        raise ValueError("Invalid otp/email data, request for otp verification again")


@api_view(["POST"])
def forgot_password(request):
    try:
        email = request.data.get("email")
        employee = Profile.objects.filter(email=email).first()
        if employee is None:
            raise ValueError("There is no employee with the given email ")

        otp, email, pwd_otp = verify_otp_forgot_password(request)
        password = request.data.get('password')
        if password is None or len(str(password)) < 8:
            raise ValueError("Please provide valid password of size greater than equal to 8")
        if employee.check_password(password):
            raise ValueError("Try another password as this password matches the Old Password!")
        employee.is_password_changed = True
        employee.set_password(password)
        employee.save()
        # pwd_otp.delete()
        return HttpResponse(json.dumps({"message": "Password is Reset."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def update_initial_password(request):
    try:
        emp_id = request.data.get("emp_id")
        employee = Profile.objects.get(emp_id=emp_id)
        if employee.is_password_changed:
            raise ValueError("Password for this Employee has already been changed.")
        password = request.data.get('password')
        if password is None or len(str(password)) < 8:
            raise ValueError("Please provide valid password of size greater than equal to 8")
        if employee.check_password(password):
            raise ValueError("Try another password as this password matches the Old Password!")
        employee.is_password_changed = True
        employee.set_password(password)
        employee.save()
        # pwd_otp.delete()
        return HttpResponse(json.dumps({"message": "Password is Reset."}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_exception_log(request):
    text_msg = request.data.get("message")
    action = "not logged"
    if text_msg:
        ExceptionLog.objects.create(message=text_msg)
        action = "logged"
    return HttpResponse(json.dumps({"message": "exception " + action}))


@api_view(['GET'])
# @authentication_classes([CustomTokenAuthentication])
# @permission_classes([IsAuthenticated])
def get_designations_by_dept(request):
    dept = request.GET.get("dept")
    designations = []
    processes = []
    department = None
    if dept:
        if str(dept).isdigit():
            department = Department.objects.filter(id=dept).last()
        else:
            department = Department.objects.filter(name__iexact=dept).last()

    if department:
        designations = list(
            Designation.objects.filter(department=department).values_list('name', flat=True))
        processes = list(
            Process.objects.filter(department=department, is_active=True).values_list('name', flat=True))

    return HttpResponse(json.dumps({"designations": designations, "process": processes}))


@api_view(['GET'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_open_employee_ref_count(request):
    ref_count = EmployeeReferral.objects.filter(is_open=True, status="Referred").count()
    return HttpResponse(json.dumps({"referrals_open": ref_count}))


def create_employee_referral(request, usr, ta_input, **kwargs):
    # th_months = datetime.now() - timedelta(days=91)
    created_by = request.user
    if not ta_input:
        email = request.data.get("email")
        email = email.lower() if email else None
        data = update_request(request.data, created_by=created_by.id, referred_by_emp=usr.id, email=email)
    else:
        data = update_request({}, referred_by_emp=usr.id, created_by=created_by.id, **kwargs)
    serializer = CreateEmployeeReferral(data=data)
    if not serializer.is_valid():
        return return_error_response(serializer)
    # serializer.validated_data['created_at'] = th_months
    phone_no = serializer.validated_data["phone_no"]
    email = serializer.validated_data["email"]
    emp = EmployeeReferral.objects.filter(Q(email=email) | Q(phone_no=phone_no))

    if len(emp) > 0:
        existing_candidate = emp.filter(is_open=True).last()
        if existing_candidate:
            raise ValueError(
                "Candidate is already referred by an employee {0}".format(existing_candidate.referred_by_emp.emp_id))

        existing_emp = emp.filter(is_open=False).filter(~Q(referred_emp=None))
        if len(existing_emp) > 0:
            existing_emp = existing_emp.latest('created_at')
            if existing_emp.referred_emp.status == "Active":
                raise ValueError("Employee already exists with this email/phone_no")

    _ = serializer.create(serializer.validated_data)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_employee_reference(request):
    try:
        usr = request.user
        create_employee_referral(request, usr, False)
        return HttpResponse(json.dumps({"message": "Employee referral created successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_emp_ref_by_ta(request, emp_id):
    try:
        from interview.views import get_candidate_info_by_id
        employee = get_emp_by_emp_id(emp_id)
        candidate_id = request.data.get("candidate_id")
        candidate = get_candidate_info_by_id(candidate_id)
        name = get_formatted_name(candidate)
        create_employee_referral(request, employee, True, name=name, phone_no=candidate.mobile, email=candidate.email)
        return HttpResponse(json.dumps({"message": "Employee referral created successfully"}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


class GetAllEmployeeReferences(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetEmployeeReferralSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"referred_by_emp": "referred_by_emp__emp_id", "referred_emp": "referred_emp__emp_id",
                       "referred_by_emp_name": "referred_by_emp__full_name",
                       "referred_emp_name": "referred_emp__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        self.queryset = EmployeeReferral.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(['POST'])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_emp_ref_status(request, emp_ref_id):
    try:
        try:
            emp = EmployeeReferral.objects.get(id=emp_ref_id)
        except Exception as e:
            return HttpResponse(json.dumps({"error": "Record not found"}), status=status.HTTP_404_NOT_FOUND)

        if not emp.is_open:
            raise ValueError("Record has already been closed")

        comment = request.data.get("comment")
        if comment is None:
            raise ValueError("Please provide the comment")
        serializer = UpdateEmployeeReferralSerializer(data=request.data)

        if not serializer.is_valid():
            return return_error_response(serializer)
        # logger.info(f"emp_serializer {serializer.validated_data}")

        if emp.referred_emp and serializer.validated_data.get("is_open"):
            raise ValueError("Cannot close this referral, as employee record has been created for this referral.")
        if "is_open" in serializer.validated_data.keys() and isinstance(serializer.validated_data["is_open"],
                                                                        bool) and not serializer.validated_data[
            "is_open"]:
            serializer.validated_data["closed_date"] = tz.localize(datetime.now())

        usr = request.user
        serializer.validated_data["updated_by"] = usr
        serializer.validated_data['comment'] = "Updated by {0}, {1}".format(usr.emp_id, comment)
        emp = serializer.update(emp, serializer.validated_data)
        return HttpResponse(json.dumps({"message": "Employee referral updated successfully"}))

    except Exception as e:
        logger.info(f"update_emp_ref_status POST {traceback.format_exc(5)}")
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_open_referrals(request):
    emp_ref = EmployeeReferral.objects.filter(is_open=True, status="Referred")
    referrals = EmployeeRefListSerializer(emp_ref, many=True).data
    return HttpResponse(json.dumps({"referrals": referrals}))


class GetMyEmployeeReferences(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetEmployeeReferralSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"referred_by_emp": "referred_by_emp__emp_id", "referred_emp": "referred_emp__emp_id",
                       "referred_by_emp_name": "referred_by_emp__full_name",
                       "referred_emp_name": "referred_emp__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        self.queryset = EmployeeReferral.objects.filter(referred_by_emp=request.user).filter(**filter_by).filter(
            search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


class GetMyTeamReferences(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GetEmployeeReferralSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        my_teams = get_team_ids(request.user)
        if my_teams is None:
            self.queryset = []
            return self.list(request, *args, **kwargs)

        map_columns = {"referred_by_emp": "referred_by_emp__emp_id", "referred_emp": "referred_emp__emp_id",
                       "referred_by_emp_name": "referred_by_emp__full_name",
                       "referred_emp_name": "referred_emp__full_name"}
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        self.queryset = EmployeeReferral.objects.filter(referred_by_emp__team__id__in=my_teams).filter(
            **filter_by).filter(search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_process(request):
    try:
        serializer = CreateProcessSerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["created_by"] = request.user
        _ = serializer.create(serializer.validated_data)
        return HttpResponse(json.dumps({}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_designation(request):
    try:
        serializer = CreateDesignationSerializer(data=request.data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        serializer.validated_data["created_by"] = request.user.emp_id
        _ = serializer.create(serializer.validated_data)
        return HttpResponse(json.dumps({}))
    except Exception as e:
        logger.info("exception at create_designation {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def get_from_team_to_team(request, employee):
    to_team = request.data.get('to_team')
    if to_team is None or not str(to_team).isdecimal():
        raise ValueError("please provide the to_team id")
    to_team = int(to_team)
    to_team_obj = Team.objects.filter(id=to_team).first()
    if to_team_obj is None:
        raise ValueError("Invalid to-team is provided")
    from_team = employee.team.id
    return from_team, to_team, to_team_obj


def check_pending_attendance_correction(employee):
    if AttendanceCorrectionHistory.objects.filter(attendance__profile=employee,
                                                  correction_status="Pending").count() > 0:
        raise ValueError("Employee's attendance corrections are pending")


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def create_mapping(request):
    try:
        usr = request.user
        employee = get_emp_by_emp_id(request.data.get('emp_id'))
        check_pending_attendance_correction(employee)
        from_team, to_team, _ = get_from_team_to_team(request, employee)
        if to_team == from_team:
            raise ValueError("Old team and New team are same")
        existing = Mapping.objects.filter(employee=employee.id, to_team=to_team, status="Pending")
        if existing:
            raise ValueError("Mapping for this Employee already requested.")
        data = update_request(request.data, employee=employee.id, from_team=from_team,
                              is_open=True, created_by=usr.id)
        serializer = CreateMappingSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        _ = serializer.create(serializer.validated_data)
        return HttpResponse(json.dumps({"message": "Mapping Employee done successfully"}))
    except Exception as e:
        logger.info("exception at create_designation {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def get_my_team_mapping_request_count(request):
    count = 0
    try:
        my_team = get_team_ids(request.user)
        if my_team:
            count = Mapping.objects.filter(to_team__in=my_team, is_open=True).count()
    except Exception as e:
        logger.info("exception at get_my_team_mapping_request_count {0}".format(traceback.format_exc(5)))
    return HttpResponse(json.dumps({"mapping_req_count": count}))


class GetMyTeamMappingRequests(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllMappingSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        usr = request.user
        map_columns = {"from_team": "from_team__name", "to_team": "to_team__name",
                       "employee_emp_id": "employee__emp_id",
                       "employee_name": "employee__full_name", "approved_by_emp_id": "approved_by__emp_id",
                       "approved_by_name": "approved_by__full_name",
                       "to_team_manager_emp_id": "to_team__manager__emp_id",
                       "to_team_manager_name": "to_team__manager__full_name",
                       "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name"
                       }
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        my_team = list(usr.my_team.all().values_list("id", flat=True))
        self.queryset = Mapping.objects.filter(to_team__in=my_team, is_open=True).filter(**filter_by).filter(
            search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


class GetMyTeamHistoryMapping(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllMappingSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        usr = request.user
        map_columns = {"from_team": "from_team__name", "to_team": "to_team__name",
                       "employee_emp_id": "employee__emp_id",
                       "employee_name": "employee__full_name", "approved_by_emp_id": "approved_by__emp_id",
                       "approved_by_name": "approved_by__full_name",
                       "to_team_manager_emp_id": "to_team__manager__emp_id",
                       "to_team_manager_name": "to_team__manager__full_name",
                       "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name"
                       }
        my_team = list(usr.my_team.all().values_list("id", flat=True))
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        self.queryset = Mapping.objects.filter(to_team__in=my_team).filter(**filter_by).filter(search_query).order_by(
            *order_by_cols)
        return self.list(request, *args, **kwargs)


class GetAllTeamMapping(ListModelMixin, GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated, HasUrlPermission]
    serializer_class = GetAllMappingSerializer
    model = serializer_class.Meta.model

    def get(self, request, *args, **kwargs):
        map_columns = {"from_team": "from_team__name", "to_team": "to_team__name",
                       "employee_emp_id": "employee__emp_id",
                       "employee_name": "employee__full_name", "approved_by_emp_id": "approved_by__emp_id",
                       "approved_by_name": "approved_by__full_name",
                       "to_team_manager_emp_id": "to_team__manager__emp_id",
                       "to_team_manager_name": "to_team__manager__full_name",
                       "created_by_emp_id": "created_by__emp_id", "created_by_name": "created_by__full_name"
                       }
        order_by_cols, search_query, filter_by = get_sort_and_filter_by_cols(request.GET, fields_look_up=map_columns)
        self.queryset = Mapping.objects.filter(**filter_by).filter(search_query).order_by(*order_by_cols)
        return self.list(request, *args, **kwargs)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def approve_mapping(request, mapping_id):
    try:
        usr = request.user
        try:
            mapping = Mapping.objects.get(id=mapping_id)
        except Exception as e:
            raise ValueError("Mapping record not found for the given mapping id")
        if not mapping.is_open:
            raise ValueError("This mapping is already closed")
        check_pending_attendance_correction(mapping.employee)
        data = update_request(request.data, approved_by=usr.id, is_open=False)
        serializer = ApproveMappingSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        if serializer.validated_data["status"] == "Approved":
            employee = mapping.employee
            team = employee.team
            if team.manager == employee:
                pass
            else:
                mapping.mapped_teams = create_mapped_teams(None, employee, team.manager,
                                                           "Team Mapping", usr)
                mapping.save()
            employee.team = mapping.to_team
            employee.save()
            update_my_team([employee.id, team.manager.id])
        serializer.update(mapping, serializer.validated_data)
        if settings.ENABLE_QMS_INTEGRATION and check_server_status(settings.QMS_URL):
            update_profile_in_qms(mapping.employee.emp_id)
        if settings.ENABLE_QMS3_INTEGRATION and check_server_status(settings.QMS3_URL):
            update_profile_in_qms3(mapping.employee.emp_id)
        return HttpResponse(json.dumps({"message": "Approve mapping employee done successfully"}))
    except Exception as e:
        logger.info("exception at approve_mapping {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def create_file(field, file, user=None):
    emp_id = user.emp_id if user else None
    name = get_formatted_name(user) if user else None
    document = Document(field=field, file=file, uploaded_by_emp_id=emp_id, uploaded_by_name=name, file_name=file.name)
    return document


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def update_employee(request, emp_id):
    try:
        profile = get_emp_by_emp_id(emp_id)
        usr = request.user
        data = request.data
        comment = data.get("comment")
        if profile.status == "Attrition":
            raise ValueError(
                "The employee is already in attrition, last-working-day is {0}".format(profile.last_working_day))
        desi = request.data.get("designation")
        dept = request.data.get("department")
        try:
            designation = Designation.objects.get(name=desi, department__id=dept)
        except Exception as e:
            raise ValueError("Designation not found")
        full_name = get_full_name(data)
        data = update_request(request.data, designation=designation.id, full_name=full_name)
        serializer = UpdateEmployeeSerializer(data=data)
        if not serializer.is_valid():
            return return_error_response(serializer)
        stat = serializer.validated_data.get('status')
        to_team = request.data.get('to_team')
        if stat == "Active" and to_team:
            from_team, to_team, _ = get_from_team_to_team(request, profile)
        if stat:
            if not comment:
                raise ValueError("Comment is required.")
            if stat not in ["Attrition", "Bench", "NCNS", "Active"]:
                raise ValueError("Invalid status selected")
            lwd = request.data.get("last_working_day")
            try:
                lwd = datetime.fromisoformat(lwd)
            except Exception as e:
                lwd = None

            if stat == "Attrition":
                if not lwd:
                    raise ValueError("Please provide valid Last Scheduled Day")
                # the input date is an effective date for the selected status
                profile.last_working_day = lwd - timedelta(days=1)
            else:
                if not lwd:
                    raise ValueError("Please provide effective date for {0}".format(stat))
                profile.last_working_day = None

            if stat == "Active":
                profile.is_active = True
                serializer.validated_data['last_working_day'] = None
            else:
                profile.is_active = False
            if profile.status != stat:
                mark_status = "Scheduled" if stat == "Active" else stat
                attendances = Attendance.objects.filter(profile=profile, date__gte=lwd)
                if stat != "Active":

                    leaves_count = attendances.filter(status="PL").count()
                    pending_leaves = Leave.objects.filter(profile=profile, status="Pending")
                    msg = f"making candidate to {stat}"
                    if pending_leaves.count() > 0:
                        pl_leave_count = pending_leaves.filter(leave_type="PL").aggregate(total=Sum("no_of_days"))[
                            "total"]
                        pl_leave_count = pl_leave_count if pl_leave_count else 0
                        leaves_count += pl_leave_count
                        sl_leave_count = pending_leaves.filter(leave_type="SL").aggregate(total=Sum("no_of_days"))[
                            "total"]
                        sl_leave_count = sl_leave_count if sl_leave_count else 0

                        if sl_leave_count > 0:
                            update_leave_balance(profile, msg, sl_leave_count, leave_type="SL")
                        pending_leaves.update(status="Rejected", reason=msg)
                    main_teams = Team.objects.filter(manager=profile)
                    if main_teams.count() > 0:
                        create_mapped_teams(main_teams, profile, profile.team.manager, f"Employee {stat}", usr)
                        update_my_team(get_all_managers_include_emp([profile]))
                    if leaves_count > 0:
                        update_leave_balance(profile, msg, leaves_count)
                attendances.update(status=mark_status)
                if mark_status == "Attrition":
                    serializer.validated_data['last_working_day'] = profile.last_working_day
                    last_date = profile.last_working_day
                    if attendances.count() > 0:
                        last_date = attendances.order_by("-date")[0].date
                    next_start_date = last_date + timedelta(days=1)
                    if last_date.month == next_start_date.month and last_date.year == next_start_date.year:
                        from ams.views import create_att_calender
                        last_day_of_month, first_day_of_next_month = get_last_day_of_cur_month_and_first_day_of_next_month(
                            input_date=next_start_date)
                        Attendance.objects.bulk_create(
                            create_att_calender(profile, [], next_start_date, last_day_of_month,
                                                att_status="Attrition"))
                    if profile.onboard and profile.onboard.candidate:
                        candidate = profile.onboard.candidate
                        candidate.status = "Attrition"
                        candidate.is_employee = False
                        candidate.save()
                        candidate.current_application.status = False
                        candidate.current_application.save()

        try:

            # Track Update History
            field_updated = []
            from_data = {}
            to_data = {}
            data = update_request(data, designation=designation,
                                  status=profile.status if stat == "" or stat is None else stat)
            update_employee_files = []
            files = request.FILES.getlist('documents')
            if files and type(files) == list:
                for i in files:
                    document = create_file('update_employee_attachment', i, user=usr)
                    if document:
                        update_employee_files.append(document)
            for field in data:
                if field in ["department", "to_team"]:
                    continue
                try:
                    from_field_data = str(getattr(profile, field))
                except Exception as e:
                    continue
                if field != "comment" and field != "documents" and not data.get(field) == from_field_data:
                    from_data[field] = from_field_data
                    to_data[field] = str(data.get(field))
                    field_updated.append(field)
            if stat == "Active" and to_team:
                from_team, to_team, to_team_obj = get_from_team_to_team(request, profile)
                from_data['team'] = profile.team.name
                to_data['team'] = to_team_obj.name
                field_updated.append('team')
                profile.team = to_team_obj

            history = UpdateEmployeeHistory.objects.create(profile=profile,
                                                           field_updated=", ".join(
                                                               str(i).strip() for i in field_updated),
                                                           updated_by=usr,
                                                           to_data=to_data, from_data=from_data,
                                                           comment=comment if comment else None)
            if len(update_employee_files) > 0:
                for doc in update_employee_files:
                    doc.history_id = history.id
                    doc.save()
                    history.attachment.add(doc)

            profile.save()
            profile = serializer.update(profile, serializer.validated_data)
            if settings.ENABLE_QMS_INTEGRATION and check_server_status(settings.QMS_URL):
                update_profile_in_qms(profile.emp_id)
            if settings.ENABLE_QMS3_INTEGRATION and check_server_status(settings.QMS3_URL):
                update_profile_in_qms3(profile.emp_id)
        except Exception as e:
            logger.info("exception at update_employee {0}".format(traceback.format_exc(5)))
            return HttpResponse(json.dumps({"error": "contact cc-team, Something went wrong {0}".format(str(e))}),
                                status=status.HTTP_400_BAD_REQUEST)

        return HttpResponse(json.dumps({"error": "Employee update is successful"}))
    except Exception as e:
        logger.info("exception at update_employee {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated, HasUrlPermission])
def reset_password_by_mgr(request, emp_id):
    try:
        usr = request.user
        my_team = get_team_ids(usr)
        if my_team is None:
            raise ValueError("You do not have any employees under you")
        # logger.info("my_team {0}".format(my_team))

        employee = get_emp_by_emp_id(emp_id)
        team_id = employee.team.id
        # logger.info("team_id{0}".format(team_id))

        if team_id not in my_team:
            raise ValueError("You are not the manager for this employee")
        password = request.data.get("pass")
        if password is None or password == "":
            raise ValueError("Please provide the valid password")
        employee.set_password(password)
        employee.save()
        return HttpResponse(json.dumps({"message": "Password update successful"}))
    except Exception as e:
        logger.info("exception at reset_password_by_mgr {0}".format(traceback.format_exc(5)))
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


def frontend_version(request):
    try:
        vers = settings.FRONT_END_VERSION
        return HttpResponse(json.dumps({"version": vers}))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
# @authentication_classes([CustomTokenAuthentication])
# @permission_classes([IsAuthenticated])
def get_all_profiles_for_pbi(request):
    try:
        profiles = Profile.objects.filter(is_superuser=0, team__isnull=False)
        profiles = QMSProfileSerializer(profiles, many=True).data
        return HttpResponse(json.dumps(profiles))
    except Exception as e:
        return HttpResponse(json.dumps({"error": str(e)}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([CustomTokenAuthentication])
@permission_classes([IsAuthenticated])
def remove_permissions(request):
    try:
        permissions_to_be_removed = PermissionsToBeRemoved.objects.all()
        removed_permissions = "No Changes Made"
        if permissions_to_be_removed.count() > 0:
            all_emp_perms = EmployeePermissions.objects.all()
            all_dept_perms = HrmsDeptPermissionGroup.objects.all()
            all_hrms_group_perms = HrmsPermissionGroup.objects.all()

            for to_be_removed in permissions_to_be_removed:
                permissions = to_be_removed.permissions.all()
                for perm in permissions:
                    if perm.url_name == "remove_permissions_cc_team_only":
                        continue
                    emp_perms = all_emp_perms.filter(permissions=perm)
                    for eperm in emp_perms:
                        removed_permissions = "Permissions removed"
                        eperm.permissions.remove(perm)
                    dept_perms = all_dept_perms.filter(permissions=perm)
                    for dperm in dept_perms:
                        removed_permissions = "Permissions removed"
                        dperm.permissions.remove(perm)
                    hrms_group_perms = all_hrms_group_perms.filter(permissions=perm)
                    for hperm in hrms_group_perms:
                        removed_permissions = "Permissions removed"
                        hperm.permissions.remove(perm)
        return Response({"message": removed_permissions})
    except Exception as e:
        logger.info("exception at remove_permissions {0}".format(traceback.format_exc(5)))
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
