from django.contrib import admin
from django.utils.html import format_html

# Disable adminsortable2 to avoid static files issues
HAS_SORTABLE = False
SortableAdminMixin = object

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


if HAS_SORTABLE:
    @admin.register(Product)
    class ProductAdmin(SortableAdminMixin, admin.ModelAdmin):
        change_list_template = 'admin/change_list.html'  # Use default template instead of adminsortable2
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
else:
    @admin.register(Product)
    class ProductAdmin(admin.ModelAdmin):
        list_display = ["image_thumbnail", "barcode", "description", "product_group", "factory", "uom", "min_order_qty", "sort_rank", "is_active"]
        search_fields = ["barcode", "description", "product_group"]
        list_filter = ["product_group", "factory", "is_active"]
        ordering = ["sort_rank", "barcode"]
        fields = ["barcode", "description", "product_group", "image", "uom", "factory", "min_order_qty", "sort_rank", "is_active"]

        # Enable autocomplete for this model
        search_fields = ["barcode", "description"]

        def image_thumbnail(self, obj):
            if obj.image:
                return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
            return "-"
        image_thumbnail.short_description = "รูป"


@admin.register(CustomerProduct)
class CustomerProductAdmin(admin.ModelAdmin):
    list_display = ["customer", "product", "effective_barcode_display", "customer_sku", "min_order_qty_override", "sort_rank_override"]
    list_filter = ["customer"]
    search_fields = ["barcode_override", "customer_sku", "product__barcode", "product__description"]
    fields = ["customer", "product", "barcode_override", "customer_sku", "min_order_qty_override", "sort_rank_override"]
    autocomplete_fields = ["product"]

    def effective_barcode_display(self, obj):
        """Display effective barcode with indicator if overridden"""
        effective = obj.effective_barcode
        if obj.barcode_override:
            return format_html('<span style="color: #0066cc; font-weight: bold;">{}</span> (Override)', effective)
        return format_html('<span style="color: #666;">{}</span> (Default)', effective)
    effective_barcode_display.short_description = "Effective Barcode"

    def get_readonly_fields(self, request, obj=None):
        # Make customer and product readonly after creation to prevent accidental changes
        if obj:  # Editing an existing object
            return ["customer", "product"]
        return []

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter products based on selected customer in the form"""
        if db_field.name == "product":
            # Get customer_id from the URL (for editing) or from POST (for adding)
            customer_id = None
            if request.resolver_match.kwargs.get('object_id'):
                # Editing existing
                obj_id = request.resolver_match.kwargs['object_id']
                try:
                    cp = CustomerProduct.objects.get(pk=obj_id)
                    customer_id = cp.customer_id
                except CustomerProduct.DoesNotExist:
                    pass
            elif 'customer' in request.GET:
                # Adding new with customer pre-selected
                customer_id = request.GET.get('customer')

            # Note: We don't filter here because it would break the autocomplete
            # The filtering should be done in JavaScript on the frontend
            kwargs["queryset"] = Product.objects.filter(is_active=True).order_by('barcode')

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
