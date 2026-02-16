from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources

from erf.models import ERF, ERFHistory


class ERFResource(resources.ModelResource):
    class Meta:
        model = ERF


class ERFInfo(ImportExportModelAdmin):
    list_display = ["id", "has_test", 'requisition_date', 'hc_req', 'created_by', 'process',
                    'department', 'designation', 'approval_status', 'process_type_one', 'process_type_two',
                    'process_type_three', 'pricing', 'salary_range_frm', 'salary_range_to', 'qualification',
                    'other_quali', "fields_of_experience", 'languages', 'shift_timing', 'shift_timing_frm',
                    'shift_timing_to', 'type_of_working', 'week_offs', 'requisition_type', 'approved_or_rejected_by',
                    'reason_for_replace', 'closure_date', 'deadline', 'closed_by', 'created_at', 'updated_at']
    search_fields = ("id", "languages", "requisition_type")
    autocomplete_fields = ['department', 'designation', "process", 'closed_by', 'created_by', 'profiles',
                           'approved_or_rejected_by', "test"]
    resource_class = ERFResource

    def has_test(self, obj):
        return True if obj.test.all().count() > 0 else False


class ERFHistoryinfo(admin.ModelAdmin):
    list_display = ["id", "erf", "comment", "status", "added_or_removed_by", "profile"]
    search_fields = ("id", "erf__id", "profile__emp_id")
    autocomplete_fields = ["erf", "added_or_removed_by", "profile"]


admin.site.register(ERFHistory, ERFHistoryinfo)
admin.site.register(ERF, ERFInfo)
