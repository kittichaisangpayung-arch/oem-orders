from django.contrib import admin
from django.utils.html import format_html
from adminsortable2.admin import SortableAdminMixin

from .models import CompanyProfile, Customer, CustomerProduct, Factory, Product, Store


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ["name_th", "name_en", "phone", "tax_id", "is_active"]
    fieldsets = (
        ("ข้อมูลบริษัท", {
            "fields": ("name_th", "name_en", "address", "phone", "fax", "tax_id", "logo")
        }),
        ("ข้อมูลธนาคาร", {
            "fields": ("bank_name", "bank_swift", "bank_account_no", "bank_account_name")
        }),
        ("สถานะ", {
            "fields": ("is_active",)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Override save to handle file upload errors gracefully"""
        try:
            super().save_model(request, obj, form, change)
            self.message_user(request, "บันทึกข้อมูลบริษัทเรียบร้อยแล้ว", level='success')
        except Exception as e:
            from django.contrib import messages
            error_msg = f"ไม่สามารถบันทึกข้อมูลได้: {str(e)}"
            if "Google Drive" in str(e):
                error_msg += " (ปัญหาการเชื่อมต่อ Google Drive - กรุณาติดต่อผู้ดูแลระบบ)"
            self.message_user(request, error_msg, level='error')
            raise


class StoreInline(admin.TabularInline):
    model = Store
    extra = 1


@admin.register(Factory)
class FactoryAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active", "created_at"]
    search_fields = ["name", "code"]
    list_filter = ["is_active"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "parser_key", "is_active"]
    search_fields = ["name", "code"]
    inlines = [StoreInline]


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ["name", "store_code", "customer", "is_active"]
    list_filter = ["customer"]
    search_fields = ["name", "store_code"]


@admin.register(Product)
class ProductAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["image_thumbnail", "barcode", "description", "product_group", "factory", "uom", "min_order_qty", "sort_rank", "is_active"]
    search_fields = ["barcode", "description", "product_group"]
    list_filter = ["product_group", "factory", "is_active"]
    ordering = ["sort_rank", "barcode"]
    fields = ["barcode", "description", "product_group", "image", "uom", "factory", "min_order_qty", "sort_rank", "is_active"]

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "-"
    image_thumbnail.short_description = "รูป"


@admin.register(CustomerProduct)
class CustomerProductAdmin(admin.ModelAdmin):
    list_display = ["customer", "product", "customer_sku", "min_order_qty_override", "sort_rank_override"]
    list_filter = ["customer"]
