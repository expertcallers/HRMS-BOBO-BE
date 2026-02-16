from django.db import models

from interview.models import Candidate
from mapping.models import Profile


# Create your models here.

class CabDetail(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="candidate_cab_details")
    updated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="cab_updated_by")
    house_no = models.CharField(max_length=50, null=True)
    house_apartment_name = models.CharField(max_length=255, null=True)
    landmark = models.CharField(max_length=255, null=True)
    area = models.CharField(max_length=255, null=True)
    address_1 = models.CharField(max_length=255, blank=True, null=True)
    address_2 = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    employee = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True, related_name="cab_employee")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return f"{self.id}-{self.candidate.full_name}"
