from django.contrib import admin

from .models import DeliveryNote, DeliveryNoteItem, StoreProductOverride


class DeliveryNoteItemInline(admin.TabularInline):
    model = DeliveryNoteItem
    extra = 0
    readonly_fields = ["product", "quantity", "claimed_quantity", "unit_price", "amount", "line_no"]
    can_delete = False


@admin.register(DeliveryNote)
class DeliveryNoteAdmin(admin.ModelAdmin):
    list_display = ["dn_number", "store", "batch", "status", "grand_total", "created_at", "created_by"]
    list_filter = ["status", "store__customer", "created_at"]
    search_fields = ["dn_number", "store__name", "store__store_code"]
    readonly_fields = ["dn_number", "created_at", "confirmed_at"]
    inlines = [DeliveryNoteItemInline]
    actions = ["delete_selected"]

    fieldsets = (
        ("ข้อมูลทั่วไป", {
            "fields": ("dn_number", "store", "batch", "status")
        }),
        ("ที่อยู่", {
            "fields": ("delivery_address", "customer_head_office_address", "customer_tax_id", "po_numbers")
        }),
        ("การเงิน", {
            "fields": ("subtotal", "vat_rate", "vat_amount", "grand_total", "payment_terms")
        }),
        ("ข้อมูลเพิ่มเติม", {
            "fields": ("notes", "created_by", "created_at", "confirmed_at")
        }),
    )


@admin.register(StoreProductOverride)
class StoreProductOverrideAdmin(admin.ModelAdmin):
    list_display = ["purchase_order_batch", "store", "product", "override_qty", "updated_by", "updated_at"]
    list_filter = ["purchase_order_batch", "store"]
    search_fields = ["product__description", "product__barcode", "store__name"]
