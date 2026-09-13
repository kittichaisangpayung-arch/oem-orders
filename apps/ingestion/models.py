from django.conf import settings
from django.db import models

from apps.core.models import Customer, Product, Store


class PurchaseOrderBatch(models.Model):
    """One upload session: a set of PO PDFs uploaded together for a customer."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSED = "PROCESSED", "Processed"
        FAILED = "FAILED", "Failed"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="batches")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Batch #{self.pk} - {self.customer} ({self.uploaded_at:%Y-%m-%d %H:%M})"


def po_pdf_upload_path(instance, filename):
    """
    Generate upload path with structure: YYYY/Month/Week_X/batch_id/filename
    Example: 2569/กันยายน/สัปดาห์ที่ 2/1/file.pdf
    """
    from datetime import datetime
    import calendar

    # Get upload date (use batch uploaded_at if available)
    if hasattr(instance, 'batch') and instance.batch:
        upload_date = instance.batch.uploaded_at
    else:
        upload_date = datetime.now()

    # Thai year (Buddhist Era)
    thai_year = upload_date.year + 543

    # Thai month names
    thai_months = {
        1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม', 4: 'เมษายน',
        5: 'พฤษภาคม', 6: 'มิถุนายน', 7: 'กรกฎาคม', 8: 'สิงหาคม',
        9: 'กันยายน', 10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
    }
    thai_month = thai_months[upload_date.month]

    # Calculate week number in month (1-5)
    day = upload_date.day
    week_in_month = ((day - 1) // 7) + 1
    week_folder = f"สัปดาห์ที่ {week_in_month}"

    # Build path: YYYY/Month/Week/batch_id/filename
    return f"po_pdfs/{thai_year}/{thai_month}/{week_folder}/{instance.batch_id}/{filename}"


class PurchaseOrder(models.Model):
    """One PO = one uploaded source PDF. Raw parsed header fields are kept
    alongside resolved FKs so an unmapped store/customer never blocks
    ingestion -- it just surfaces as something to review."""

    class ParseStatus(models.TextChoices):
        OK = "OK", "OK"
        PARTIAL = "PARTIAL", "Partial (row count mismatch)"
        FAILED = "FAILED", "Failed"

    batch = models.ForeignKey(PurchaseOrderBatch, on_delete=models.CASCADE, related_name="purchase_orders")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="purchase_orders")
    store = models.ForeignKey(
        Store, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_orders"
    )

    order_no = models.CharField(max_length=100, blank=True)
    store_code_raw = models.CharField(max_length=50, blank=True)
    store_name_raw = models.CharField(max_length=200, blank=True)

    source_filename = models.CharField(max_length=255)
    source_file = models.FileField(upload_to=po_pdf_upload_path)

    parse_status = models.CharField(max_length=20, choices=ParseStatus.choices, default=ParseStatus.OK)
    expected_row_count = models.PositiveIntegerField(default=0)
    parsed_row_count = models.PositiveIntegerField(default=0)
    parser_used = models.CharField(max_length=50, blank=True)
    raw_text = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PO {self.order_no or self.source_filename} ({self.customer})"


class POLineItem(models.Model):
    """One product line from a parsed PO. Immutable once created -- this is
    the source of truth that dashboard aggregations query against."""

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="line_items")
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="line_items"
    )

    barcode_raw = models.CharField(max_length=20)
    description_raw = models.CharField(max_length=300, blank=True)
    uom_raw = models.CharField(max_length=20, blank=True)

    qty = models.IntegerField(default=0)
    qty2 = models.IntegerField(default=0)
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    line_no = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["purchase_order", "line_no"]

    def __str__(self):
        return f"{self.barcode_raw} x{self.qty2}"
