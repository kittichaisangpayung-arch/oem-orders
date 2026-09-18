"""
Utility functions for core app
"""
from .models import Product, CustomerProduct


def get_products_for_customer(customer, include_all=True):
    """
    Get all products for a specific customer with their effective barcodes.

    Args:
        customer: Customer object or customer_id
        include_all: If True, include all active products. If False, only products with overrides.

    Returns:
        List of dicts with product info and effective values
    """
    if customer is None:
        # No customer selected - return all products with default values
        products = Product.objects.filter(is_active=True).order_by('sort_rank', 'barcode')
        return [{
            'product': p,
            'product_id': p.id,
            'effective_barcode': p.barcode,
            'effective_min_order_qty': p.min_order_qty,
            'effective_sort_rank': p.sort_rank,
            'has_override': False,
            'customer_sku': '',
        } for p in products]

    # Get customer ID if customer object passed
    customer_id = customer.id if hasattr(customer, 'id') else customer

    # Use the classmethod from CustomerProduct
    from .models import Customer
    customer_obj = Customer.objects.get(pk=customer_id)
    return CustomerProduct.get_products_for_customer(customer_obj)


def get_barcode_to_product_map(customer=None):
    """
    Get mapping of barcode -> product for a specific customer.
    Uses customer-specific barcode if available, otherwise default barcode.

    Args:
        customer: Customer object or customer_id (optional)

    Returns:
        Dict: {barcode: product_id}
    """
    barcode_map = {}

    if customer is None:
        # No customer - use default barcodes only
        products = Product.objects.filter(is_active=True)
        for p in products:
            if p.barcode:
                barcode_map[p.barcode] = p.id
    else:
        # Get customer ID
        customer_id = customer.id if hasattr(customer, 'id') else customer

        # Get all customer product overrides
        customer_products = CustomerProduct.objects.filter(
            customer_id=customer_id
        ).select_related('product')

        # Build map with customer-specific barcodes
        override_product_ids = set()
        for cp in customer_products:
            effective_barcode = cp.effective_barcode
            if effective_barcode:
                barcode_map[effective_barcode] = cp.product_id
                override_product_ids.add(cp.product_id)

        # Add remaining products with default barcodes
        remaining_products = Product.objects.filter(
            is_active=True
        ).exclude(id__in=override_product_ids)

        for p in remaining_products:
            if p.barcode and p.barcode not in barcode_map:
                barcode_map[p.barcode] = p.id

    return barcode_map


def find_product_by_barcode(barcode, customer=None):
    """
    Find product by barcode, considering customer-specific barcode overrides.

    Args:
        barcode: Barcode string to search for
        customer: Customer object or customer_id (optional)

    Returns:
        Product object or None
    """
    if not barcode:
        return None

    if customer is None:
        # No customer - use default barcode lookup
        return Product.objects.filter(barcode=barcode, is_active=True).first()

    # Get customer ID
    customer_id = customer.id if hasattr(customer, 'id') else customer

    # First check customer-specific barcode overrides
    cp = CustomerProduct.objects.filter(
        customer_id=customer_id,
        barcode_override=barcode
    ).select_related('product').first()

    if cp:
        return cp.product

    # Fall back to default barcode
    return Product.objects.filter(barcode=barcode, is_active=True).first()
