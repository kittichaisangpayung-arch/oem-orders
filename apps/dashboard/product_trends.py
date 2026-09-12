"""
Product trend analysis views for historical data analysis
"""
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, Q
from django.shortcuts import render, get_object_or_404

from apps.core.models import Product, Store
from apps.ingestion.models import POLineItem, PurchaseOrderBatch


@login_required
def product_trend_list(request):
    """List all products with trend summary."""

    # Get date range filter (default: last 6 months)
    months = int(request.GET.get('months', 6))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months*30)

    # Get all products with orders in the period
    products = Product.objects.filter(
        is_active=True,
        line_items__purchase_order__batch__uploaded_at__gte=start_date
    ).distinct().order_by('sort_rank', 'barcode')

    product_stats = []

    for product in products:
        # Get line items for this product in the period
        line_items = POLineItem.objects.filter(
            product=product,
            purchase_order__batch__uploaded_at__gte=start_date
        )

        # Calculate statistics
        total_qty = line_items.aggregate(total=Sum('qty2'))['total'] or 0
        total_value = line_items.aggregate(total=Sum('line_total'))['total'] or 0
        order_count = line_items.values('purchase_order__batch_id').distinct().count()
        avg_price = line_items.aggregate(avg=Avg('unit_amount'))['avg'] or 0

        # Get last order date
        last_order = line_items.order_by('-purchase_order__batch__uploaded_at').first()
        last_order_date = last_order.purchase_order.batch.uploaded_at if last_order else None

        product_stats.append({
            'product': product,
            'total_qty': total_qty,
            'total_value': total_value,
            'order_count': order_count,
            'avg_price': avg_price,
            'last_order_date': last_order_date,
        })

    # Sort by total quantity (most ordered first)
    product_stats.sort(key=lambda x: x['total_qty'], reverse=True)

    context = {
        'product_stats': product_stats,
        'months': months,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'dashboard/product_trend_list.html', context)


@login_required
def product_trend_detail(request, product_id):
    """Detailed trend analysis for a specific product."""

    product = get_object_or_404(Product, pk=product_id)

    # Get date range filter (default: last 12 months)
    months = int(request.GET.get('months', 12))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months*30)

    # Get all line items for this product
    line_items = POLineItem.objects.filter(
        product=product,
        purchase_order__batch__uploaded_at__gte=start_date
    ).select_related('purchase_order__batch', 'purchase_order__store')

    # === Monthly Trend ===
    monthly_data = defaultdict(lambda: {
        'qty': 0,
        'value': Decimal('0'),
        'batches': set(),
        'stores': set()
    })

    for item in line_items:
        batch_date = item.purchase_order.batch.uploaded_at
        month_key = batch_date.strftime('%Y-%m')

        monthly_data[month_key]['qty'] += item.qty2 or 0
        monthly_data[month_key]['value'] += item.line_total or Decimal('0')
        monthly_data[month_key]['batches'].add(item.purchase_order.batch_id)
        if item.purchase_order.store:
            monthly_data[month_key]['stores'].add(item.purchase_order.store.name)

    # Convert to sorted list
    monthly_trend = []
    for month_key in sorted(monthly_data.keys()):
        data = monthly_data[month_key]
        monthly_trend.append({
            'month': month_key,
            'month_display': datetime.strptime(month_key, '%Y-%m').strftime('%B %Y'),
            'qty': data['qty'],
            'value': data['value'],
            'batch_count': len(data['batches']),
            'store_count': len(data['stores']),
            'avg_price': data['value'] / data['qty'] if data['qty'] > 0 else Decimal('0')
        })

    # === Store Distribution ===
    store_data = defaultdict(lambda: {'qty': 0, 'value': Decimal('0'), 'orders': 0})

    for item in line_items:
        if item.purchase_order.store:
            store_name = item.purchase_order.store.name
            store_data[store_name]['qty'] += item.qty2 or 0
            store_data[store_name]['value'] += item.line_total or Decimal('0')
            store_data[store_name]['orders'] += 1

    # Convert to sorted list (by quantity)
    store_distribution = []
    for store_name, data in store_data.items():
        store_distribution.append({
            'store': store_name,
            'qty': data['qty'],
            'value': data['value'],
            'orders': data['orders'],
            'avg_qty_per_order': data['qty'] / data['orders'] if data['orders'] > 0 else 0
        })
    store_distribution.sort(key=lambda x: x['qty'], reverse=True)

    # === Batch History ===
    batch_history = []
    batches = PurchaseOrderBatch.objects.filter(
        purchase_orders__line_items__product=product,
        uploaded_at__gte=start_date
    ).distinct().order_by('-uploaded_at')

    for batch in batches:
        batch_items = line_items.filter(purchase_order__batch=batch)
        total_qty = batch_items.aggregate(total=Sum('qty2'))['total'] or 0
        total_value = batch_items.aggregate(total=Sum('line_total'))['total'] or 0
        store_count = batch_items.values('purchase_order__store').distinct().count()

        batch_history.append({
            'batch': batch,
            'qty': total_qty,
            'value': total_value,
            'store_count': store_count,
            'avg_price': total_value / total_qty if total_qty > 0 else Decimal('0')
        })

    # === Summary Statistics ===
    total_qty = sum(item['qty'] for item in monthly_trend)
    total_value = sum(item['value'] for item in monthly_trend)
    avg_monthly_qty = total_qty / len(monthly_trend) if monthly_trend else 0

    # Calculate trend direction (last 3 months vs previous 3 months)
    trend_direction = 'stable'
    if len(monthly_trend) >= 6:
        recent_3_months = sum(m['qty'] for m in monthly_trend[-3:])
        previous_3_months = sum(m['qty'] for m in monthly_trend[-6:-3])

        if recent_3_months > previous_3_months * 1.1:
            trend_direction = 'increasing'
        elif recent_3_months < previous_3_months * 0.9:
            trend_direction = 'decreasing'

    context = {
        'product': product,
        'monthly_trend': monthly_trend,
        'store_distribution': store_distribution,
        'batch_history': batch_history,
        'months': months,
        'start_date': start_date,
        'end_date': end_date,
        'summary': {
            'total_qty': total_qty,
            'total_value': total_value,
            'avg_monthly_qty': avg_monthly_qty,
            'total_batches': len(batch_history),
            'total_stores': len(store_distribution),
            'trend_direction': trend_direction,
        }
    }

    return render(request, 'dashboard/product_trend_detail.html', context)


@login_required
def product_comparison(request):
    """Compare trends of multiple products side by side."""

    # Get selected product IDs
    product_ids = request.GET.getlist('products')
    months = int(request.GET.get('months', 6))

    if not product_ids:
        # Show product selection form
        products = Product.objects.filter(is_active=True).order_by('sort_rank', 'barcode')
        context = {
            'products': products,
            'months': months,
        }
        return render(request, 'dashboard/product_comparison_form.html', context)

    # Get comparison data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months*30)

    products = Product.objects.filter(id__in=product_ids)
    comparison_data = []

    for product in products:
        line_items = POLineItem.objects.filter(
            product=product,
            purchase_order__batch__uploaded_at__gte=start_date
        )

        monthly_data = defaultdict(int)
        for item in line_items:
            month_key = item.purchase_order.batch.uploaded_at.strftime('%Y-%m')
            monthly_data[month_key] += item.qty2 or 0

        total_qty = line_items.aggregate(total=Sum('qty2'))['total'] or 0
        total_value = line_items.aggregate(total=Sum('line_total'))['total'] or 0

        comparison_data.append({
            'product': product,
            'monthly_data': dict(monthly_data),
            'total_qty': total_qty,
            'total_value': total_value,
        })

    # Get all months for x-axis
    all_months = set()
    for data in comparison_data:
        all_months.update(data['monthly_data'].keys())
    all_months = sorted(all_months)

    context = {
        'comparison_data': comparison_data,
        'all_months': all_months,
        'months': months,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'dashboard/product_comparison.html', context)
