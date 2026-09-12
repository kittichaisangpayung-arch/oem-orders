from django import forms

from apps.core.models import Customer


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
    customer = forms.ModelChoiceField(queryset=Customer.objects.filter(is_active=True))
    upload_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='วันที่ Upload (เว้นว่างถ้าเป็นวันนี้)',
        help_text='สำหรับ upload PO ย้อนหลัง'
    )
    files = MultiFileField(widget=MultiFileInput(attrs={"multiple": True}))
