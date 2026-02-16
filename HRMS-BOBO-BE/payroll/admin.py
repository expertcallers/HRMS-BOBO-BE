from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from payroll.models import *
from utils.utils import get_column_names_with_foreign_keys_separate


class PayrollInfoResource(resources.ModelResource):
    class Meta:
        model = Payroll


class PayrollInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(Payroll)
    list_display = foreign_keys + list_display.copy()
    search_fields = ("profile__emp_id", "profile__full_name", 'year', "month")
    resource_class = PayrollInfoResource


class DeductionInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(Deduction)
    list_display = foreign_keys + list_display.copy()
    search_fields = ("profile__emp_id", "profile__full_name", 'year', "month")


class VariablePayInfo(admin.ModelAdmin):
    list_display = ["id", "profile", "created_by", "total", "process_incentive", "client_incentive", "bb_rent",
                    "overtime", "night_shift_allowance", "arrears", "attendance_bonus", "year", "month", "is_active",
                    "created_at", "updated_at"]
    search_fields = ("profile__emp_id", "profile__full_name", 'year', "month")
    autocomplete_fields = ["profile", "created_by", "updated_by"]


class SalaryInfo(ImportExportModelAdmin):
    search_fields = (['id', "candidate__full_name", "candidate__email"])
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(Salary)
    list_display = foreign_keys + list_display


class PayGradeInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(PayGrade)
    list_display = foreign_keys + list_display
    search_fields = ("level",)


class UpdateSalaryHistoryInfo(admin.ModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(UpdateSalaryHistory)
    list_display = foreign_keys + list_display
    search_fields = ("profile__emp_id", "candidate__full_name", "profile__full_name")


admin.site.register(UpdateSalaryHistory, UpdateSalaryHistoryInfo)
admin.site.register(PayGrade, PayGradeInfo)
admin.site.register(Salary, SalaryInfo)

admin.site.register(Payroll, PayrollInfo)
admin.site.register(Deduction, DeductionInfo)
admin.site.register(VariablePay, VariablePayInfo)
