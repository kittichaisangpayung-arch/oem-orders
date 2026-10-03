"""
Product trend analysis views for historical data analysis
"""
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Sum, Avg, Count, Q
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.http import urlencode

from apps.core.framing import allow_embedding
from apps.core.models import Product, Store
from apps.ingestion.models import POLineItem, PurchaseOrderBatch

THAI_MONTHS = [
    'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
    'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม',
]
# Line charts use an 8-slot categorical palette; more series stop being distinguishable.
MAX_COMPARE_PRODUCTS = 8
DEFAULT_COMPARE_MONTHS = 6

THAI_MONTHS_SHORT = [
    'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
    'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.',
]


def _month_range(year, month):
    """Return aware [start, end) datetimes covering one calendar month."""
    tz = timezone.get_current_timezone()
    start = datetime(year, month, 1, tzinfo=tz)
    end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=tz)
    return start, end


def _month_label(key):
    year, month = int(key[:4]), int(key[5:])
    return f'{THAI_MONTHS[month - 1]} {year + 543}'


def _selected_months(request):
    """Valid, de-duplicated ?month=YYYY-MM values, newest first."""
    months = set()
    for value in request.GET.getlist('month'):
        try:
            months.add(datetime.strptime(value, '%Y-%m').strftime('%Y-%m'))
        except ValueError:
            continue
    return sorted(months, reverse=True)


def _year_groups(data_months, selected_months):
    """Month picker grouped by year (newest first), all 12 months per year.

    Months without data are disabled unless already selected.
    """
    years = {int(m[:4]) for m in data_months | set(selected_months)}
    return [
        {
            'year': year,
            'label': year + 543,
            'months': [
                {
                    'value': key,
                    'label': THAI_MONTHS_SHORT[month - 1],
                    'title': _month_label(key),
                    'selected': key in selected_months,
                    'enabled': key in data_months or key in selected_months,
                }
                for month in range(1, 13)
                for key in [f'{year}-{month:02d}']
            ],
        }
        for year in sorted(years, reverse=True)
    ]


@allow_embedding
def product_trend_list(request):
    """Product summary for one or more calendar months (?month=YYYY-MM&month=..., default: current month)."""

    selected_months = _selected_months(request) or [timezone.localdate().strftime('%Y-%m')]

    stats = {}
    for key in selected_months:
        start, end = _month_range(int(key[:4]), int(key[5:]))
        rows = POLineItem.objects.filter(
            product__is_active=True,
            purchase_order__batch__uploaded_at__gte=start,
            purchase_order__batch__uploaded_at__lt=end,
        ).values('product').annotate(
            qty=Sum('qty2'),
            value=Sum('line_total'),
            price_sum=Sum('unit_amount'),
            line_count=Count('id'),
            order_count=Count('purchase_order__batch', distinct=True),
        )
        for r in rows:
            s = stats.setdefault(r['product'], {
                'total_qty': 0, 'total_value': 0, 'price_sum': 0,
                'line_count': 0, 'order_count': 0, 'by_month': {},
            })
            s['total_qty'] += r['qty'] or 0
            s['total_value'] += r['value'] or 0
            s['price_sum'] += r['price_sum'] or 0
            s['line_count'] += r['line_count']
            s['order_count'] += r['order_count']
            s['by_month'][key] = r['qty'] or 0

    products = Product.objects.in_bulk(stats.keys())
    product_stats = []
    for product_id, s in stats.items():
        product_stats.append({
            'product': products[product_id],
            'total_qty': s['total_qty'],
            'total_value': s['total_value'],
            'order_count': s['order_count'],
            'avg_price': s['price_sum'] / s['line_count'] if s['line_count'] else 0,
            'monthly': [
                (_month_label(key), s['by_month'].get(key, 0)) for key in reversed(selected_months)
            ],
        })
    product_stats.sort(key=lambda x: x['total_qty'], reverse=True)

    data_months = {
        d.strftime('%Y-%m') for d in PurchaseOrderBatch.objects.dates('uploaded_at', 'month')
    }

    context = {
        'product_stats': product_stats,
        'selected_months': selected_months,
        'selected_labels': [_month_label(m) for m in reversed(selected_months)],
        'month_query': urlencode([('month', m) for m in selected_months]),
        'year_groups': _year_groups(data_months, selected_months),
        'active_year': int(selected_months[0][:4]),
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
        'back_query': urlencode([('month', m) for m in _selected_months(request)]),
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


def _selected_product_ids(request):
    """Valid ?products=<id> values in the order given, de-duplicated, capped."""
    ids = []
    for value in request.GET.getlist('products'):
        if value.isdigit() and int(value) not in ids:
            ids.append(int(value))
    return ids[:MAX_COMPARE_PRODUCTS]


@allow_embedding
def product_comparison(request):
    """Monthly trend of several products side by side (?products=<id>&month=YYYY-MM...)."""

    data_months = {
        d.strftime('%Y-%m') for d in PurchaseOrderBatch.objects.dates('uploaded_at', 'month')
    }
    selected_months = _selected_months(request) or (
        sorted(data_months, reverse=True)[:DEFAULT_COMPARE_MONTHS]
        or [timezone.localdate().strftime('%Y-%m')]
    )
    months_asc = sorted(selected_months)
    metric = 'value' if request.GET.get('metric') == 'value' else 'qty'

    products = Product.objects.in_bulk(_selected_product_ids(request))
    product_ids = [pid for pid in _selected_product_ids(request) if pid in products]

    by_product = {pid: {} for pid in product_ids}
    if product_ids:
        for key in months_asc:
            start, end = _month_range(int(key[:4]), int(key[5:]))
            rows = POLineItem.objects.filter(
                product_id__in=product_ids,
                purchase_order__batch__uploaded_at__gte=start,
                purchase_order__batch__uploaded_at__lt=end,
            ).values('product').annotate(qty=Sum('qty2'), value=Sum('line_total'))
            for r in rows:
                by_product[r['product']][key] = {'qty': r['qty'] or 0, 'value': r['value'] or 0}

    empty = {'qty': 0, 'value': 0}
    series = []
    for index, pid in enumerate(product_ids):
        months = [by_product[pid].get(key, empty) for key in months_asc]
        series.append({
            'product': products[pid],
            'slot': index + 1,
            'points': months,
            'chart_values': [float(m[metric]) for m in months],
            'total_qty': sum(m['qty'] for m in months),
            'total_value': sum(m['value'] for m in months),
        })

    table_rows = [
        {'label': _month_label(key), 'cells': [s['points'][i] for s in series]}
        for i, key in enumerate(months_asc)
    ]

    context = {
        'series': series,
        'table_rows': table_rows,
        'metric': metric,
        'selected_months': selected_months,
        'selected_labels': [_month_label(m) for m in months_asc],
        'chart_labels': [_month_label(m) for m in months_asc],
        'chart_series': [
            {'label': s['product'].description, 'slot': s['slot'], 'values': s['chart_values']}
            for s in series
        ],
        'year_groups': _year_groups(data_months, selected_months),
        'active_year': int(selected_months[0][:4]),
        'month_query': urlencode([('month', m) for m in selected_months]),
        'selected_product_ids': product_ids,
        'all_products': Product.objects.filter(is_active=True).order_by('sort_rank', 'barcode'),
        'max_products': MAX_COMPARE_PRODUCTS,
    }

    return render(request, 'dashboard/product_comparison.html', context)
