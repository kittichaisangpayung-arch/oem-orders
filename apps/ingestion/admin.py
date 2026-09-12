from django.contrib import admin

from .models import POLineItem, PurchaseOrder, PurchaseOrderBatch


class POLineItemInline(admin.TabularInline):
    model = POLineItem
    extra = 0
    readonly_fields = ["barcode_raw", "description_raw", "uom_raw", "qty", "qty2", "unit_amount", "line_total"]


@admin.register(PurchaseOrderBatch)
class PurchaseOrderBatchAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "uploaded_by", "uploaded_at", "status"]
    list_filter = ["customer", "status"]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["order_no", "customer", "store", "parse_status", "parsed_row_count", "expected_row_count", "created_at"]
    list_filter = ["customer", "parse_status"]
    search_fields = ["order_no", "source_filename", "store_code_raw"]
    inlines = [POLineItemInline]
    readonly_fields = [
        "batch", "customer", "order_no", "store_code_raw", "store_name_raw",
        "source_filename", "parse_status", "expected_row_count", "parsed_row_count",
        "parser_used", "raw_text", "error_message", "created_at",
    ]
