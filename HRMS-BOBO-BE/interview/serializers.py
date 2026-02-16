from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from mapping.models import Profile, EmployeeReferral
from onboarding.models import OfferAppointmentLetter, Onboard, Salary
from transport.serializers import CabAddressDetailSerializer
from utils.utils import hash_value, unhash_value, form_module_url, get_formatted_name, get_decrypted_name, \
    get_candidate_interview_timing, get_formatted_choice, get_column_names_with_foreign_keys_separate, \
    get_decrypted_value, decrypt_salary_fields
from interview.models import Candidate, Interviewer, CandidateOTPTest, FieldsOfExperience, Application, Document, \
    InternApplication, InternQuestion, InternAnswer, InternPosition
import logging
from hrms import settings

logger = logging.getLogger(__name__)

highest_graduation = get_formatted_choice(settings.QUALF_CHOICES)
source_choice = get_formatted_choice(settings.SOURCE_CHOICES)
branch_choice = get_formatted_choice(settings.BRANCH_CHOICES)
gender_choice = get_formatted_choice(settings.GENDER_CHOICES)


def form_document_url(doc_id):
    return form_module_url(doc_id, "interview")


def get_path_and_name_dict(obj):
    if not obj:
        return None
    return {"path": form_document_url(obj.id), "name": obj.file.name.split("/")[::-1][0]}


class UpdateInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interviewer
        fields = ['feedback', 'status', 'total_rounds', 'to_department']


class CreateInterviewerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interviewer
        fields = "__all__"
        extra_kwargs = {
            'candidate': {'error_messages': {'required': 'Please enter the candidate id'}},
            'feedback': {'error_messages': {'required': 'Please provide the candidate feedback'}},
            'to_department': {'error_messages': {'required': 'Please select the to_department'}},
            'from_department': {'error_messages': {'required': 'Please select the from_department'}},
            'status': {'error_messages': {'required': 'Please select the status other than applied'}},
            'total_rounds': {'error_messages': {'required': 'Please provide the total rounds value'}},
        }

    def create(self, validated_data):
        # candidate_id is already decrypted
        interviewer = Interviewer.objects.create(**validated_data)
        return interviewer


class GetAllInterviewerSerializer(serializers.ModelSerializer):
    candidate_id = serializers.SerializerMethodField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["to_person_name"] = instance.to_person.full_name if instance.to_person else None
        data["to_person_id"] = instance.to_person.emp_id if instance.to_person else None
        data["interviewer_name"] = instance.interview_emp.full_name if instance.interview_emp else None
        data["interviewer_emp_id"] = instance.interview_emp.emp_id if instance.interview_emp else None
        data["job_position"] = instance.application.job_position
        return data

    class Meta:
        model = Interviewer
        exclude = (['candidate', "interview_emp"])

    def get_candidate_id(self, obj):
        return hash_value(obj.candidate.id, 'cd', mini=True)


def get_position_applied(pa):
    return str(pa.designation.name) + " #" + str(pa.id) if pa and pa.designation else None


def get_total_and_current_round(data, cur_app):
    interviewer = Interviewer.objects.filter(application=cur_app).latest('created_at')
    if data.get('source') == "Referral":
        try:
            emp_ref = EmployeeReferral.objects.get(id=cur_app.source_ref)
            data["source_ref"] = emp_ref.referred_by_emp.emp_id + " - " + emp_ref.referred_by_emp.full_name
        except Exception as e:
            data["source_ref"] = None

    data['total_rounds'] = interviewer.total_rounds
    data['current_round'] = interviewer.current_round
    return data


# class GetCandidateStatusSerializer(serializers.ModelSerializer):


class GetCandidateSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super(GetCandidateSerializer, self).to_representation(instance)
        cur_app = instance.current_application
        erf = cur_app.position_applied if cur_app and cur_app.position_applied else None
        data['id'] = hash_value(instance.id, 'cd')
        data['resume'] = get_path_and_name_dict(instance.resume)
        data['relieving_letter'] = get_path_and_name_dict(instance.relieving_letter)
        data['position_applied'] = get_position_applied(erf) if cur_app else None
        data["erf"] = erf.id if erf else None
        data["interviewer_name"] = cur_app.interviewer.full_name if cur_app and cur_app.interviewer else None
        data["interviewer_emp_id"] = cur_app.interviewer.emp_id if cur_app and cur_app.interviewer else None
        data["source"] = cur_app.source if cur_app else None
        data["source_ref"] = cur_app.source_ref if cur_app else None
        data["branch"] = cur_app.branch if cur_app else None
        data["job_position"] = cur_app.job_position if cur_app else None
        data["to_department"] = cur_app.to_department.name if cur_app and cur_app.to_department else None
        data["ta_rating"] = cur_app.ta_rating if cur_app else None
        data["ops_rating"] = cur_app.ops_rating if cur_app else None
        data["aadhaar_no"] = get_decrypted_name(instance.aadhaar_no)
        test = cur_app.test if cur_app else None
        not_rejected = True if instance.status != "Rejected" else False
        data["test_name"] = test.test_name if test and not_rejected else None
        data["test_id"] = test.id if test and not_rejected else None
        data["test_duration"] = test.duration if test and not_rejected else None
        cd_interview_timing = get_candidate_interview_timing(instance, cur_app, test) if test else None
        data["cd_int_timing"] = cd_interview_timing.id if cd_interview_timing else None
        data["test_status"] = cd_interview_timing.test_status if cd_interview_timing else None
        data["test_completed"] = cd_interview_timing.test_status != "Started" if cd_interview_timing else None
        data["cnd_test_start_time"] = str(cd_interview_timing.cnd_test_start_time) if cd_interview_timing else None
        data[
            "cnd_test_end_time"] = str(
            cd_interview_timing.cnd_test_end_time) if cd_interview_timing and cd_interview_timing.cnd_test_end_time else None
        data["test_duration"] = cd_interview_timing.test.duration if cd_interview_timing else data["test_duration"]
        data["total_ans_questions"] = cd_interview_timing.total_ans_questions if cd_interview_timing else None
        data["total_questions"] = cd_interview_timing.total_questions if cd_interview_timing else None
        data["total_score"] = cd_interview_timing.total_score if cd_interview_timing else None
        data["max_score"] = cd_interview_timing.max_score if cd_interview_timing else None
        data["result"] = cd_interview_timing.result if cd_interview_timing else None
        data["percentage"] = cd_interview_timing.percentage if cd_interview_timing else None
        data["pass_percent"] = test.pass_percent if test else None
        offer_app = OfferAppointmentLetter.objects.filter(candidate=instance,
                                                          application__status=True).exclude(Q(
            candidate__is_employee=True) | Q(
            candidate__is_inactive=True)).first() if instance.status in ['Selected For Onboarding', "Onboard"] else None
        data['is_appointment_letter_generated'] = True if offer_app and offer_app.appointment_letter else False
        data["is_offer_letter_accepted"] = offer_app.is_offer_letter_accepted if offer_app else None
        data[
            "transport_admin_app_rej_by_name"] = instance.transport_admin_app_rej_by.full_name if instance.transport_admin_app_rej_by else None
        data[
            "transport_admin_app_rej_by_emp_id"] = instance.transport_admin_app_rej_by.emp_id if instance.transport_admin_app_rej_by else None
        data["cab_address"] = CabAddressDetailSerializer(instance.cab_address) if instance.cab_address else None
        if cur_app:
            data = get_total_and_current_round(data, cur_app)
        return data

    class Meta:
        model = Candidate
        fields = "__all__"


class GetAllCandidateSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super(GetAllCandidateSerializer, self).to_representation(instance)
        cur_app = instance.current_application
        data['id'] = hash_value(instance.id, 'cd')
        data['resume'] = form_document_url(instance.resume.id) if instance.resume else None
        data[
            'position_applied'] = cur_app.position_applied.designation.name if cur_app.position_applied and cur_app.position_applied.designation else None
        data['to_department'] = cur_app.to_department.name
        data["interviewer_name"] = cur_app.interviewer.full_name if cur_app and cur_app.interviewer else None
        data["interviewer_emp_id"] = cur_app.interviewer.emp_id if cur_app and cur_app.interviewer else None
        data["job_position"] = cur_app.job_position
        data["aadhaar_no"] = get_decrypted_name(instance.aadhaar_no)
        data["branch"] = cur_app.branch
        data["erf_id"] = cur_app.position_applied.id if cur_app and cur_app.position_applied else None
        data[
            "process_name"] = cur_app.position_applied.process.name if cur_app and cur_app.position_applied and cur_app.position_applied.process else None
        data[
            "transport_admin_app_rej_by_name"] = instance.transport_admin_app_rej_by.full_name if instance.transport_admin_app_rej_by else None
        data[
            "transport_admin_app_rej_by_emp_id"] = instance.transport_admin_app_rej_by.emp_id if instance.transport_admin_app_rej_by else None

        return data

    class Meta:
        model = Candidate
        fields = (
            'status', 'id', "is_interview_completed", "last_interview_at", "gender", 'first_name', 'last_name',
            'middle_name', 'email', 'resume', 'created_at', "is_employee", 'updated_at', 'total_work_exp',
            'is_inactive', "full_name", "is_transport_required", "transport_approval_status","education_course",
            "highest_qualification","languages","transport_approval_comment","prev_comp_name","prev_comp_exp","current_ctc","expected_ctc",
            "fields_of_experience","dob","mobile","mobile_alt","email")


salary_cols, _, _ = get_column_names_with_foreign_keys_separate(Salary)
if 'id' in salary_cols:
    salary_cols.remove('id')


class GetAllSelectedForOnboardSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super(GetAllSelectedForOnboardSerializer, self).to_representation(instance)
        cur_app = instance.application
        candidate = instance.candidate
        data['is_appointment_letter_generated'] = False if instance.appointment_letter is None else True
        data['is_offer_letter_generated'] = False if instance.offer_letter is None else True
        data['candidate_id'] = hash_value(candidate.id, 'cd')
        data['full_name'] = candidate.full_name
        data['to_department'] = cur_app.to_department.name
        data["reviewed_by_emp_id"] = instance.reviewed_by.emp_id if instance.reviewed_by else None
        data["reviewed_by_name"] = instance.reviewed_by.full_name if instance.reviewed_by else None
        data["gender"] = candidate.gender
        onboard = Onboard.objects.filter(candidate=candidate).last()
        data["onboard_exists"] = onboard.id if onboard else None
        data["is_onboard_created"] = True if onboard else False
        data["mobile"] = candidate.mobile
        data["tmp_address_1"] = candidate.address_1
        data["tmp_address_2"] = candidate.address_2
        data["tmp_city"] = candidate.city
        data["tmp_state"] = candidate.state
        data["tmp_zip_code"] = candidate.zip_code
        data["aadhaar_no"] = get_decrypted_name(candidate.aadhaar_no)
        pos_app = cur_app.position_applied
        data['email'] = candidate.email
        data['position_applied'] = pos_app.designation.name if pos_app else None
        data["process"] = pos_app.process.name if pos_app else None
        data["department"] = pos_app.department.name if pos_app else None
        data["dob"] = candidate.dob
        data["erf_id"] = pos_app.id if pos_app else None
        data["transport_approval_status"] = candidate.transport_approval_status
        data = decrypt_salary_fields(data, salary_cols, instance.salary)
        return data

    class Meta:
        model = OfferAppointmentLetter
        exclude = ('reviewed_by', "candidate", "offer_letter", "appointment_letter")


class CreateCandidateSerializer(serializers.ModelSerializer):
    # gender = serializers.ChoiceField(choices=settings.GENDER_CHOICES,error_messages=[""])
    class Meta:
        model = Candidate
        exclude = (
            ['resume', 'relieving_letter', 'is_employee', "all_applications"])
        highest_graduation = ",".join(i[0] for i in settings.QUALF_CHOICES)
        qual_msg = f'Please provide values among these {highest_graduation}'

        extra_kwargs = {
            'first_name': {'error_messages': {'required': 'Please enter valid name'}},
            'last_name': {'error_messages': {'required': 'Please enter valid name'}},
            'email': {'error_messages': {'required': 'Please enter valid email'}},
            'mobile': {'error_messages': {'required': 'Please enter valid mobile'}},
            'address_1': {'error_messages': {'required': 'Please enter your address_1'}},
            'city': {'error_messages': {'required': 'Please enter your city'}},
            'state': {'error_messages': {'required': 'Please enter your state'}},
            'zip_code': {'error_messages': {'required': 'Please enter your zip_code'}},
            'dob': {'error_messages': {'required': 'Please enter your date of birth'}},

            'highest_qualification': {'error_messages': {'blank': qual_msg, 'null': qual_msg, 'invalid': qual_msg,
                                                         'required': qual_msg, "invalid_choice": qual_msg}},
            'gender': {'error_messages': {'required': 'Please provide your gender info'}},
            'current_ctc': {'error_messages': {
                'required': 'Please provide your current_ctc in lakhs per annum'}},
            'expected_ctc': {'error_messages': {
                'required': 'Please provide your expected_ctc in lakhs per annum'}},
            'prev_comp_exp': {'error_messages': {'required': 'Please enter your previous company experience'}},
            'prev_comp_name': {'error_messages': {'required': 'Please enter your previous company name'}},
            'aadhaar_no': {'error_messages': {'required': 'Please enter your valid aadhaar number'}},
            'is_transport_required': {'error_messages': {'required': 'Please provide transport info'}},
            'languages': {'error_messages': {'required': 'Please select the languages you know'}},
        }


class CreateApplicationSerializer(serializers.ModelSerializer):
    source = serializers.ChoiceField(choices=settings.SOURCE_CHOICES, error_messages={
        "invalid_choice": 'Accepted source info is "{0}"'.format(source_choice)})
    branch = serializers.ChoiceField(choices=settings.BRANCH_CHOICES, error_messages={
        "invalid_choice": 'Accepted branch info is "{0}"'.format(branch_choice)
    })

    class Meta:
        model = Application
        fields = ["job_position", "source", "candidate", "source_ref", "branch", "to_department", "position_applied"]


class UploadCreateApplicationSerializer(serializers.ModelSerializer):
    source = serializers.ChoiceField(choices=settings.SOURCE_CHOICES, error_messages={
        "invalid_choice": 'Accepted source info is "{0}"'.format(source_choice)}, allow_null=True, allow_blank=True)
    branch = serializers.ChoiceField(choices=settings.BRANCH_CHOICES, error_messages={
        "invalid_choice": 'Accepted branch info is "{0}"'.format(branch_choice)
    }, allow_null=True, allow_blank=True)

    class Meta:
        model = Application
        fields = ["job_position", "source", "source_ref", "branch", "to_department", "position_applied"]


class UpdateCandidateSerializer(CreateCandidateSerializer):
    gender = serializers.ChoiceField(choices=settings.GENDER_CHOICES,
                                     error_messages={
                                         'invalid_choice': 'Accepted gender info is "{0}".'.format(gender_choice)},
                                     allow_blank=True, allow_null=True)

    highest_qualification = serializers.ChoiceField(choices=settings.QUALF_CHOICES,
                                                    error_messages={
                                                        'invalid_choice': 'accepted highest qualification info is "{0}"'.format(
                                                            highest_graduation)}, allow_blank=True, allow_null=True)

    class Meta:
        model = Candidate
        exclude = ('is_employee', 'aadhaar_no', 'email')
        qual_msg = f'Please provide values among these {highest_graduation}'

        extra_kwargs = {
            'first_name': {'error_messages': {'required': 'Please enter valid name'}},
            'last_name': {'error_messages': {'required': 'Please enter valid name'}},
            'email': {'error_messages': {'required': 'Please enter valid email'}},
            'mobile': {'error_messages': {'required': 'Please enter valid mobile'}},
            'dob': {'error_messages': {'required': 'Please enter your date of birth'}},
            'gender': {'error_messages': {'required': 'Please provide your gender info'}},
            'highest_qualification': {'error_messages': {'blank': qual_msg, 'null': qual_msg, 'invalid': qual_msg,
                                                         'required': qual_msg, "invalid_choice": qual_msg}},
            'current_ctc': {'error_messages': {
                'required': 'Please provide your current_ctc in lakhs per annum'}},
            'expected_ctc': {'error_messages': {
                'required': 'Please provide your expected_ctc in lakhs per annum'}},
            'prev_comp_exp': {'error_messages': {'required': 'Please enter your previous company experience'}},
            'prev_comp_name': {'error_messages': {'required': 'Please enter your previous company name'}},
            'aadhaar_no': {'error_messages': {'required': 'Please enter your valid aadhaar number'}},
            'is_transport_required': {'error_messages': {'required': 'Please provide transport info'}},
            'languages': {'error_messages': {'required': 'Please select the languages you know'}},
        }


class CandidateOTPTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateOTPTest
        fields = "__all__"


class AddFieldsOfExpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldsOfExperience
        fields = ["category", "subcategory"]


class DocumentSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["path"] = form_document_url(instance.id)
        data["name"] = instance.file.name.split("/")[::-1][0]
        return data

    class Meta:
        model = Document
        exclude = ("field", "candidate_id", "file", "filehash")


class UpdateApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ["branch", "job_position", "source", "source_ref", ]


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternPosition
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternQuestion
        fields = ["id", "question_text"]


class AnswerSerilizer(serializers.ModelSerializer):
    class Meta:
        model = InternAnswer
        fields = "__all__"


class InternApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternApplication
        fields = "__all__"
