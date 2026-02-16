from django.db import models

from hrms import settings
from interview_test.models import Test
from mapping.models import Profile, Department, Designation
from team.models import Process


# Create your models here.
class ERF(models.Model):
    test = models.ManyToManyField(Test, blank=True, related_name="erf_test")
    approval_status = models.CharField(
        choices=settings.ERF_APPROVAL_STATUS, max_length=10)
    approved_or_rejected_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                                related_name="erf_approved_or_rejected_by")
    requisition_date = models.DateField()
    hc_req = models.IntegerField()
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="erf_profile")
    profiles = models.ManyToManyField(Profile, blank=True, related_name="erf_profiles")
    process = models.ForeignKey(Process, related_name="erf_process", on_delete=models.CASCADE, blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="erf_department", blank=True,
                                   null=True)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE, related_name="erf_designation", blank=True,
                                    null=True)
    process_type_one = models.CharField(max_length=50)
    process_type_two = models.CharField(max_length=50)
    process_type_three = models.CharField(max_length=50)
    years_of_experience = models.IntegerField(default=0)
    pricing = models.BigIntegerField()
    salary_range_frm = models.IntegerField()
    salary_range_to = models.IntegerField()
    qualification = models.CharField(choices=settings.QUALF_CHOICES, max_length=30)

    other_quali = models.TextField(null=True, blank=True)

    fields_of_experience = models.TextField()
    languages = models.TextField(null=True, blank=True)

    shift_timing = models.CharField(choices=settings.SHIFT_TIMING, max_length=20)
    shift_timing_frm = models.CharField(max_length=20, null=True, blank=True)
    shift_timing_to = models.CharField(max_length=20, null=True, blank=True)

    type_of_working = models.CharField(choices=settings.TYPE_OF_WORKING, max_length=100)

    week_offs = models.CharField(max_length=20, null=True, blank=True)

    requisition_type = models.CharField(choices=settings.REQUISITION_TYPE, max_length=50)
    reason_for_replace = models.TextField(null=True, blank=True)
    no_of_rounds = models.IntegerField()
    round_names = models.CharField(max_length=255)
    interview_persons = models.CharField(max_length=66)
    closure_date = models.DateField(null=True, blank=True)

    deadline = models.DateField()

    closed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="erf_cl_by")
    is_erf_open = models.BooleanField(default=True)
    always_open = models.BooleanField(default=False)
    close_reason = models.CharField(max_length=255, blank=True, null=True)
    erf_reopen = models.BooleanField(default=False)
    erf_reopen_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class ERFHistory(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                related_name="erf_history_profile")

    status = models.CharField(max_length=8, choices=settings.ERF_HISTORY_STATUS)
    comment = models.CharField(max_length=255, blank=True, null=True)
    erf = models.ForeignKey(ERF, on_delete=models.SET_NULL, blank=True, null=True)
    added_or_removed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                            related_name="erf_history_created_removed_by")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.profile

# class ERFRounds(models.Model):
#     round_name = models.CharField(max_length=255)
#     person = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="erf_person", blank=True, null=True)
#     round_value = models.IntegerField()
#     is_active = models.BooleanField(default=False)
#     is_completed = models.BooleanField(default=False)
#     is_dept_specific = models.BooleanField(default=False)
#     department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="erf_dept", blank=True, null=True)
#     erf = models.ForeignKey(ERF, on_delete=models.CASCADE, related_name="erf_rounds")
#
#     def __str__(self):
#         return str(self.round_name)
