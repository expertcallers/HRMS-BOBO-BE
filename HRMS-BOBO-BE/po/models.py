from django.db import models
from django.core.validators import validate_email
from rest_framework.exceptions import ValidationError

from mapping.models import Profile
from utils.utils import EncryptedCField, validate_bnk_account_no, validate_alphanumeric, validate_ifsc
from hrms import settings


def validate_cin_code(value):
    if len(str(value)) > 21:
        raise ValidationError("Max length for CIN Code is 21.")


class SupplierAdministration(models.Model):
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField()
    contact_person = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=15)
    contact_email = models.EmailField(max_length=255, unique=True, validators=[validate_email])
    pan_no = EncryptedCField(max_length=255, unique=True)
    gst = EncryptedCField(max_length=255, unique=True)
    acc_name = EncryptedCField(max_length=255)
    account_number = EncryptedCField(max_length=255, unique=True, validators=[validate_bnk_account_no])
    bank_name = EncryptedCField(max_length=255, validators=[validate_alphanumeric])
    bank_branch = models.CharField(max_length=255)
    ifsc = EncryptedCField(max_length=255, validators=[validate_ifsc])
    cin_code = EncryptedCField(max_length=255, null=True, blank=True, validators=[validate_cin_code])
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class BillAdministration(models.Model):
    supplier = models.ForeignKey(SupplierAdministration, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.CharField(max_length=255)
    po_no = models.CharField(max_length=50, blank=True, null=True)
    date = models.DateField()
    billing_office = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, choices=settings.PO_CATEGORY, null=True, blank=True)
    delivery_office = models.CharField(max_length=255)
    delivery_address = models.TextField()
    contact_person = models.CharField(max_length=255)
    contact_no = models.CharField(max_length=15)
    contact_email = models.EmailField(max_length=255, validators=[validate_email])
    terms_and_conditions = models.TextField()
    amount_in_words = models.TextField(null=True, blank=True)
    pan = EncryptedCField(max_length=255, default='AAECE0810D')
    gst = EncryptedCField(max_length=255, default='29AAECE0810D1Z6')
    total_amount = models.FloatField(null=True, blank=True)
    gst_amount = models.FloatField(null=True, blank=True)
    grand_total = models.FloatField(null=True, blank=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class BillItemDescription(models.Model):
    bill = models.ForeignKey(BillAdministration, on_delete=models.CASCADE)
    description = models.TextField()
    quantity = models.IntegerField()
    gst_percent = models.FloatField()
    gst_amount = models.FloatField(null=True, blank=True)
    price = models.FloatField()
    amount = models.FloatField(null=True, blank=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.bill.project
