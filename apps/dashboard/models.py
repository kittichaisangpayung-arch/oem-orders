from django.conf import settings
from django.db import models

from apps.core.models import Product, Store
from apps.ingestion.models import PurchaseOrderBatch


class StoreProductOverride(models.Model):
    """Manual override of a product's quantity for a specific store in a batch."""

    purchase_order_batch = models.ForeignKey(PurchaseOrderBatch, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    override_qty = models.IntegerField()
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order_batch", "product", "store"],
                name="unique_override_per_batch_product_store",
            ),
        ]

    def __str__(self):
        return f"Override: {self.product} -> {self.store} ({self.override_qty})"


class DeliveryNote(models.Model):
    """Delivery note for shipping products to a store."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        DELIVERED = "DELIVERED", "Delivered"

    # DN-YYYYMMDD-SSSS-NNNNNN format
    dn_number = models.CharField(max_length=50, unique=True, editable=False)

    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="delivery_notes")
    batch = models.ForeignKey(PurchaseOrderBatch, on_delete=models.SET_NULL, related_name="delivery_notes", null=True, blank=True)

    # Snapshot of store address at time of DN creation
    delivery_address = models.TextField()

    # Snapshot of customer head office address and tax ID
    customer_head_office_address = models.TextField(blank=True)
    customer_tax_id = models.CharField(max_length=50, blank=True)

    # PO order numbers (comma-separated if multiple POs)
    po_numbers = models.CharField(max_length=500, blank=True)

    # Delivery date (scheduled delivery date)
    delivery_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Financial information
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=7.00)  # 7% VAT
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Payment terms
    payment_terms = models.CharField(max_length=200, default="ระยะเวลา 30 วัน")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_delivery_notes")
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.dn_number} - {self.store.name}"

    def save(self, *args, **kwargs):
        if not self.dn_number:
            # Generate DN number: DN-YYYYMMDD-SSSS-NNNNNN
            from datetime import datetime
            today = datetime.now()
            date_str = today.strftime("%Y%m%d")
            store_code = f"{self.store.id:04d}"

            # Get next sequential number for today
            last_dn = DeliveryNote.objects.filter(
                dn_number__startswith=f"DN-{date_str}-{store_code}-"
            ).order_by("-dn_number").first()

            if last_dn:
                last_seq = int(last_dn.dn_number.split("-")[-1])
                next_seq = last_seq + 1
            else:
                next_seq = 1

            self.dn_number = f"DN-{date_str}-{store_code}-{next_seq:06d}"

        # Snapshot address if not set
        if not self.delivery_address and self.store:
            self.delivery_address = self.store.address or self.store.name

        super().save(*args, **kwargs)


class DeliveryNoteItem(models.Model):
    """Line item in a delivery note."""

    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    # Track if this quantity includes claims
    claimed_quantity = models.PositiveIntegerField(default=0)

    # Pricing
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    line_no = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["line_no", "product__sort_rank", "product__barcode"]

    def __str__(self):
        return f"{self.delivery_note.dn_number} - {self.product.description} x{self.quantity}"


class Invoice(models.Model):
    """Invoice for billing customer, combining multiple delivery notes."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    # INV-YYYYMM-NNNNNN format
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)

    customer = models.ForeignKey("core.Customer", on_delete=models.PROTECT, related_name="invoices")

    # Invoice period (month/year)
    invoice_month = models.IntegerField()  # 1-12
    invoice_year = models.IntegerField()  # YYYY

    # Customer head office address snapshot
    billing_address = models.TextField()
    customer_tax_id = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Financial information
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=7.00)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Payment terms
    payment_terms = models.CharField(max_length=200, default="ระยะเวลา 30 วัน")
    due_date = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_invoices")
    created_at = models.DateTimeField(auto_now_add=True)
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "invoice_year", "invoice_month"],
                name="unique_invoice_per_customer_month"
            ),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name} ({self.invoice_year}-{self.invoice_month:02d})"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number: INV-YYYYMM-NNNNNN
            year_month = f"{self.invoice_year}{self.invoice_month:02d}"
            prefix = f"INV-{year_month}-"

            # Find the last invoice number for this month
            last_invoice = Invoice.objects.filter(
                invoice_number__startswith=prefix
            ).order_by("-invoice_number").first()

            if last_invoice:
                last_seq = int(last_invoice.invoice_number.split("-")[-1])
                new_seq = last_seq + 1
            else:
                new_seq = 1

            self.invoice_number = f"{prefix}{new_seq:06d}"

        super().save(*args, **kwargs)


class InvoiceLineItem(models.Model):
    """Line item in an invoice - one line per delivery note."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    delivery_note = models.ForeignKey(DeliveryNote, on_delete=models.PROTECT, related_name="invoice_items")

    # External invoice number from other system
    external_invoice_number = models.CharField(max_length=100, blank=True)

    # Summary info from DN
    description = models.TextField()  # Product groups summary
    quantity = models.IntegerField()  # Total quantity
    unit = models.CharField(max_length=20, default="PCS")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    line_no = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["invoice", "line_no"]

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.delivery_note.dn_number}"

