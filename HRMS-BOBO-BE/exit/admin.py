from django.contrib import admin
from .models import Resignation, ResignationHistory, ExitFeedbackInterview, ExitChecklist, FinalApprovalChecklist


class ResignationInfo(admin.ModelAdmin):
    list_display = ['resignation_status', 'applied_by', 'start_date', 'exit_date', 'notice_period_in_days',
                    'applied_at']
    search_fields = ['resignation_status', 'applied_by__emp_id', 'start_date', 'exit_date', 'notice_period_in_days',
                     'accepted_or_rejected_by__emp_id', 'applied_at']
    autocomplete_fields = ['applied_by', 'accepted_or_rejected_by', 'notice_period_extended_or_reduced_by']


class ResignationHistoryInfo(admin.ModelAdmin):
    list_display = ['resignation', 'transaction', 'message', 'created_at']
    search_fields = ['resignation', 'transaction', 'message', 'created_at']
    autocomplete_fields = ['resignation']


class ExitFeedbackInterviewInfo(admin.ModelAdmin):
    list_display = ['resignation', 'primary_reason', 'created_at']
    search_fields = ['resignation', 'primary_reason', 'created_at']
    autocomplete_fields = ['resignation']


class ExitChecklistInfo(admin.ModelAdmin):
    list_display = ['content', 'dept', 'created_at']
    search_fields = ['content', 'dept', 'created_at']
    autocomplete_fields = ['dept']


class FinalApprovalInfo(admin.ModelAdmin):
    list_display = ['checklist', 'resignation', 'due_status', 'approved_by']
    search_fields = ['checklist', 'resignation', 'due_status', 'approved_by']
    autocomplete_fields = ['checklist', 'resignation', 'approved_by']


admin.site.register(Resignation, ResignationInfo)
admin.site.register(ResignationHistory, ResignationHistoryInfo)
admin.site.register(ExitFeedbackInterview, ExitFeedbackInterviewInfo)
admin.site.register(ExitChecklist, ExitChecklistInfo)
admin.site.register(FinalApprovalChecklist, FinalApprovalInfo)
