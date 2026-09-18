from django.db import models


class CompanyProfile(models.Model):
    """Our company information for delivery notes and documents."""

    name_th = models.CharField(max_length=200, default="บริษัท ไมด้า อินเตอร์เทรด จำกัด")
    name_en = models.CharField(max_length=200, default="MIDA INTERTRADE CO., LTD.")
    address = models.TextField(default="25 ซอยสุขุมวิท 13 แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพมหานคร 10110")
    phone = models.CharField(max_length=50, default="02-651-1234")
    fax = models.CharField(max_length=50, default="02-651-1235", blank=True)
    tax_id = models.CharField(max_length=50, default="0105561071598")
    logo = models.ImageField(upload_to="company/", blank=True, null=True, help_text="Company logo")
    bank_name = models.CharField(max_length=100, default="กสิกรไทย")
    bank_swift = models.CharField(max_length=50, default="KASITHBK")
    bank_account_no = models.CharField(max_length=50, default="066-3-51404-0")
    bank_account_name = models.CharField(max_length=200, default="บริษัท นิวไลน์ โปรดักชั่น จำกัด")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profile"

    def __str__(self):
        return self.name_th

    @classmethod
    def get_active(cls):
        """Get the active company profile, or create a default one."""
        profile = cls.objects.filter(is_active=True).first()
        if not profile:
            profile = cls.objects.create(is_active=True)
        return profile


class Factory(models.Model):
    """Factory/manufacturer that produces products."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    contact_info = models.TextField(blank=True, help_text="Contact details, address, etc.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Factories"

    def __str__(self):
        return self.name


class Customer(models.Model):
    """A retail customer that sends us POs (e.g. Donki). Each customer has
    its own fixed PDF template, so parser_key selects which parser in
    apps.parsers.registry knows how to read that template."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    parser_key = models.CharField(
        max_length=50,
        help_text="Key registered in apps.parsers.registry, e.g. 'donki_v1'",
    )
    head_office_address = models.TextField(blank=True, help_text="Head office address for delivery notes")
    tax_id = models.CharField(max_length=50, blank=True, help_text="Customer tax ID")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Store(models.Model):
    """A branch/store of a customer, identified by that customer's own
    store code as printed on their PO (replaces the old STORE_CODE_MAP)."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="stores")
    store_code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, help_text="Full delivery address")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["customer", "store_code"], name="unique_store_code_per_customer"),
        ]

    def __str__(self):
        return f"{self.name} ({self.store_code})"


class Product(models.Model):
    """Master product/SKU catalog, keyed by barcode (replaces BARCODE_DESC,
    MIN_ORDER_MAP, PREDEFINED_ORDER which were hardcoded in the old script)."""

    barcode = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=300)
    product_group = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Product group for factory grouping (e.g., 'Nama Pudding', 'Cake')"
    )
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        help_text="Product image"
    )
    uom = models.CharField(max_length=20, default="PCS")
    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
        help_text="Factory that manufactures this product"
    )
    min_order_qty = models.PositiveIntegerField(
        default=0, help_text="Minimum order quantity per batch; 0 = no minimum"
    )
    sort_rank = models.PositiveIntegerField(
        null=True, blank=True, help_text="Display order in dashboards; blank sorts last"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = [models.F("sort_rank").asc(nulls_last=True), "barcode"]

    def __str__(self):
        return f"{self.barcode} - {self.description}"


class CustomerProduct(models.Model):
    """Optional per-customer override of a product's SKU text, barcode,
    minimum order quantity, or sort order (falls back to Product's own values)."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="product_overrides")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="customer_overrides")
    barcode_override = models.CharField(
        max_length=20,
        blank=True,
        help_text="Customer-specific barcode; if blank, uses product's default barcode"
    )
    customer_sku = models.CharField(max_length=100, blank=True)
    min_order_qty_override = models.PositiveIntegerField(null=True, blank=True)
    sort_rank_override = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["customer", "product"], name="unique_product_per_customer"),
            models.UniqueConstraint(
                fields=["customer", "barcode_override"],
                name="unique_barcode_per_customer",
                condition=models.Q(barcode_override__gt=""),
            ),
        ]

    def __str__(self):
        return f"{self.customer} / {self.product}"

    @property
    def effective_barcode(self):
        """Return customer-specific barcode if set, otherwise product's default barcode."""
        return self.barcode_override if self.barcode_override else self.product.barcode

    @property
    def effective_min_order_qty(self):
        return self.min_order_qty_override if self.min_order_qty_override is not None else self.product.min_order_qty

    @property
    def effective_sort_rank(self):
        return self.sort_rank_override if self.sort_rank_override is not None else self.product.sort_rank

    @classmethod
    def get_products_for_customer(cls, customer):
        """
        Get all products available for a customer, showing customer-specific barcode if exists.
        Returns list of dicts with: product, effective_barcode, effective_min_order_qty, effective_sort_rank
        """
        # Get all customer product overrides
        customer_products = cls.objects.filter(customer=customer).select_related('product')

        # Build map of product_id -> customer_product
        cp_map = {cp.product_id: cp for cp in customer_products}

        # Get all active products
        all_products = Product.objects.filter(is_active=True)

        result = []
        for product in all_products:
            cp = cp_map.get(product.id)
            if cp:
                # Has customer override
                result.append({
                    'product': product,
                    'customer_product': cp,
                    'effective_barcode': cp.effective_barcode,
                    'effective_min_order_qty': cp.effective_min_order_qty,
                    'effective_sort_rank': cp.effective_sort_rank,
                    'has_override': True,
                })
            else:
                # Use default product values
                result.append({
                    'product': product,
                    'customer_product': None,
                    'effective_barcode': product.barcode,
                    'effective_min_order_qty': product.min_order_qty,
                    'effective_sort_rank': product.sort_rank,
                    'has_override': False,
                })

        # Sort by effective_sort_rank and effective_barcode
        result.sort(key=lambda x: (
            x['effective_sort_rank'] is None,
            x['effective_sort_rank'] or 0,
            x['effective_barcode']
        ))

        return result
