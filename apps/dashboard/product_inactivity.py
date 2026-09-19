"""
Product Inactivity Report - Track products not ordered by stores for extended periods
"""
from datetime import datetime, timedelta
from django.db.models import Max, Q
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.core.models import Product, Store, Customer, CustomerProduct
from apps.ingestion.models import POLineItem, PurchaseOrder


def get_last_order_dates(store, products, lookback_months=12):
    """
    Get the last order date for each product at a specific store.

    Returns:
        dict: {product_id: last_order_date or None}
    """
    lookback_date = timezone.now() - timedelta(days=lookback_months * 30)

    # Get all line items for this store within lookback period
    line_items = POLineItem.objects.filter(
        purchase_order__store=store,
        purchase_order__created_at__gte=lookback_date,
        product__in=products
    ).values('product_id').annotate(
        last_ordered=Max('purchase_order__created_at')
    )

    # Create lookup dict
    last_dates = {item['product_id']: item['last_ordered'] for item in line_items}

    # Fill in None for products never ordered
    result = {}
    for product in products:
        result[product.id] = last_dates.get(product.id)

    return result


def calculate_weeks_inactive(last_order_date):
    """Calculate how many weeks since last order."""
    if not last_order_date:
        return None  # Never ordered

    now = timezone.now()
    # Ensure both dates are timezone-aware
    if timezone.is_naive(last_order_date):
        last_order_date = timezone.make_aware(last_order_date)

    delta = now - last_order_date
    weeks = delta.days // 7
    return weeks


def get_alert_level(weeks_inactive):
    """
    Determine alert level based on weeks inactive.

    Returns:
        tuple: (level, css_class)
        - 'ok': < 2 weeks
        - 'warning': 2-4 weeks
        - 'alert': 4-8 weeks
        - 'critical': > 8 weeks
        - 'never': never ordered
    """
    if weeks_inactive is None:
        return ('never', 'bg-gray-100 text-gray-600')
    elif weeks_inactive < 2:
        return ('ok', '')
    elif weeks_inactive < 4:
        return ('warning', 'bg-yellow-50 text-yellow-800')
    elif weeks_inactive < 8:
        return ('alert', 'bg-orange-50 text-orange-800')
    else:
        return ('critical', 'bg-red-50 text-red-800')


@login_required
def product_inactivity_report(request):
    """
    Display a report of products not ordered by each store for extended periods.
    Products are filtered by customer - only shows products in that customer's catalog.
    """
    # Get filter parameters
    min_weeks = int(request.GET.get('min_weeks', 2))  # Minimum weeks to show
    lookback_months = int(request.GET.get('lookback_months', 12))  # How far back to check
    customer_filter = request.GET.get('customer')
    store_filter = request.GET.get('store')

    # Get all active customers
    customers = Customer.objects.filter(is_active=True)
    if customer_filter:
        customers = customers.filter(id=customer_filter)
    customers = customers.order_by('name')

    # Get all active stores
    all_stores = Store.objects.filter(is_active=True)
    if store_filter:
        all_stores = all_stores.filter(id=store_filter)

    # Build report data grouped by customer
    report_data = []

    for customer in customers:
        # Get products for this customer (only products they carry)
        customer_products = CustomerProduct.get_products_for_customer(customer)
        products = [cp['product'] for cp in customer_products]

        if not products:
            continue  # Skip customers with no products

        # Get stores for this customer
        customer_stores = all_stores.filter(customer=customer).order_by('name')

        store_data_list = []
        for store in customer_stores:
            last_order_dates = get_last_order_dates(store, products, lookback_months)

            inactive_products = []
            for product in products:
                last_date = last_order_dates.get(product.id)
                weeks_inactive = calculate_weeks_inactive(last_date)
                alert_level, css_class = get_alert_level(weeks_inactive)

                # Only include if meets minimum threshold or never ordered
                if weeks_inactive is None or weeks_inactive >= min_weeks:
                    inactive_products.append({
                        'product': product,
                        'last_ordered': last_date,
                        'weeks_inactive': weeks_inactive,
                        'alert_level': alert_level,
                        'css_class': css_class,
                    })

            # Sort by weeks inactive (descending), never ordered first
            inactive_products.sort(
                key=lambda x: (x['weeks_inactive'] is None, -(x['weeks_inactive'] or 0)),
                reverse=True
            )

            if inactive_products:  # Only include stores with inactive products
                store_data_list.append({
                    'store': store,
                    'inactive_products': inactive_products,
                    'total_inactive': len(inactive_products),
                })

        if store_data_list:  # Only include customers that have stores with inactive products
            report_data.append({
                'customer': customer,
                'stores': store_data_list,
                'total_products': len(products),
                'total_stores_with_issues': len(store_data_list),
            })

    context = {
        'report_data': report_data,
        'min_weeks': min_weeks,
        'lookback_months': lookback_months,
        'total_customers': len(report_data),
        'customers': Customer.objects.filter(is_active=True),
        'stores': Store.objects.filter(is_active=True).select_related('customer'),
    }

    return render(request, 'dashboard/product_inactivity_report.html', context)
