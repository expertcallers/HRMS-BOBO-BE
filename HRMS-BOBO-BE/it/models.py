from ckeditor.fields import RichTextField
from django.db import models

from hrms import settings
from mapping.models import Profile


# Create your models here.
class ChangeMgmt(models.Model):
    document_number = models.IntegerField()
    sub_doc_number = models.IntegerField(default=0)
    version = models.CharField(max_length=10)
    version_date = models.DateField()
    location_site = models.CharField(max_length=10, choices=settings.BRANCH_CHOICES)
    application_system = models.CharField(max_length=20, choices=settings.APPLICATION_SYSTEM)
    current_version = models.CharField(max_length=10)
    changed_version = models.CharField(max_length=10)
    implemented_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                       related_name="imp_profile")
    initiated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name="ini_by_profile")
    type = models.CharField(max_length=50, choices=settings.CHANGE_MGMT_TYPE)
    reason_for_change = models.CharField(max_length=555, blank=True, null=True)
    change_impact = models.CharField(max_length=20, choices=settings.CHANGE_IMPACT)
    exp_the_chng_imp_area_fn_carryout_chng = models.TextField(blank=True, null=True)
    deployment_details = RichTextField()
    rollback_action = models.CharField(max_length=555, blank=True, null=True)
    communication_plan = models.TextField(max_length=555, blank=True, null=True)
    downtime_req = models.CharField(max_length=555, blank=True, null=True)
    deployment_start_datetime = models.DateTimeField()
    deployment_end_datetime = models.DateTimeField()
    device_name = models.CharField(max_length=30, choices=settings.DEVICE_NAME)
    site = models.CharField(max_length=10, choices=settings.CHANGE_SITE)
    hypervisor_name = models.CharField(max_length=255, blank=True, null=True)
    physical_hostname = models.CharField(max_length=255, blank=True, null=True)
    vm_hostname = models.CharField(max_length=255, blank=True, null=True)
    change_approved_date = models.DateTimeField(blank=True, null=True)
    change_approved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                           related_name="approved_by_profile")
    reviewed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name="reviewed_by_profile")
    reviewed_date = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="created_by_profile")
    rejected_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                    related_name="rejected_by_profile")
    rejected_date = models.DateTimeField(blank=True, null=True)
    new_edit_exists = models.BooleanField(default=False)

    change_status = models.CharField(max_length=8, choices=settings.CHANGE_STATUS, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)
