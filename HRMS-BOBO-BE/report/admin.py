from django.contrib import admin

from report.models import *
from utils.utils import get_column_names


# Register your models here.

class SLAInfo(admin.ModelAdmin):
    list_display = ["id", "task", "index", "metric", "metric_id", "date", "value"]
    search_fields = ["report_file__process"]
    autocomplete_fields = ["report_file"]


class TAInfo(admin.ModelAdmin):
    list_display = ["id", "main_task", "main_task_id", "task", "index_for_the_whole_team", "weight",
                    "daily_target_of_the_whole_team", "days", "days_achieved_the_target", "achieved_ratio", "month",
                    "year", "created_by", "created_at", "updated_at"]
    search_fields = ["report_file__process"]
    autocomplete_fields = ["report_file"]


class ReportFileInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(ReportFile)
    search_fields = ["process"]


class GBMDialerInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(GbmDialer)


class GBMCallInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(GbmCall)


class GBMEmailInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(GbmEmail)


class GBMLeadInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(GbmLead)


class AadyaSolutionsInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(AadyaSolutions)


class InsalvageInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(Insalvage)


class MedicareInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(Medicare)


class SapphireMedicalInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(SapphireMedical)


class CapgeminiInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(Capgemini)


class BBMInfo(admin.ModelAdmin):
    list_display, autocomplete_fields = get_column_names(BBM)


admin.site.register(SLA, SLAInfo)
admin.site.register(TA, TAInfo)
admin.site.register(ReportFile, ReportFileInfo)
admin.site.register(GbmDialer, GBMDialerInfo)
admin.site.register(GbmCall, GBMCallInfo)
admin.site.register(GbmEmail, GBMEmailInfo)
admin.site.register(GbmLead, GBMLeadInfo)
admin.site.register(BBM, BBMInfo)
admin.site.register(Capgemini, CapgeminiInfo)
admin.site.register(SapphireMedical, SapphireMedicalInfo)
admin.site.register(Medicare, MedicareInfo)
admin.site.register(Insalvage, InsalvageInfo)
admin.site.register(AadyaSolutions, AadyaSolutionsInfo)
