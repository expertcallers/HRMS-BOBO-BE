from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from tax.models import *
from utils.utils import get_column_names_with_foreign_keys_separate


# Register your models here.

class IT80CInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(IT80C)
    search_fields = list_display.copy() + []
    list_display = [] + foreign_keys + list_display


class OtherChapVIADeductionsInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        OtherChapVIADeductions)
    search_fields = list_display.copy() + []
    list_display = [] + foreign_keys + list_display


class HouseRentInfoInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(HouseRentInfo)
    search_fields = list_display.copy() + []
    list_display = [] + foreign_keys + list_display


class HouseRentAllowanceInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(HouseRentAllowance)
    search_fields = list_display.copy() + []
    list_display = [] + foreign_keys + list_display


class MedicalSec80DInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(MedicalSec80D)
    search_fields = list_display.copy() + []
    list_display = [] + foreign_keys + list_display


class HousePropertyInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(HouseProperty)
    search_fields = list_display.copy() + []
    list_display = [] + foreign_keys + list_display


class HousePropertyIncomeLossInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        HousePropertyIncomeLoss)
    search_fields = list_display.copy() + []
    list_display = [] + foreign_keys + list_display


class OtherIncomeInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(OtherIncome)
    search_fields = list_display.copy() + []
    list_display = [] + foreign_keys + list_display


class ITInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(IT)
    search_fields = list_display.copy() + []
    list_display = [] + foreign_keys + list_display


admin.site.register(IT, ITInfo)
admin.site.register(OtherIncome, OtherIncomeInfo)
admin.site.register(HousePropertyIncomeLoss, HousePropertyIncomeLossInfo)
admin.site.register(HouseProperty, HousePropertyInfo)
admin.site.register(MedicalSec80D, MedicalSec80DInfo)
admin.site.register(HouseRentAllowance, HouseRentAllowanceInfo)
admin.site.register(HouseRentInfo, HouseRentInfoInfo)
admin.site.register(OtherChapVIADeductions, OtherChapVIADeductionsInfo)
admin.site.register(IT80C, IT80CInfo)
