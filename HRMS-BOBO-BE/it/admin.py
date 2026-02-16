from ckeditor.widgets import CKEditorWidget
from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from it.models import ChangeMgmt
from utils.utils import get_column_names


# Register your models here.

class ChangeMgmtInfo(ImportExportModelAdmin):
    list_display, autocomplete_fields = get_column_names(ChangeMgmt)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'deployment_details':
            kwargs['widget'] = CKEditorWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)


admin.site.register(ChangeMgmt, ChangeMgmtInfo)
