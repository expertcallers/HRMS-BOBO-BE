from django.contrib import admin

from powerbi.models import SOP, SOPSourceData


# Register your models here.

class SOPInfo(admin.ModelAdmin):
    list_display = ["id", "campaign", "status", "campaign_type", "campaign_type_other", "process_type_one",
                    "process_type_two", "process_type_three", "created_by"]
    search_fields = ["campaign__name", "id"]


class SOPSourceDataInfo(admin.ModelAdmin):
    list_display = ["sop", "data_source", "data_location", "data_username", "data_password"]
    search_fields = ("sop__id",)


admin.site.register(SOP, SOPInfo)
admin.site.register(SOPSourceData, SOPSourceDataInfo)
