from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from transport.models import CabDetail
from utils.utils import get_column_names_with_foreign_keys_separate


# Register your models here.
class CabDetailInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(CabDetail)
    search_fields = list_display.copy() + ["id", "employee__emp_id"]
    list_display = foreign_keys + list_display


admin.site.register(CabDetail, CabDetailInfo)
