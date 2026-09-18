"""
Compensation Analytics Views
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth

from apps.claims.models import Compensation
from apps.core.models import Product, Customer, Store
from apps.ingestion.models import PurchaseOrderBatch


@login_required
def compensation_summary_dashboard(request):
    """Dashboard showing compensation analytics and trends"""

    # Filters
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    customer_id = request.GET.get("customer", "")
    store_id = request.GET.get("store", "")
    product_id = request.GET.get("product", "")

    # Base queryset
    qs = Compensation.objects.select_related('product', 'store', 'store__customer', 'purchase_order')

    # Apply filters
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if customer_id:
        qs = qs.filter(store__customer_id=customer_id)
    if store_id:
        qs = qs.filter(store_id=store_id)
    if product_id:
        qs = qs.filter(product_id=product_id)

    # Overall stats
    total_compensations = qs.aggregate(
        total_qty=Sum('qty'),
        total_count=Count('id')
    )

    # Top 10 most compensated products
    top_products = qs.values(
        'product__id',
        'product__barcode',
        'product__description',
        'product__image'
    ).annotate(
        total_qty=Sum('qty'),
        compensation_count=Count('id')
    ).order_by('-total_qty')[:10]

    # Monthly trend (last 12 months)
    monthly_trend = qs.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total_qty=Sum('qty'),
        compensation_count=Count('id')
    ).order_by('month')

    # Recent compensations (last 20)
    recent_compensations = qs.order_by('-created_at')[:20]

    # Filter options
    customers = Customer.objects.filter(is_active=True).order_by('name')
    stores = Store.objects.filter(is_active=True).select_related('customer').order_by('name')
    products = Product.objects.filter(is_active=True).order_by('description')

    context = {
        'total_compensations': total_compensations,
        'top_products': top_products,
        'monthly_trend': list(monthly_trend),
        'recent_compensations': recent_compensations,
        'customers': customers,
        'stores': stores,
        'products': products,
        'date_from': date_from,
        'date_to': date_to,
        'customer_filter': customer_id,
        'store_filter': store_id,
        'product_filter': product_id,
    }

    return render(request, 'dashboard/compensation_summary_dashboard.html', context)
