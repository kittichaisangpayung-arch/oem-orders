from django.contrib import admin

from .models import Claim


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ["store", "product", "qty", "created_by", "created_at"]
    list_filter = ["store", "product"]
    search_fields = ["store__name", "product__description", "product__barcode"]
