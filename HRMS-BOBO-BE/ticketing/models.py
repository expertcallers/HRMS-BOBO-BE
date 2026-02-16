import uuid
from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from mapping.models import Profile, Department
from hrms import settings


def validate_tkt_rating(value):
    if value > 5 or value < 1:
        raise ValidationError("Rating must be 1 to 5")


def document_file(instance, filename):
    today = datetime.today()
    return '/'.join(
        ['documents', str(today.year), str(today.month), str(today.day), str(uuid.uuid4()), filename])


class Document(models.Model):
    field = models.CharField(max_length=255)
    ticket_id = models.CharField(max_length=20, blank=True, null=True)
    file = models.FileField(upload_to=document_file,
                            validators=[
                                FileExtensionValidator(
                                    allowed_extensions=settings.DEFAULT_ALLOWED_EXTENSIONS)])
    file_name = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_emp_id = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.file)


class SubCategory(models.Model):
    sub_category = models.CharField(max_length=255)
    dept = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='dept_sub_category')
    priority = models.CharField(max_length=8, choices=settings.TICKET_PRIORITY, default="Normal")
    tat_days = models.IntegerField(null=True, blank=True)
    tat_hours = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class Ticket(models.Model):
    subject = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    created_for = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='tkt_created_for')
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='tkt_sub_category', default=1)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='tkt_raised_by')
    to_dept = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="tkt_to_dept")
    tkt_attachments = models.ManyToManyField(Document, blank=True, related_name="tkt_attachments")
    assigned_to = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='tkt_assigned_to')
    status = models.CharField(max_length=8, choices=settings.TICKET_STATUS_CHOICES, default="Open")
    user_rating = models.IntegerField(blank=True, null=True, validators=[validate_tkt_rating])
    closed_comment = models.CharField(max_length=255, null=True, blank=True)
    resolved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='t_resolved_by')
    resolve_comment = models.CharField(max_length=255, null=True, blank=True)
    closing_attachments = models.ManyToManyField(Document, blank=True, related_name="closing_attachments")
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class TicketReply(models.Model):
    message = models.CharField(max_length=500)
    reply_attachments = models.ManyToManyField(Document, blank=True, related_name="reply_attachments")
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='reply_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="track_message")
    message = models.TextField()
    msg_attachments = models.ManyToManyField(Document, blank=True, related_name="message_attachments")
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='message_created_by')
    replies = models.ManyToManyField(TicketReply, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.ticket)


class TicketHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='ticket_history')
    transaction = models.CharField(max_length=255)
    created_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='tm_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.ticket)
