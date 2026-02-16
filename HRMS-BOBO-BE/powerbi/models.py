from ckeditor.fields import RichTextField
from django.db import models

from hrms import settings
from mapping.models import Profile
from team.models import Process


# Create your models here.

class SOP(models.Model):
    campaign = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="sop_campaign")
    campaign_type = models.CharField(max_length=255)
    campaign_type_other = models.CharField(max_length=255, blank=True, null=True)
    process_type_one = models.CharField(max_length=255)
    process_type_two = models.CharField(max_length=255)
    process_type_three = models.CharField(max_length=255)
    report_format = RichTextField(blank=True, null=True)
    other_info = models.TextField(blank=True)
    status = models.CharField(choices=settings.SOP_STATUS, max_length=20, default="Pending")

    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="sop_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class SOPSourceData(models.Model):
    sop = models.ForeignKey(SOP, on_delete=models.CASCADE, related_name="sop_data", blank=True, null=True)
    data_source = models.CharField(choices=settings.DATA_SOURCE, max_length=16)
    data_location = models.CharField(max_length=255)
    data_username = models.CharField(max_length=255, blank=True, null=True)
    data_password = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return str(self.id)
