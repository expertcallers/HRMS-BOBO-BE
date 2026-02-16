from django.db import models

from hrms import settings
from mapping.models import Profile


def validate_positive_value(value):
    if not value >= 0:
        raise ValueError("Value needs to be Positive")


class ProcessSubCampaign(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="subcampaign_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class HeadcountProcess(models.Model):
    name = models.CharField(max_length=255)
    pricing = models.FloatField(default=0)
    currency = models.CharField(choices=settings.HC_CURRENCY, max_length=10)
    pricing_type = models.CharField(choices=settings.HC_PRICING_TYPE, max_length=10)
    pricing_type_value = models.FloatField(default=0)
    approved_headcount = models.FloatField(default=0, validators=[validate_positive_value])
    rm = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="reporting_manager")
    sub_campaign = models.ManyToManyField(ProcessSubCampaign, blank=True, related_name="hc_process_sub_campaign")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="process_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)


class Headcount(models.Model):
    sub_campaign = models.ForeignKey(ProcessSubCampaign, on_delete=models.SET_NULL, null=True,
                                     related_name="hc_sub_campaign")
    scheduled_hc = models.FloatField(default=0, validators=[validate_positive_value])
    present_hc = models.FloatField(default=0, validators=[validate_positive_value])
    deficit = models.FloatField(default=0, validators=[validate_positive_value])
    total_hours = models.FloatField(default=0, validators=[validate_positive_value])
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="hc_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.sub_campaign.name)


class HeadcountReference(models.Model):
    process = models.ForeignKey(HeadcountProcess, on_delete=models.SET_NULL, null=True,
                                related_name="headcount_process")
    approved_headcount = models.FloatField(default=0, validators=[validate_positive_value])
    date = models.DateField()
    headcount = models.ManyToManyField(Headcount, blank=True, related_name="hc_ref")
    target_revenue = models.FloatField(default=0, validators=[validate_positive_value])
    achieved_revenue = models.FloatField(default=0, validators=[validate_positive_value])
    leakage_revenue = models.FloatField(default=0, validators=[validate_positive_value])
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="hc_ref_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class UpdateProcessRequest(models.Model):
    process = models.ForeignKey(HeadcountProcess, on_delete=models.CASCADE)
    requested_approved_headcount = models.FloatField(default=0, validators=[validate_positive_value])
    requested_pricing = models.FloatField(default=0, blank=True, null=True)
    requested_currency = models.CharField(choices=settings.HC_CURRENCY, max_length=10, blank=True, null=True)
    requested_pricing_type = models.CharField(choices=settings.HC_PRICING_TYPE, max_length=10, blank=True, null=True)
    requested_pricing_type_value = models.FloatField(default=0, blank=True, null=True)
    comment = models.CharField(max_length=550)
    status = models.CharField(choices=settings.HEADCOUNT_STATUS_CHOICES, max_length=10)
    approved_rejected_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True,
                                             related_name="update_hc_approved_rejected_by")
    approved_rejected_comment = models.CharField(max_length=550, null=True, blank=True)
    approved_rejected_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True,
                                   related_name="update_process_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class UpdateHeadcountRequest(models.Model):
    headcount = models.ForeignKey(Headcount, on_delete=models.SET_NULL, null=True, related_name="update_headcount")
    old_scheduled_hc = models.FloatField(default=0, validators=[validate_positive_value])
    scheduled_hc = models.FloatField(default=0, validators=[validate_positive_value])
    old_present_hc = models.FloatField(default=0, validators=[validate_positive_value])
    present_hc = models.FloatField(default=0, validators=[validate_positive_value])
    comment = models.CharField(max_length=550)
    status = models.CharField(choices=settings.HEADCOUNT_STATUS_CHOICES, max_length=10)
    approved_rejected_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True,
                                             related_name="update_process_approved_rejected_by")
    approved_rejected_comment = models.CharField(max_length=550, null=True, blank=True)
    approved_rejected_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="update_hc_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)
