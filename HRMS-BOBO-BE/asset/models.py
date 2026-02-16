from django.db import models
from mapping.models import Profile
from hrms import settings
from datetime import datetime
import uuid
from django.core.validators import FileExtensionValidator


def document_file(instance, filename):
    today = datetime.today()
    return '/'.join(
        ['documents', str(today.year), str(today.month), str(today.day), str(uuid.uuid4()), filename])


class Document(models.Model):
    field = models.CharField(max_length=255)
    asset_allocation_id = models.CharField(max_length=20, blank=True, null=True)
    file = models.FileField(upload_to=document_file, validators=[FileExtensionValidator(
        allowed_extensions=settings.DEFAULT_ALLOWED_EXTENSIONS)])
    file_name = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_emp_id = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.file)


class AssetCategory(models.Model):
    name = models.CharField(max_length=55, unique=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='category_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.name)


class Asset(models.Model):
    asset_category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True)
    brand = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=255, null=True, blank=True)
    system_name = models.CharField(max_length=100, null=True, blank=True)
    processor = models.CharField(max_length=255, null=True, blank=True)
    serial_number = models.CharField(max_length=255)
    ram = models.CharField(max_length=15, null=True, blank=True)
    hard_disk_type = models.CharField(max_length=5, choices=settings.HARD_DISK_TYPE, null=True, blank=True)
    hard_disk_serial_no = models.CharField(max_length=255, null=True, blank=True)
    hard_disk_size = models.CharField(max_length=55, null=True, blank=True)
    monitor_brand = models.CharField(max_length=100, null=True, blank=True)
    monitor_serial_no = models.CharField(max_length=255, null=True, blank=True)
    monitor_size = models.CharField(max_length=55, null=True, blank=True)
    keyboard = models.BooleanField(default=False)
    mouse = models.BooleanField(default=False)
    webcam = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=settings.ASSET_STATUS)
    os = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='asset_created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id) + " - " + str(self.serial_number)


class AssetAllocation(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    it_policy = models.CharField(max_length=500, null=True, blank=True)
    policy_number = models.CharField(max_length=500, null=True, blank=True)
    docs = models.ManyToManyField(Document, blank=True, related_name="asset_documents")
    docs_uid = models.CharField(max_length=255, null=True, blank=True)
    docs_type = models.CharField(max_length=255, null=True, blank=True)
    assigned_to = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='assigned_to')
    status = models.CharField(max_length=20, choices=settings.ASSET_ALLOCATION_CHOICES)
    assigned_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='assigned_by')
    assigned_at = models.DateTimeField(auto_now_add=True)
    return_comment = models.CharField(max_length=500, null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class AssetHistory(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='asset_history')
    transaction = models.CharField(max_length=55)
    message = models.CharField(max_length=255)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True,
                                   related_name='asset_history_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)
