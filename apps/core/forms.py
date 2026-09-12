from django import forms

from .models import Product


class ProductMinOrderForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["min_order_qty"]
