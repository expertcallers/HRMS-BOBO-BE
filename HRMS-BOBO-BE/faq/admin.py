from ckeditor.widgets import CKEditorWidget
from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource

from faq.models import FAQ, FAQDocuments, GenericRichTextData


class FaqResource(ModelResource):
    class Meta:
        model = FAQ


class FaqInfo(ImportExportModelAdmin):
    search_fields = ("id", "question",)
    list_display = ["question", "answer", "created_at", "updated_at"]
    resource_class = FaqResource

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'answer':
            kwargs['widget'] = CKEditorWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class FAQDocumentsInfo(admin.ModelAdmin):
    search_fields = ("id", "file_name", "added_by__emp_id")
    list_display = ("id", "file_name", 'added_by')
    readonly_fields = ["file_name"]
    fields = ["file"]


class GenericRichTextResource(ModelResource):
    class Meta:
        model = GenericRichTextData


class GenericRichTextInfo(ImportExportModelAdmin):
    search_fields = ("id", "title")
    list_display = ["id", "title", "created_at", "updated_at"]
    resource_class = GenericRichTextResource

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'content':
            kwargs['widget'] = CKEditorWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)


admin.site.register(FAQDocuments, FAQDocumentsInfo)
admin.site.register(GenericRichTextData, GenericRichTextInfo)
admin.site.register(FAQ, FaqInfo)
