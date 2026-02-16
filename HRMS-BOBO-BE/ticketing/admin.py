from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from utils.utils import get_column_names_with_foreign_keys_separate
from .models import Document, Ticket, TicketReply, TicketMessage, TicketHistory, SubCategory


class DocumentInfo(admin.ModelAdmin):
    list_display = ['field', 'ticket_id', 'uploaded_by_emp_id', 'uploaded_by_name']
    search_fields = ['field', 'ticket_id', 'uploaded_by_emp_id', 'uploaded_by_name']


class TicketInfo(admin.ModelAdmin):
    list_display = ['subject', 'sub_category', 'created_by', 'created_for', 'to_dept', 'assigned_to', 'status']
    search_fields = ['subject', 'sub_category', 'created_by', 'created_for', 'to_dept', 'assigned_to', 'status',
                     'created_at']
    autocomplete_fields = ['created_by', 'created_for', 'to_dept', 'assigned_to']


class TicketReplyInfo(admin.ModelAdmin):
    list_display = ["id", 'message', 'created_by']
    search_fields = ["id", 'message', 'created_by']
    autocomplete_fields = ['created_by', "reply_attachments"]


class TicketMessageInfo(admin.ModelAdmin):
    list_display = ['ticket', 'message', 'created_by']
    search_fields = ['ticket', 'message', 'created_by']
    autocomplete_fields = ['ticket', 'created_by', "msg_attachments"]


class TicketHistoryInfo(admin.ModelAdmin):
    list_display = ['ticket', 'transaction', 'created_by']
    search_fields = ['ticket', 'transaction', 'created_by']
    autocomplete_fields = ['ticket', 'created_by']


class SubCategoryInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(SubCategory)
    search_fields = list_display.copy()
    list_display += foreign_keys


admin.site.register(Document, DocumentInfo)
admin.site.register(Ticket, TicketInfo)
admin.site.register(TicketReply, TicketReplyInfo)
admin.site.register(TicketMessage, TicketMessageInfo)
admin.site.register(TicketHistory, TicketHistoryInfo)
admin.site.register(SubCategory, SubCategoryInfo)
