import logging

from django.core.validators import validate_email, FileExtensionValidator
from django.db import models
from hrms import settings

from datetime import datetime

from rest_framework.exceptions import ValidationError

from mapping.models import Department, Designation, Profile
from utils.utils import validate_number_with_fixed_size, hash_value, EncryptedCField, validate_current_century, \
    document_file, validate_mobile_no, validate_aadhaar_no

logger = logging.getLogger(__name__)


# Create your models here.
def resume_file(instance, filename):
    return '/'.join(['resume', filename])


def rel_letter_file(instance, filename):
    return '/'.join(['rel_letter', filename])


LANG_CHOICES = settings.LANG_CHOICES
GENDER_CHOICES = settings.GENDER_CHOICES
CANDIDATE_STATUS_CHOICES = settings.CANDIDATE_STATUS_CHOICES
QUALF_CHOICES = settings.QUALF_CHOICES
SOURCE_CHOICES = settings.SOURCE_CHOICES
BRANCH_CHOICES = settings.BRANCH_CHOICES


def validate_alpha_text(value):
    for char1 in str(value):
        if not char1.isalpha() and not char1.isspace() and char1 not in ["'", "."]:
            raise ValidationError("It should have only alpha characters")


def validate_prev_comp_exp(value):
    data = value.split(",")
    for i in data:
        if not str(i).isnumeric():
            raise ValidationError("it must contain only numeric data")


class CandidateOTPTest(models.Model):
    email = models.EmailField(max_length=255, validators=[validate_email])
    verify_otp = models.CharField(max_length=6)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.email)


class FieldsOfExperience(models.Model):
    category = models.CharField(max_length=255)
    subcategory = models.CharField(max_length=255)

    def __str__(self):
        return str(self.subcategory)


class Application(models.Model):
    candidate = models.ForeignKey('interview.Candidate', on_delete=models.CASCADE, related_name="interview_cand_app",
                                  null=True, blank=True)
    status = models.BooleanField(default=True)
    test_completed = models.BooleanField(default=False)
    test = models.ForeignKey("interview_test.Test", on_delete=models.SET_NULL, null=True, blank=True, db_index=True,
                             related_name='int_test')
    position_applied = models.ForeignKey('erf.ERF', on_delete=models.SET_NULL, null=True, blank=True, db_index=True,
                                         related_name='candidate_erf')
    job_position = models.CharField(max_length=100, blank=True, null=True)
    to_department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True)
    interviewer = models.ForeignKey('mapping.Profile', on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name="candidate_interviewer")
    all_to_departments = models.ManyToManyField(Department, blank=True, related_name="all_to_departments",
                                                db_index=True)
    all_interview_persons = models.ManyToManyField(Profile, blank=True, related_name="all_interviewers")
    source = models.CharField(choices=SOURCE_CHOICES, max_length=30, blank=True, null=True)
    source_ref = models.CharField(max_length=255, default="NA")
    # status = models.CharField(choices=CANDIDATE_STATUS_CHOICES, max_length=30, default="Applied", db_index=True)

    ta_rating = models.JSONField(default=dict, null=True, blank=True)
    ops_rating = models.JSONField(default=dict, null=True, blank=True)
    branch = models.CharField(choices=BRANCH_CHOICES, max_length=10, blank=True, null=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return str(self.id)


class Candidate(models.Model):
    current_application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name="curr_application")
    all_applications = models.ManyToManyField(Application, blank=True, related_name="all_applications")
    first_name = models.CharField(max_length=255, validators=[validate_alpha_text], db_index=True)
    middle_name = models.CharField(max_length=255, blank=True, null=True, validators=[validate_alpha_text],
                                   db_index=True)
    last_name = models.CharField(max_length=255, validators=[validate_alpha_text], db_index=True, blank=True, null=True)
    full_name = models.CharField(max_length=555, validators=[validate_alpha_text], null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True, validators=[validate_email], db_index=True, null=True)
    mobile = models.CharField(max_length=10, validators=[validate_mobile_no], blank=True, null=True)
    mobile_alt = models.CharField(max_length=10, blank=True, null=True, validators=[validate_mobile_no])
    house_no = models.CharField(max_length=50, null=True)
    house_apartment_name = models.CharField(max_length=255, null=True)
    landmark = models.CharField(max_length=255, null=True)
    area = models.CharField(max_length=255, null=True)
    address_1 = models.CharField(max_length=255, blank=True, null=True)
    address_2 = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    dob = models.DateField(validators=[validate_current_century], blank=True, null=True)
    is_interview_completed = models.BooleanField(default=False)
    highest_qualification = models.CharField(choices=QUALF_CHOICES, max_length=30, blank=True, null=True)
    education_course = models.CharField(max_length=255, blank=True, null=True)
    fields_of_experience = models.CharField(max_length=500)
    gender = models.CharField(choices=GENDER_CHOICES, max_length=14, blank=True, null=True)
    resume = models.ForeignKey('interview.Document', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="resume")
    is_employee = models.BooleanField(default=False)
    current_ctc = models.FloatField()
    expected_ctc = models.FloatField()
    total_work_exp = models.FloatField(default=0, db_index=True)
    prev_comp_exp = models.CharField(max_length=255, blank=True, null=True, validators=[validate_prev_comp_exp])
    prev_comp_name = models.CharField(max_length=500, blank=True, null=True)
    relieving_letter = models.ForeignKey('interview.Document', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name="relieving_letter")
    status = models.CharField(choices=CANDIDATE_STATUS_CHOICES, max_length=30, default="Not Applied", db_index=True)
    aadhaar_no = EncryptedCField(max_length=24, unique=True, validators=[validate_aadhaar_no])

    # aadhaar_no = models.CharField(max_length=12, unique=True, validators=[validate_aadhaar_no])
    is_transport_required = models.BooleanField(default=False)
    transport_approval_status = models.CharField(max_length=8, choices=settings.TRANSPORT_APPROVAL_STATUS_ALL,
                                                 default="NA")
    transport_admin_app_rej_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True,
                                                   related_name="transport_admin_app", null=True)
    transport_approval_comment = models.CharField(max_length=255, blank=True, null=True)
    cab_address = models.ForeignKey('transport.CabDetail', on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name="cab_details")
    languages = models.TextField(blank=True, null=True)
    is_inactive = models.BooleanField(default=False)
    last_interview_at = models.DateTimeField(db_index=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return str(self.email)

    def save(self, *args, **kwargs):
        self.email = self.email.lower() if self.email else None
        super().save(*args, **kwargs)


# TODO delete associated file if the instance is deleted, here candidate
class Document(models.Model):
    field = models.CharField(max_length=255)
    candidate_id = models.CharField(max_length=20)
    file = models.FileField(upload_to=document_file,
                            validators=[
                                FileExtensionValidator(
                                    allowed_extensions=settings.DEFAULT_ALLOWED_EXTENSIONS)])
    file_name = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_emp_id = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_name = models.CharField(max_length=255, blank=True, null=True)
    filehash = models.CharField(max_length=32, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.file)


class Interviewer(models.Model):
    interview_emp = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name="i_profile")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="interview_candidate")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interview_application")
    status = models.CharField(choices=CANDIDATE_STATUS_CHOICES, max_length=30)
    feedback = models.TextField()
    round_name = models.CharField(max_length=60)
    interview_files = models.ManyToManyField(Document, blank=True, related_name='inter_document')
    result = models.BooleanField()
    to_department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name="to_department")
    from_department = models.ForeignKey(Department, related_name="from_department", on_delete=models.SET_NULL,
                                        blank=True, null=True)
    is_dept_specific = models.BooleanField(default=False)
    to_person = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True, related_name="to_person")
    total_rounds = models.IntegerField()
    current_round = models.IntegerField(default=-1)
    editable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class ToAppliedCandidateStatus(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="send_back_candidate")
    old_application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="send_back_old_application")
    new_application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="send_back_new_application")
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True, related_name="created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class InternPosition(models.Model):
    name = models.CharField(max_length=25, choices=settings.INTERN_POSITION, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)


class InternQuestion(models.Model):
    position = models.ForeignKey(InternPosition, on_delete=models.SET_NULL, related_name="questions", null=True)
    question_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class InternApplication(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, validators=[validate_email])
    phone_no = models.CharField(max_length=10)
    tech_skills = models.TextField(null=True)
    position = models.ForeignKey(InternPosition, on_delete=models.SET_NULL, related_name="interns_positions", null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)


class InternAnswer(models.Model):
    intern = models.ForeignKey(InternApplication, on_delete=models.CASCADE, related_name="answers_by_interns")
    question = models.ForeignKey(InternQuestion, on_delete=models.SET_NULL, related_name="answers_by_questions",
                                 null=True)
    answer_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    score = models.IntegerField(null=True)

    def __str__(self):
        return str(self.id)
