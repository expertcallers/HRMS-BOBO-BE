from datetime import datetime

from django.db import models

from hrms import settings
from mapping.models import Profile, Designation
from team.models import Process


# Create your models here.
class Parameter(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True, unique=True)
    type = models.CharField(max_length=1, choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name) + " ( " + str(self.id) + " - " + str(self.type) + " )"


class EmpAppraisal(models.Model):
    status = models.CharField(max_length=50, choices=settings.APPRAISAL_STATUS, default="Parameters Added")
    employee = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="emp_data_appraisee")
    supervisor_emp_id = models.CharField(max_length=20, blank=True, null=True)
    supervisor_name = models.CharField(max_length=255, blank=True, null=True)
    supervisor_designation = models.CharField(max_length=255, blank=True, null=True)
    reviewer_emp_id = models.CharField(max_length=20, blank=True, null=True)
    reviewer_name = models.CharField(max_length=255, blank=True, null=True)
    reviewer_designation = models.CharField(max_length=255, blank=True, null=True)
    mgr_appraisal_date = models.DateTimeField(blank=True, null=True)
    agent_completed_date = models.DateTimeField(blank=True, null=True)
    self_appraisal_date = models.DateTimeField(blank=True, null=True)
    emp_score = models.FloatField(blank=True, null=True)
    mgr_score = models.FloatField(blank=True, null=True)
    year = models.IntegerField(default=datetime.now().year)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class EmployeeParameter(models.Model):
    parameter = models.ForeignKey(Parameter, on_delete=models.SET_NULL, blank=True, null=True,
                                  related_name="emp_parameter")
    score = models.IntegerField(null=True, blank=True)
    emp_appraisal = models.ForeignKey(EmpAppraisal, on_delete=models.CASCADE, related_name="user_emp_appraisal")
    mgr_rating = models.FloatField(null=True, blank=True)
    mgr_comment = models.TextField(null=True, blank=True)
    emp_rating = models.FloatField(null=True, blank=True)
    emp_comment = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="created_by_emp")
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="updated_by_emp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class PartA_Appraisee(models.Model):
    emp_appraisal = models.ForeignKey(EmpAppraisal, on_delete=models.CASCADE, related_name="emp_PartA_appraisee")
    mgr_special_comment = models.TextField(blank=True, null=True)
    emp_special_comment = models.TextField(blank=True, null=True)
    mgr_score = models.FloatField(null=True, blank=True)
    emp_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class PartB_Appraisee(models.Model):
    emp_appraisal = models.ForeignKey(EmpAppraisal, on_delete=models.CASCADE, related_name="emp_PartB_appraisee")
    mgr_score = models.FloatField(null=True, blank=True)
    emp_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class PartC_Appraisee(models.Model):
    emp_appraisal = models.ForeignKey(EmpAppraisal, on_delete=models.CASCADE, related_name="emp_PartC_appraisee")
    mgr_score = models.FloatField(null=True, blank=True)
    emp_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class PartD_Appraisee(models.Model):
    emp_appraisal = models.ForeignKey(EmpAppraisal, on_delete=models.CASCADE, related_name="emp_PartD_appraisee")
    strengths = models.TextField(blank=True, null=True)
    improvement_areas = models.TextField(blank=True, null=True)
    checkbox = models.CharField(max_length=250, blank=True, null=True)
    mgr_appraisee_roles = models.TextField(blank=True, null=True)
    mgr_appraisee_skills_required = models.TextField(blank=True, null=True)
    mgr_appraisee_timeframe_from = models.DateField(blank=True, null=True)
    mgr_appraisee_timeframe_to = models.DateField(blank=True, null=True)
    mgr_comments_feedback = models.TextField(blank=True, null=True)
    appraisee_roles = models.TextField(blank=True, null=True)
    appraisee_skills_required = models.TextField(blank=True, null=True)
    appraisee_timeframe_from = models.DateField(blank=True, null=True)
    appraisee_timeframe_to = models.DateField(blank=True, null=True)
    appraisee_comments_feedback = models.TextField(blank=True, null=True)
    emp_agree_disagree = models.TextField(blank=True, null=True)
    is_emp_agreed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class DevActResDes(models.Model):
    partd_appraisee = models.ForeignKey(PartD_Appraisee, on_delete=models.CASCADE, related_name="dev_act_part_d",
                                        blank=True, null=True)
    development_need = models.TextField(blank=True, null=True)
    action_plan = models.TextField(blank=True, null=True)
    responsibility_time_to = models.DateField(blank=True, null=True)
    responsibility_time_from = models.DateField(blank=True, null=True)
    desired_level = models.TextField(blank=True, null=True)
    employee = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="DevActResDes_employee")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class TrainingTime(models.Model):
    training_type = models.CharField(max_length=255, blank=True, null=True)
    partd_appraisee = models.ForeignKey(PartD_Appraisee, on_delete=models.CASCADE, related_name="training_part_d",
                                        blank=True, null=True)
    timeframe_from = models.DateField(blank=True, null=True)
    timeframe_to = models.DateField(blank=True, null=True)
    employee = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="training_time_employee")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class DesiMap(models.Model):
    designations = models.ManyToManyField(Designation, blank=True, related_name="map_desi")
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)


class DefaultParams(models.Model):
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name="default_param")
    score = models.IntegerField()
    desi_map = models.ForeignKey(DesiMap, on_delete=models.CASCADE, related_name="map_desi_param")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class ExcludeList(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)
