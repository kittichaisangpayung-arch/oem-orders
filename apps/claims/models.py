from django.conf import settings
from django.db import models

from apps.core.models import Product, Store


class Claim(models.Model):
    """A store reports a claim (e.g. shortage/damage that needs replacing)
    for a given product quantity, tied to the PurchaseOrder it was ordered
    on. Claims ADD to the PO quantity when computing the net production
    total sent to the factory -- the store needs the originally ordered
    amount PLUS the claimed amount."""

    purchase_order = models.ForeignKey(
        "ingestion.PurchaseOrder", on_delete=models.SET_NULL, null=True, blank=True, related_name="claims"
    )
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="claims")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="claims")
    qty = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.store} / {self.product} x{self.qty}"


class Compensation(models.Model):
    """A store receives compensation for a given product quantity, tied to
    the PurchaseOrder. Compensations ADD to the PO quantity when computing
    the net production total sent to the factory -- the store needs the
    originally ordered amount PLUS the compensation amount."""

    purchase_order = models.ForeignKey(
        "ingestion.PurchaseOrder", on_delete=models.SET_NULL, null=True, blank=True, related_name="compensations"
    )
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="compensations")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="compensations")
    qty = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.store} / {self.product} x{self.qty}"
