"""
Product trend analysis views for historical data analysis
"""
import re
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Sum, Avg, Count, Q
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from apps.core.framing import allow_embedding
from apps.core.models import Product, Store
from apps.ingestion.models import POLineItem, PurchaseOrderBatch

THAI_MONTHS = [
    'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
    'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม',
]


def _month_range(year, month):
    """Return aware [start, end) datetimes covering one calendar month."""
    tz = timezone.get_current_timezone()
    start = datetime(year, month, 1, tzinfo=tz)
    end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=tz)
    return start, end


def _shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


@allow_embedding
def product_trend_list(request):
    """Product summary for one calendar month (?month=YYYY-MM, default: current month)."""

    today = timezone.localdate()
    try:
        selected = datetime.strptime(request.GET.get('month', ''), '%Y-%m')
        year, month = selected.year, selected.month
    except ValueError:
        year, month = today.year, today.month

    start_date, end_date = _month_range(year, month)

    line_items = POLineItem.objects.filter(
        product__is_active=True,
        purchase_order__batch__uploaded_at__gte=start_date,
        purchase_order__batch__uploaded_at__lt=end_date,
    )

    rows = line_items.values('product').annotate(
        total_qty=Sum('qty2'),
        total_value=Sum('line_total'),
        avg_price=Avg('unit_amount'),
        order_count=Count('purchase_order__batch', distinct=True),
    )
    products = Product.objects.in_bulk([r['product'] for r in rows])

    product_stats = [{
        'product': products[r['product']],
        'total_qty': r['total_qty'] or 0,
        'total_value': r['total_value'] or 0,
        'order_count': r['order_count'],
        'avg_price': r['avg_price'] or 0,
    } for r in rows]
    product_stats.sort(key=lambda x: x['total_qty'], reverse=True)

    available_months = [
        d.strftime('%Y-%m') for d in
        PurchaseOrderBatch.objects.dates('uploaded_at', 'month', order='DESC')
    ]

    prev_year, prev_month = _shift_month(year, month, -1)
    next_year, next_month = _shift_month(year, month, 1)
    has_next = (next_year, next_month) <= (today.year, today.month)

    context = {
        'product_stats': product_stats,
        'selected_month': f'{year:04d}-{month:02d}',
        'month_label': f'{THAI_MONTHS[month - 1]} {year + 543}',
        'available_months': [
            (m, f'{THAI_MONTHS[int(m[5:]) - 1]} {int(m[:4]) + 543}') for m in available_months
        ],
        'prev_month': f'{prev_year:04d}-{prev_month:02d}',
        'next_month': f'{next_year:04d}-{next_month:02d}' if has_next else None,
        'start_date': start_date,
        'end_date': end_date - timedelta(days=1),
        'grand_total_qty': sum(p['total_qty'] for p in product_stats),
        'grand_total_value': sum(p['total_value'] for p in product_stats),
    }

    return render(request, 'dashboard/product_trend_list.html', context)


@allow_embedding
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
        'back_month': request.GET.get('month', '') if re.fullmatch(r'\d{4}-\d{2}', request.GET.get('month', '')) else '',
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


@allow_embedding
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
