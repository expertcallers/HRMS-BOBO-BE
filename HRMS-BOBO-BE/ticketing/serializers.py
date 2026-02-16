import json

from rest_framework import serializers
from datetime import timedelta
from hrms import settings
from ticketing.models import Ticket, TicketHistory, Document, TicketMessage, TicketReply, SubCategory
from utils.utils import get_formatted_name, form_module_url


def form_document_url(doc_id):
    return form_module_url(doc_id, "tkt")


def get_path_and_name_dict(obj):
    if not obj:
        return None
    return {"path": form_document_url(obj.id), "name": obj.file.name.split("/")[::-1][0]}


class CreateTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["subject", "created_for", "content", "to_dept", "sub_category", "created_by"]


class DocumentSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["path"] = form_document_url(instance.id)
        data["name"] = instance.file.name.split("/")[::-1][0]
        return data

    class Meta:
        model = Document
        exclude = ("field", "ticket_id", "file")


class GetAllTicketsSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["assigned_to_emp_id"] = instance.assigned_to.emp_id if instance.assigned_to else None
        data["assigned_to_name"] = instance.assigned_to.full_name if instance.assigned_to else None
        data["created_by_emp_id"] = instance.created_by.emp_id
        data["created_by_name"] = instance.created_by.full_name
        data["created_for_emp_id"] = instance.created_for.emp_id if instance.created_for else None
        data["created_for_name"] = instance.created_for.full_name if instance.created_for else None
        data["resolved_by_emp_id"] = instance.resolved_by.emp_id if instance.resolved_by else None
        data["resolved_by_name"] = instance.resolved_by.full_name if instance.resolved_by else None
        data["from_dept"] = instance.created_by.designation.department.name
        data["to_dept"] = instance.to_dept.name
        data["sub_category"] = instance.sub_category.sub_category
        data["priority"] = instance.sub_category.priority
        data["tat_days"] = instance.sub_category.tat_days
        data["tat_hours"] = instance.sub_category.tat_hours
        data["tkt_attachments"] = DocumentSerializer(instance.tkt_attachments.all(), many=True).data
        data["closing_attachments"] = DocumentSerializer(instance.closing_attachments.all(), many=True).data
        data["remaining_time"] = str(instance.created_at + timedelta(days=instance.sub_category.tat_days,
                                                                     hours=instance.sub_category.tat_hours))
        return data

    class Meta:
        model = Ticket
        exclude = ("created_by", "assigned_to", "tkt_attachments", "closing_attachments")


class UpdateTicketStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["status"]


class GetTicketHistorySerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        return data

    class Meta:
        model = TicketHistory
        exclude = ("created_by",)


class CreateTicketReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketReply
        fields = ["message"]


class CreateTicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketMessage
        fields = ["message"]


class GetAllTicketReplySerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        image = instance.created_by.image if instance.created_by else None
        data['profile_image'] = settings.MEDIA_URL + str(image) if str(image) else ""
        data["msg_attachments"] = DocumentSerializer(instance.reply_attachments.all(), many=True).data
        return data

    class Meta:
        model = TicketReply
        exclude = ['reply_attachments']


class GetAllTicketMessageSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by_emp_id"] = instance.created_by.emp_id if instance.created_by else None
        data["created_by_name"] = instance.created_by.full_name if instance.created_by else None
        image = instance.created_by.image if instance.created_by else None
        data['profile_image'] = settings.MEDIA_URL + str(image) if str(image) else ""
        data["msg_attachments"] = DocumentSerializer(instance.msg_attachments.all(), many=True).data
        data["replies"] = GetAllTicketReplySerializer(instance.replies.all(), many=True).data
        return data

    class Meta:
        model = TicketMessage
        exclude = ("created_by",)


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = '__all__'


class ResolveTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['resolved_by', 'resolve_comment']


class CloseTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['closed_comment', 'user_rating', 'closed_at']
