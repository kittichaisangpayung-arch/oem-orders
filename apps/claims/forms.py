from django import forms

from apps.ingestion.models import PurchaseOrderBatch

from .models import Claim


class BatchSelectForm(forms.Form):
    batch = forms.ModelChoiceField(
        queryset=PurchaseOrderBatch.objects.order_by("-uploaded_at"),
        required=False,
        label="เลือก Batch",
    )


class ClaimForm(forms.ModelForm):
    line_item = forms.IntegerField(widget=forms.Select(choices=[]))

    class Meta:
        model = Claim
        fields = ["qty", "note"]

    def __init__(self, *args, po_line_items=None, **kwargs):
        super().__init__(*args, **kwargs)
        po_line_items = po_line_items or []
        self.fields["line_item"].widget = forms.Select(
            choices=[
                (
                    li.pk,
                    f"{li.barcode_raw} - {li.description_raw} (สั่ง {li.qty2})",
                )
                for li in po_line_items
            ]
        )
        self.fields["line_item"].label = "รายการสินค้า"
