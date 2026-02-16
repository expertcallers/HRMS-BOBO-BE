from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from appraisal.models import *
from utils.utils import get_column_names, get_column_names_with_foreign_keys_separate


# Register your models here.

class ParameterInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(Parameter)
    search_fields = list_display.copy()
    list_display += foreign_keys


class ExcludeListInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(ExcludeList)
    search_fields = list_display.copy()
    list_display += foreign_keys


class EmployeeParameterInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(EmployeeParameter)
    search_fields = list_display.copy() + ["emp_appraisal__employee__emp_id"]
    list_display = ["emp_id"] + foreign_keys + list_display

    def emp_id(self, obj):
        return obj.emp_appraisal.employee.emp_id


class DefaultParamsInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(DefaultParams)
    search_fields = list_display.copy()
    list_display += foreign_keys


class DesiMapInfo(ImportExportModelAdmin):
    list_display, foreign_keys, _ = get_column_names_with_foreign_keys_separate(DesiMap)
    search_fields = list_display.copy()
    list_display += foreign_keys
    autocomplete_fields = foreign_keys
    filter_horizontal = ("designations",)


class PartA_AppraiseeInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(PartA_Appraisee)
    search_fields = list_display.copy() + ["emp_appraisal__employee__emp_id"]
    list_display = ["emp_id"] + foreign_keys + list_display

    def emp_id(self, obj):
        return obj.emp_appraisal.employee.emp_id


class PartB_AppraiseeInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(PartB_Appraisee)
    search_fields = list_display.copy() + ["emp_appraisal__employee__emp_id"]
    list_display = ["emp_id"] + foreign_keys + list_display

    def emp_id(self, obj):
        return obj.emp_appraisal.employee.emp_id


class PartC_AppraiseeInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(PartC_Appraisee)
    search_fields = list_display.copy() + ["emp_appraisal__employee__emp_id"]
    list_display = ["emp_id"] + foreign_keys + list_display

    def emp_id(self, obj):
        return obj.emp_appraisal.employee.emp_id


class PartD_AppraiseeInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(PartD_Appraisee)
    search_fields = list_display.copy() + ["emp_appraisal__employee__emp_id"]
    list_display = ["emp_id"] + foreign_keys + list_display

    def emp_id(self, obj):
        return obj.emp_appraisal.employee.emp_id


class EmpAppraisalInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(EmpAppraisal)
    search_fields = list_display.copy() + ["employee__emp_id"]
    list_display = foreign_keys + ["emp_name"] + list_display

    def emp_name(self, obj):
        return obj.employee.full_name


admin.site.register(ExcludeList, ExcludeListInfo)
admin.site.register(EmpAppraisal, EmpAppraisalInfo)
admin.site.register(PartA_Appraisee, PartA_AppraiseeInfo)
admin.site.register(PartB_Appraisee, PartB_AppraiseeInfo)
admin.site.register(PartC_Appraisee, PartC_AppraiseeInfo)
admin.site.register(PartD_Appraisee, PartD_AppraiseeInfo)
admin.site.register(Parameter, ParameterInfo)
admin.site.register(EmployeeParameter, EmployeeParameterInfo)
admin.site.register(DesiMap, DesiMapInfo)
admin.site.register(DefaultParams, DefaultParamsInfo)
