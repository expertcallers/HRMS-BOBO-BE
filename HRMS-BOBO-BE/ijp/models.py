from django.db import models
from rest_framework.exceptions import ValidationError
import mapping.models
from hrms import settings
from team.models import Process


def contact_number_validator(value):
    if not str(value).isnumeric() or not len(str(value)) == 10:
        raise ValidationError("Contact Number should be Numeric & shall contain 10 digits.")


class IJP(models.Model):
    # approval_status = models.CharField(
    #     choices=settings.ERF_APPROVAL_STATUS, max_length=10)
    # approved_or_rejected_by = models.ForeignKey(mapping.models.Profile, on_delete=models.SET_NULL, blank=True, null=True,
    #                                             related_name="ijp_approved_or_rejected_by")
    no_of_openings = models.IntegerField()
    created_by = models.ForeignKey(mapping.models.Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="ijp_created_by")
    process = models.ForeignKey(Process, related_name="ijp_process", on_delete=models.CASCADE)
    department = models.ForeignKey(mapping.models.Department, on_delete=models.CASCADE, related_name="ijp_department")
    designation = models.ForeignKey(mapping.models.Designation, on_delete=models.CASCADE,
                                    related_name="ijp_designation")
    contact_profile = models.CharField(max_length=55)
    contact_number = models.CharField(max_length=10, validators=[contact_number_validator])

    selection_criteria = models.TextField()
    selection_process = models.TextField()
    additional_requirements = models.JSONField(default=dict, blank=True, null=True)

    no_of_rounds = models.IntegerField()
    round_names = models.CharField(max_length=255)
    shift_timing = models.CharField(choices=settings.IJP_SHIFT_TIMING, max_length=20)
    last_date_to_apply = models.DateField()

    closed_by = models.ForeignKey(mapping.models.Profile, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="ijp_closed_by")
    is_ijp_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.designation.name + " - " + self.process.name


class IJPCandidate(models.Model):
    profile = models.ForeignKey(mapping.models.Profile, on_delete=models.CASCADE, related_name="ijp_profile")
    ijp_applied = models.ForeignKey(IJP, on_delete=models.CASCADE, related_name="ijp_candidate_ijp")
    current_process = models.ForeignKey(Process, on_delete=models.SET_NULL, null=True,
                                        related_name="ijp_current_process")
    contact_number = models.CharField(max_length=10, validators=[contact_number_validator])
    alternate_contact_number = models.CharField(max_length=10, validators=[contact_number_validator], null=True,
                                                blank=True)
    disciplinary_status = models.CharField(max_length=100, null=True, blank=True)
    attendance_count = models.IntegerField(null=True, blank=True)
    current_round = models.IntegerField(default=0)
    status = models.CharField(choices=settings.IJP_CANDIDATE_STATUS, max_length=30, default="Applied")
    comments = models.TextField(null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.profile.first_name + " ; " + self.ijp_applied.__str__()
