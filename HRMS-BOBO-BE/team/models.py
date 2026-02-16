from crum import get_current_user
from django.db import models

from hrms import settings
from mapping.models import Profile, Designation, Department


class Process(models.Model):
    name = models.CharField(max_length=255, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="process_department")
    has_report = models.BooleanField(default=False)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True, related_name="process_cr")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)


class Team(models.Model):
    base_team = models.ForeignKey(Process, on_delete=models.SET_NULL, blank=True, null=True, related_name="base_team")
    name = models.CharField(max_length=255, unique=True)
    manager = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True, related_name="team_rm")
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True, related_name="team_cr")
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True, related_name="team_up")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)
