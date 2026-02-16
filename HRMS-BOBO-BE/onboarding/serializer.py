from rest_framework import serializers
import logging

import logging

from rest_framework import serializers

from hrms import settings
from onboarding.models import Onboard, OfferAppointmentLetter, Salary
from utils.utils import hash_value, form_module_url, get_decrypted_name, get_formatted_choice, \
    get_column_names_with_foreign_keys_separate, decrypt_salary_fields

logger = logging.getLogger(__name__)
pay_grade_choices = get_formatted_choice(settings.PAY_GRADE_LEVELS)


def form_document_url(doc_id):
    return form_module_url(doc_id, "onboard")


def get_path_and_name_dict(obj):
    if not obj:
        return None
    return {"path": form_document_url(obj.id), "name": obj.file.name.split("/")[::-1][0]}


salary_cols, _, _ = get_column_names_with_foreign_keys_separate(Salary)
if 'id' in salary_cols:
    salary_cols.remove('id')


class GetOnboardSerializer(serializers.ModelSerializer):
    def to_representation(self, obj):
        data = super(GetOnboardSerializer, self).to_representation(obj)
        data['first_name'] = obj.candidate.first_name
        data['middle_name'] = obj.candidate.middle_name
        data['last_name'] = obj.candidate.last_name
        data['full_name'] = obj.candidate.full_name
        data['email'] = obj.candidate.email
        data['id'] = obj.id
        data['pancard'] = get_path_and_name_dict(obj.pancard)
        data['copy_of_signed_offer_letter'] = get_path_and_name_dict(obj.copy_of_signed_offer_letter)
        data['copy_of_signed_nda'] = get_path_and_name_dict(obj.copy_of_signed_nda)
        data['aadhaar_card'] = get_path_and_name_dict(obj.aadhaar_card)
        data['photo'] = get_path_and_name_dict(obj.photo)
        data['candidate_id'] = hash_value(obj.candidate.id, 'cd')
        data['relieving_letters'] = [get_path_and_name_dict(i) for i in obj.relieving_letters.all()]
        data['education_documents'] = [get_path_and_name_dict(i) for i in obj.education_documents.all()]
        data['cheque_copy'] = get_path_and_name_dict(obj.cheque_copy)
        data['onboarded_by_emp_id'] = obj.onboarded_by.emp_id if obj.onboarded_by else None
        data['onboarded_by_name'] = obj.onboarded_by.full_name if obj.onboarded_by else None
        data["pan_no"] = get_decrypted_name(obj.pan_no)
        data["aadhaar_no"] = get_decrypted_name(obj.aadhaar_no) if obj.aadhaar_no else None
        erf = obj.appointment_letter.application.position_applied if obj.appointment_letter else None
        data["erf_id"] = erf.id if erf else None
        data["process"] = erf.process.name if erf and erf.process else None
        data = decrypt_salary_fields(data, salary_cols, obj.salary)
        return data

    class Meta:
        model = Onboard
        exclude = (['candidate', 'onboarded_by'])


class CreateOnboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Onboard
        exclude = ['copy_of_signed_nda', 'copy_of_signed_offer_letter', 'pancard', 'aadhaar_card',
                   'education_documents', 'relieving_letters', 'photo', 'cheque_copy', "candidate"]

        extra_kwargs = {
            'permanent_address': {'error_messages': {'required': 'Please provide the permanent address'}},
            'temporary_address': {'error_messages': {'required': 'Please provide the temporary address'}},
            'emergency_contact_1': {'error_messages': {'required': 'Please provide valid emergency contact-1'}},
            'emergency_contact_2': {'error_messages': {'required': 'Please provide valid emergency contact-2'}},
        }

    def create(self, validated_data):
        return Onboard.objects.create(**validated_data)


class PublicCreateOnboardSerializer(CreateOnboardSerializer):
    class Meta:
        model = Onboard
        exclude = ['copy_of_signed_nda', 'copy_of_signed_offer_letter', 'pancard', 'aadhaar_card',
                   'education_documents', 'relieving_letters', 'photo', 'cheque_copy', "candidate",
                   "is_all_doc_verified", "is_pan_verified", "is_aadhaar_verified",
                   "is_education_documents_verified", "is_relieving_letters_verified", "is_offer_letter_issued",
                   "onboard_status"]


class UpdateOnboardEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Onboard
        exclude = ['copy_of_signed_nda', 'copy_of_signed_offer_letter', 'pancard', 'aadhaar_card',
                   'education_documents', 'relieving_letters', 'photo', 'cheque_copy']
        read_only_fields = ['candidate']


class UpdateOnboardCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Onboard
        exclude = [
            'is_all_doc_verified', 'onboarded_by', 'copy_of_signed_nda', 'copy_of_signed_offer_letter',
            'pancard', 'aadhaar_card', 'education_documents', 'relieving_letters', 'photo', "cheque_copy"]


class AppointmentLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferAppointmentLetter
        fields = ["date_of_joining"]


class OfferLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferAppointmentLetter
        exclude = ("date_of_joining",)


class GetSalaryStructureSerializer(serializers.ModelSerializer):
    pay_grade = serializers.ChoiceField(choices=settings.PAY_GRADE_LEVELS,
                                        error_messages={
                                            "invalid_choice": 'accepted pay_grade info is "{0}"'.format(
                                                pay_grade_choices)})

    class Meta:
        model = Onboard
        fields = ['total_fixed_gross', 'pay_grade', 'opting_for_pf']

        extra_kwargs = {
            'total_fixed_gross': {'error_messages': {'required': "Please input the total_fixed_gross value"}},
            "pay_grade": {'error_messages': {'required': "please input the pay_grade data"}}
        }
