import logging
import uuid
from datetime import datetime

from django.core.validators import FileExtensionValidator
from django.db import models
import logging

from rest_framework.exceptions import ValidationError

from hrms import settings
from interview.models import Candidate, Application
from mapping.models import Profile
from payroll.models import Salary
from utils.utils import hash_value, validate_number_with_fixed_size, EncryptedCField, validate_current_century, \
    validate_mobile_no, validate_alphanumeric, validate_ifsc, validate_bnk_account_no, document_file
from django.db.models import UniqueConstraint, Func, F, Q

logger = logging.getLogger(__name__)


class Document(models.Model):
    field = models.CharField(max_length=255)
    onboard_id = models.CharField(max_length=20)
    file = models.FileField(upload_to=document_file,
                            validators=[
                                FileExtensionValidator(
                                    allowed_extensions=settings.DEFAULT_ALLOWED_EXTENSIONS)])
    file_name = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_emp_id = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_name = models.CharField(max_length=255, blank=True, null=True)
    filehash = models.CharField(max_length=32, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.file)


class OfferAppointmentLetter(models.Model):
    salary = models.ForeignKey(Salary, on_delete=models.SET_NULL, blank=True, null=True, related_name="offer_salary")
    reviewed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name="appointment_letter_profile")
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    offer_letter = models.ForeignKey(Document, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name="offer_letter")
    appointment_letter = models.ForeignKey(Document, on_delete=models.SET_NULL, blank=True, null=True,
                                           related_name="appointment_letter")
    is_offer_letter_accepted = models.BooleanField(default=False)
    spoc_name = models.CharField(max_length=255, blank=True, null=True)
    spoc_contact_no = models.CharField(max_length=10, validators=[validate_mobile_no], blank=True, null=True)
    branch = models.CharField(max_length=10, choices=settings.BRANCH_CHOICES, blank=True, null=True)
    date_of_joining = models.DateField(blank=True, null=True)
    is_onboard_created = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.candidate)


class Onboard(models.Model):
    appointment_letter = models.ForeignKey(OfferAppointmentLetter, on_delete=models.SET_NULL,
                                           related_name="onboard_appointment", blank=True, null=True)
    salary = models.ForeignKey(Salary, on_delete=models.SET_NULL, related_name="onboard_salary", blank=True, null=True)
    father_name = models.CharField(max_length=255, blank=True, null=True)
    father_dob = models.DateField(blank=True, null=True)
    mother_name = models.CharField(max_length=255, blank=True, null=True)
    mother_dob = models.DateField(blank=True, null=True)
    spouse_name = models.CharField(max_length=255, blank=True, null=True)
    spouse_dob = models.DateField(blank=True, null=True)
    child_1_name = models.CharField(max_length=255, blank=True, null=True)
    child_2_name = models.CharField(max_length=255, blank=True, null=True)
    child_1_dob = models.DateField(blank=True, null=True)
    child_2_dob = models.DateField(blank=True, null=True)
    blood_group = models.CharField(max_length=3, choices=settings.BLOOD_GROUP, blank=True, null=True)
    marital_status = models.CharField(max_length=10, choices=settings.MARITAL_STATUS, blank=True, null=True)
    candidate = models.OneToOneField(Candidate, on_delete=models.CASCADE)
    onboarded_by = models.ForeignKey("mapping.Profile", on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name="onboarded_by")
    permanent_address = models.TextField(blank=True, null=True)
    prmnt_address_1 = models.CharField(max_length=255, blank=True, null=True)
    prmnt_address_2 = models.CharField(max_length=255, blank=True, null=True)
    prmnt_state = models.CharField(max_length=255, blank=True, null=True)
    prmnt_city = models.CharField(max_length=255, blank=True, null=True)
    prmnt_zip_code = models.CharField(max_length=10, blank=True, null=True)

    temporary_address = models.TextField(blank=True, null=True)
    tmp_address_1 = models.CharField(max_length=255, blank=True, null=True)
    tmp_address_2 = models.CharField(max_length=255, blank=True, null=True)
    tmp_state = models.CharField(max_length=255, blank=True, null=True)
    tmp_city = models.CharField(max_length=255, blank=True, null=True)
    tmp_zip_code = models.CharField(max_length=10, blank=True, null=True)

    emergency_contact_1 = models.CharField(max_length=10, validators=[validate_mobile_no], blank=True, null=True)
    emergency_contact_relation = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_2 = models.CharField(max_length=10, validators=[validate_mobile_no], blank=True, null=True)
    onboard_status = models.BooleanField(default=True)
    is_all_doc_verified = models.BooleanField(default=False)
    is_pan_verified = models.BooleanField(default=False)
    is_aadhaar_verified = models.BooleanField(default=False)
    is_education_documents_verified = models.BooleanField(default=False)
    is_relieving_letters_verified = models.BooleanField(default=False)
    is_offer_letter_issued = models.BooleanField(default=False)

    relieving_letters = models.ManyToManyField(Document, blank=True, related_name='relieving_letters')
    education_documents = models.ManyToManyField(Document, blank=True, related_name="education_doc")
    aadhaar_card = models.ForeignKey(Document, on_delete=models.SET_NULL, blank=True, related_name="aadhaar", null=True)
    pancard = models.ForeignKey(Document, on_delete=models.SET_NULL, related_name="pancard", blank=True, null=True)
    health_card = models.ForeignKey(Document, on_delete=models.SET_NULL, related_name="health_card", blank=True,
                                    null=True)
    copy_of_signed_nda = models.ForeignKey(Document, on_delete=models.SET_NULL, related_name="copy_of_signed_nda",
                                           blank=True, null=True)
    copy_of_signed_offer_letter = models.ForeignKey(Document, on_delete=models.SET_NULL,
                                                    related_name="signed_offer_letter", blank=True, null=True)
    photo = models.ForeignKey(Document, on_delete=models.SET_NULL, related_name='photo', blank=True, null=True)
    cheque_copy = models.ForeignKey(Document, on_delete=models.SET_NULL, related_name="cheque_copy", blank=True,
                                    null=True)
    branch = models.CharField(max_length=10, choices=settings.BRANCH_CHOICES, blank=True, null=True)
    pan_no = EncryptedCField(max_length=24, blank=True, null=True)
    created_by_candidate_at = models.DateTimeField(blank=True, null=True)
    aadhaar_no = EncryptedCField(max_length=24, blank=True, null=True)
    gender = models.CharField(choices=settings.GENDER_CHOICES, max_length=14, blank=True, null=True)
    dob = models.DateField(validators=[validate_current_century], blank=True, null=True)
    date_of_joining = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return str(self.candidate)

