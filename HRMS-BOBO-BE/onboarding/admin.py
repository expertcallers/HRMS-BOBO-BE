from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from onboarding.models import *
from utils.utils import get_column_names_with_foreign_keys_separate


class OnboardInfo(ImportExportModelAdmin):
    search_fields = (['id', "candidate__full_name", "candidate__email"])
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(Onboard)
    list_display = foreign_keys + list_display


class OfferAppointmentLetterInfo(ImportExportModelAdmin):
    list_display, foreign_keys, autocomplete_fields = get_column_names_with_foreign_keys_separate(
        OfferAppointmentLetter)
    search_fields = list_display.copy()
    list_display = foreign_keys + list_display
    search_fields += ["candidate__full_name", "candidate__email"]


class DocumentInfo(ImportExportModelAdmin):
    search_fields = ("id", "field", "uploaded_by_emp_id", "onboard_id")
    list_display = ["id", "field", "onboard_id", "file_name", "created_at", "updated_at", "file", "filehash",
                    "uploaded_by_emp_id", "uploaded_by_name"]


# Register your models here.
admin.site.register(Document, DocumentInfo)
admin.site.register(Onboard, OnboardInfo)
admin.site.register(OfferAppointmentLetter, OfferAppointmentLetterInfo)
