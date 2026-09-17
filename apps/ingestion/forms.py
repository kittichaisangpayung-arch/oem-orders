from django import forms

from apps.core.models import Customer, Store, Product


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultiFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if isinstance(data, (list, tuple)):
            return [super(MultiFileField, self).clean(item, initial) for item in data]
        return super().clean(data, initial)


class BatchUploadForm(forms.Form):
    ENTRY_MODE_CHOICES = [
        ('PDF', 'อ่านจาก PDF'),
        ('MANUAL', 'กรอกข้อมูลเอง (Manual)')
    ]

    customer = forms.ModelChoiceField(queryset=Customer.objects.filter(is_active=True))
    entry_mode = forms.ChoiceField(
        choices=ENTRY_MODE_CHOICES,
        initial='PDF',
        label='โหมดการกรอก',
        widget=forms.Select(attrs={'onchange': 'toggleEntryMode(this.value)'})
    )
    upload_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='วันที่ Upload (เว้นว่างถ้าเป็นวันนี้)',
        help_text='สำหรับ upload PO ย้อนหลัง'
    )
    files = MultiFileField(
        widget=MultiFileInput(attrs={"multiple": True}),
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        entry_mode = cleaned_data.get('entry_mode')
        files = cleaned_data.get('files')

        if entry_mode == 'PDF' and not files:
            raise forms.ValidationError('กรุณาเลือกไฟล์ PDF อย่างน้อย 1 ไฟล์')

        return cleaned_data


class ManualPOLineItemForm(forms.Form):
    """Form for a single line item in manual PO entry"""
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        label='สินค้า',
        widget=forms.Select(attrs={'class': 'product-select'})
    )
    qty = forms.IntegerField(
        min_value=0,
        initial=0,
        label='จำนวน (กล่อง)',
        widget=forms.NumberInput(attrs={'class': 'qty-input'})
    )
    qty2 = forms.IntegerField(
        min_value=0,
        initial=0,
        label='จำนวน (ชิ้น)',
        widget=forms.NumberInput(attrs={'class': 'qty2-input'})
    )


class ManualPOEntryForm(forms.Form):
    """Form for manual PO entry"""
    store = forms.ModelChoiceField(
        queryset=Store.objects.none(),
        label='สาขา',
        widget=forms.Select(attrs={'class': 'store-select'})
    )
    order_no = forms.CharField(
        max_length=100,
        required=False,
        label='เลขที่ PO',
        widget=forms.TextInput(attrs={'class': 'order-no-input'})
    )

    def __init__(self, *args, customer=None, **kwargs):
        super().__init__(*args, **kwargs)
        if customer:
            self.fields['store'].queryset = Store.objects.filter(
                customer=customer,
                is_active=True
            ).order_by('name')
