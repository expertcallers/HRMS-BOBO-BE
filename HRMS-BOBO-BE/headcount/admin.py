from django.contrib import admin

from headcount.models import ProcessSubCampaign, HeadcountProcess, Headcount, UpdateProcessRequest, \
    UpdateHeadcountRequest, HeadcountReference


class ProcessSubCampaignInfo(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_by', 'created_at']
    search_fields = ['id', 'name', 'created_by__emp_id', 'created_at']
    autocomplete_fields = ['created_by']


class HeadcountProcessInfo(admin.ModelAdmin):
    list_display = ['id', 'name', 'approved_headcount', 'rm', 'is_active', 'created_by', 'created_at']
    search_fields = ['id', 'name', 'approved_headcount', 'rm__emp_id', 'is_active', 'created_by__emp_id', 'created_at']
    autocomplete_fields = ['rm', 'sub_campaign', 'created_by']


class HeadcountInfo(admin.ModelAdmin):
    list_display = ['id', 'sub_campaign', 'scheduled_hc', 'present_hc', 'deficit', 'total_hours',
                    'created_by', 'created_at']
    search_fields = ['id', 'sub_campaign__name', 'scheduled_hc', 'present_hc', 'deficit',
                     'total_hours', 'created_by__emp_id', 'created_at']
    autocomplete_fields = ['sub_campaign', 'created_by']


class UpdateProcessRequestInfo(admin.ModelAdmin):
    list_display = ['id', 'process', 'requested_approved_headcount', 'comment', 'status', 'approved_rejected_by', 'created_by',
                    'created_at']
    search_fields = ['id', 'process__name', 'approved_headcount', 'comment', 'status', 'approved_rejected_by__emp_id',
                     'created_by__emp_id', 'created_at']
    autocomplete_fields = ['process', 'approved_rejected_by', 'created_by']


class UpdateHeadcountRequestInfo(admin.ModelAdmin):
    list_display = ['id', 'headcount', 'old_scheduled_hc', 'scheduled_hc', 'old_present_hc', 'present_hc', 'comment',
                    'status', 'approved_rejected_by', 'created_by', 'created_at']
    search_fields = ['id', 'old_scheduled_hc', 'scheduled_hc', 'old_present_hc', 'present_hc', 'comment', 'status',
                     'approved_rejected_by__emp_id', 'created_by__emp_id', 'created_at']
    autocomplete_fields = ['headcount', 'approved_rejected_by', 'created_by']


class HeadcountReferenceInfo(admin.ModelAdmin):
    list_display = ['id', 'process', 'date', 'created_by', 'created_at']
    search_fields = ['id', 'process__name', 'date', 'created_by__emp_id', 'created_at']
    autocomplete_fields = ['process', 'headcount', 'created_by']


admin.site.register(ProcessSubCampaign, ProcessSubCampaignInfo)
admin.site.register(HeadcountProcess, HeadcountProcessInfo)
admin.site.register(Headcount, HeadcountInfo)
admin.site.register(UpdateProcessRequest, UpdateProcessRequestInfo)
admin.site.register(UpdateHeadcountRequest, UpdateHeadcountRequestInfo)
admin.site.register(HeadcountReference, HeadcountReferenceInfo)
