from django.contrib import admin

from po.models import SupplierAdministration, BillAdministration, BillItemDescription


class SupplierInfo(admin.ModelAdmin):
    list_display = ["id", "name", "contact_person", "contact_email", "created_by", "created_at"]
    search_fields = ["name", "contact_person", "contact_email", "created_by__emp_id", "created_at"]
    autocomplete_fields = ["created_by"]


class BillInfo(admin.ModelAdmin):
    list_display = ["id", "supplier", "project", "po_no", "date", "total_amount", "gst_amount", "grand_total",
                    "created_by", "created_at"]
    search_fields = ["supplier__name", "project", "po_no", "date", "total_amount", "gst_amount", "grand_total",
                     "created_by__emp_id", "created_at"]
    autocomplete_fields = ["supplier", "created_by"]


class ItemDescriptionInfo(admin.ModelAdmin):
    list_display = ["id", "bill", "description", "quantity", "gst_percent", "gst_amount", "price", "amount", "created_by",
                    "created_at"]
    search_fields = ["bill__id", "description", "quantity", "gst_percent", "gst_amount", "price", "amount",
                     "created_by__emp_id", "created_at"]
    autocomplete_fields = ["bill", "created_by"]


admin.site.register(SupplierAdministration, SupplierInfo)
admin.site.register(BillAdministration, BillInfo)
admin.site.register(BillItemDescription, ItemDescriptionInfo)
