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

    class InvoiceType(models.TextChoices):
        BILLING_STATEMENT = "BILLING_STATEMENT", "ใบวางบิล"  # Summary by DN
        DETAILED_INVOICE = "DETAILED_INVOICE", "Invoice"  # Detailed line items

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
    invoice_type = models.CharField(max_length=20, choices=InvoiceType.choices, default=InvoiceType.BILLING_STATEMENT)

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


class Quotation(models.Model):
    """Quotation for customer - price proposal"""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SENT = "SENT", "Sent"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    # QT-YYYYMMDD-NNNNNN format
    quotation_number = models.CharField(max_length=50, unique=True, editable=False)

    customer = models.ForeignKey("core.Customer", on_delete=models.PROTECT, related_name="quotations")

    # Customer contact info snapshot
    contact_person = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    billing_address = models.TextField()
    customer_tax_id = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Validity period
    valid_until = models.DateField(null=True, blank=True)

    # Financial information
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=7.00)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Payment terms
    payment_terms = models.CharField(max_length=200, default="ระยะเวลา 30 วัน")
    delivery_terms = models.CharField(max_length=200, default="ส่งสินค้าภายใน 7 วันทำการ")

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_quotations")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.quotation_number} - {self.customer.name}"

    def save(self, *args, **kwargs):
        if not self.quotation_number:
            # Generate quotation number: QT-YYYYMMDD-NNNNNN
            from datetime import datetime
            today = datetime.now()
            date_str = today.strftime("%Y%m%d")
            prefix = f"QT-{date_str}-"

            # Find the last quotation number for today
            last_qt = Quotation.objects.filter(
                quotation_number__startswith=prefix
            ).order_by("-quotation_number").first()

            if last_qt:
                last_seq = int(last_qt.quotation_number.split("-")[-1])
                new_seq = last_seq + 1
            else:
                new_seq = 1

            self.quotation_number = f"{prefix}{new_seq:06d}"

        super().save(*args, **kwargs)

    def calculate_totals(self):
        """Calculate and update all financial fields"""
        from decimal import Decimal

        # Calculate subtotal from line items
        self.subtotal = sum(item.amount for item in self.line_items.all())

        # Calculate discount
        if self.discount_percent > 0:
            self.discount_amount = self.subtotal * (Decimal(str(self.discount_percent)) / Decimal('100'))

        # Calculate amount after discount
        amount_after_discount = self.subtotal - self.discount_amount

        # Calculate VAT
        self.vat_amount = amount_after_discount * (Decimal(str(self.vat_rate)) / Decimal('100'))

        # Calculate grand total
        self.grand_total = amount_after_discount + self.vat_amount

        self.save(update_fields=['subtotal', 'discount_amount', 'vat_amount', 'grand_total'])


class QuotationLineItem(models.Model):
    """Line item in a quotation"""

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="line_items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    description = models.TextField()  # Product description (can be customized)
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=20, default="PCS")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Optional: show product image on quotation
    show_image = models.BooleanField(default=False)

    line_no = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["quotation", "line_no"]

    def __str__(self):
        return f"{self.quotation.quotation_number} - {self.product.description}"

    def save(self, *args, **kwargs):
        # Calculate amount
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

