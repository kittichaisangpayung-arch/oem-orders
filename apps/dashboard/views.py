from collections import defaultdict
from decimal import Decimal
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse

from apps.claims.models import Claim
from apps.core.access import staff_required
from apps.core.models import Customer, Factory, Product, Store
from apps.ingestion.models import POLineItem, PurchaseOrder, PurchaseOrderBatch

from .models import StoreProductOverride, DeliveryNote, DeliveryNoteItem, Invoice, InvoiceLineItem


@login_required
def executive_dashboard(request):
    """Executive dashboard with key metrics and insights"""
    from django.utils import timezone
    from datetime import date

    # Date range filter
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Delivery Notes Summary
    dn_stats = DeliveryNote.objects.aggregate(
        total=Count('id'),
        draft=Count('id', filter=Q(status='DRAFT')),
        confirmed=Count('id', filter=Q(status='CONFIRMED')),
        delivered=Count('id', filter=Q(status='DELIVERED')),
        total_value=Sum('grand_total')
    )

    # Invoice Summary
    invoice_stats = Invoice.objects.aggregate(
        total=Count('id'),
        draft=Count('id', filter=Q(status='DRAFT')),
        confirmed=Count('id', filter=Q(status='CONFIRMED')),
        total_value=Sum('grand_total')
    )

    # Recent Delivery Notes (last 30 days)
    recent_dns = DeliveryNote.objects.filter(
        created_at__gte=start_date
    ).aggregate(
        count=Count('id'),
        value=Sum('grand_total')
    )

    # Recent Invoices (last 30 days)
    recent_invoices = Invoice.objects.filter(
        created_at__gte=start_date
    ).aggregate(
        count=Count('id'),
        value=Sum('grand_total')
    )

    # Top Customers by Delivery Note Value
    top_customers = (
        DeliveryNote.objects
        .values('store__customer__name')
        .annotate(
            total_value=Sum('grand_total'),
            dn_count=Count('id')
        )
        .order_by('-total_value')[:10]
    )

    # Monthly Sales Trend (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month_date = date.today().replace(day=1) - timedelta(days=i*30)
        month_start = month_date.replace(day=1)
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)

        month_dns = DeliveryNote.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).aggregate(
            count=Count('id'),
            value=Sum('grand_total')
        )

        monthly_data.append({
            'month': month_date.strftime('%b %Y'),
            'dn_count': month_dns['count'] or 0,
            'dn_value': month_dns['value'] or 0,
        })

    # Top Products by Quantity (from Delivery Notes)
    top_products = (
        DeliveryNoteItem.objects
        .values('product__description', 'product__barcode')
        .annotate(
            total_qty=Sum('quantity'),
            total_value=Sum('amount')
        )
        .order_by('-total_qty')[:10]
    )

    # Active Batches
    active_batches = PurchaseOrderBatch.objects.order_by('-uploaded_at')[:5]

    # Recent Activity
    recent_dns_list = DeliveryNote.objects.select_related('store', 'store__customer').order_by('-created_at')[:10]
    recent_invoices_list = Invoice.objects.select_related('customer').order_by('-created_at')[:10]

    context = {
        'days': days,
        'dn_stats': dn_stats,
        'invoice_stats': invoice_stats,
        'recent_dns': recent_dns,
        'recent_invoices': recent_invoices,
        'top_customers': top_customers,
        'monthly_data': monthly_data,
        'top_products': top_products,
        'active_batches': active_batches,
        'recent_dns_list': recent_dns_list,
        'recent_invoices_list': recent_invoices_list,
    }

    return render(request, 'dashboard/executive_dashboard.html', context)


def _filter_line_items(request):
    qs = POLineItem.objects.select_related("product", "purchase_order", "purchase_order__store")

    batch_id = request.GET.get("batch")
    customer_id = request.GET.get("customer")
    store_id = request.GET.get("store")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if batch_id:
        qs = qs.filter(purchase_order__batch_id=batch_id)
    if customer_id:
        qs = qs.filter(purchase_order__customer_id=customer_id)
    if store_id:
        qs = qs.filter(purchase_order__store_id=store_id)
    if date_from:
        qs = qs.filter(purchase_order__batch__uploaded_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(purchase_order__batch__uploaded_at__date__lte=date_to)

    return qs


def _filter_claims(request):
    qs = Claim.objects.filter(purchase_order__isnull=False)

    batch_id = request.GET.get("batch")
    customer_id = request.GET.get("customer")
    store_id = request.GET.get("store")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if batch_id:
        qs = qs.filter(purchase_order__batch_id=batch_id)
    if customer_id:
        qs = qs.filter(purchase_order__customer_id=customer_id)
    if store_id:
        qs = qs.filter(purchase_order__store_id=store_id)
    if date_from:
        qs = qs.filter(purchase_order__batch__uploaded_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(purchase_order__batch__uploaded_at__date__lte=date_to)

    return qs


def _claimed_totals(request):
    """Returns (by_product, by_product_store) claimed-qty maps for the same
    filter params as _filter_line_items, so claims can be netted against
    production totals before they're sent to the factory."""
    qs = _filter_claims(request)

    by_product = defaultdict(int)
    for row in qs.values("product_id").annotate(total=Sum("qty")):
        by_product[row["product_id"]] += row["total"] or 0

    by_product_store = defaultdict(int)
    for row in qs.values("product_id", "store_id").annotate(total=Sum("qty")):
        by_product_store[(row["product_id"], row["store_id"])] += row["total"] or 0

    return by_product, by_product_store


@login_required
def production_summary(request):
    qs = _filter_line_items(request)

    # Get customer_id from filter
    customer_id = request.GET.get("customer")
    batch_id = request.GET.get("batch")

    # If batch is selected, get customer from batch
    selected_customer = None
    if batch_id:
        batch = PurchaseOrderBatch.objects.filter(pk=batch_id).first()
        if batch:
            selected_customer = batch.customer
    elif customer_id:
        selected_customer = Customer.objects.filter(pk=customer_id).first()

    # Get customer-specific barcodes if customer is selected
    customer_barcodes = {}
    if selected_customer:
        from apps.core.models import CustomerProduct
        cp_list = CustomerProduct.objects.filter(
            customer=selected_customer
        ).select_related('product')
        for cp in cp_list:
            if cp.barcode_override:
                customer_barcodes[cp.product_id] = cp.barcode_override

    # Build matrix like store_matrix to calculate adjusted quantities per store
    rows = qs.values(
        "product__id", "product__barcode", "product__description",
        "product__sort_rank", "product__min_order_qty", "product__image",
        "purchase_order__store__id",
    ).annotate(total_qty2=Sum("qty2"))

    products = {}
    matrix = defaultdict(dict)
    stores = set()

    for row in rows:
        store_id = row["purchase_order__store__id"]
        product_id = row["product__id"]
        stores.add(store_id)

        if product_id not in products:
            # Use customer-specific barcode if available
            effective_barcode = customer_barcodes.get(product_id) or row["product__barcode"] or "(unmapped)"

            products[product_id] = {
                "id": product_id,
                "barcode": effective_barcode,
                "description": row["product__description"] or "",
                "sort_rank": row["product__sort_rank"],
                "min_order_qty": row["product__min_order_qty"] or 0,
                "image": row["product__image"],
            }

        matrix[product_id][store_id] = row["total_qty2"]

    claimed_by_product, claimed_by_product_store = _claimed_totals(request)

    # Check for claims that create new product/store pairs
    for pid, sid in claimed_by_product_store:
        stores.add(sid)
        if pid is not None and pid not in products:
            product = Product.objects.filter(pk=pid).first()
            if product:
                # Use customer-specific barcode if available
                effective_barcode = customer_barcodes.get(pid) or product.barcode

                products[pid] = {
                    "id": pid,
                    "barcode": effective_barcode,
                    "description": product.description,
                    "sort_rank": product.sort_rank,
                    "min_order_qty": product.min_order_qty or 0,
                    "image": product.image.url if product.image else None,
                }

    single_batch_id = request.GET.get("batch") or None
    overrides = {}
    if single_batch_id:
        for o in StoreProductOverride.objects.filter(purchase_order_batch_id=single_batch_id):
            overrides[(o.product_id, o.store_id)] = o.override_qty

    # Calculate totals per product, applying min qty and overrides per store
    totals = []
    for pid, p in products.items():
        original_total = 0
        adjusted_total = 0
        claimed_total = claimed_by_product.get(pid, 0)
        has_override = False
        has_adjustment = False

        for sid in stores:
            qty = matrix[pid].get(sid, 0)
            claimed = claimed_by_product_store.get((pid, sid), 0)
            net_qty = qty + claimed
            minimum = p["min_order_qty"]

            original_total += qty

            # Apply override or minimum adjustment per store
            if (pid, sid) in overrides:
                adjusted_total += overrides[(pid, sid)]
                has_override = True
            elif qty > 0 and net_qty > 0 and minimum > 0 and net_qty < minimum:
                # Only apply minimum if store actually ordered (qty > 0)
                adjusted_total += minimum
                has_adjustment = True
            else:
                adjusted_total += net_qty

        totals.append({
            "product__id": pid,
            "product__barcode": p["barcode"],
            "product__description": p["description"],
            "product__sort_rank": p["sort_rank"],
            "product__image": p["image"],
            "original_qty": original_total,
            "claimed_qty": claimed_total,
            "net_qty2": adjusted_total,
            "overridden": has_override,
            "adjusted": has_adjustment,
        })

    # Sort by rank and barcode
    totals.sort(key=lambda x: (x["product__sort_rank"] is None, x["product__sort_rank"] or 0, x["product__barcode"]))

    unmapped_total = qs.filter(product__isnull=True).aggregate(total=Sum("qty2"))["total"] or 0

    context = {
        "totals": totals,
        "unmapped_total": unmapped_total,
        "batches": PurchaseOrderBatch.objects.order_by("-uploaded_at")[:30],
        "customers": Customer.objects.filter(is_active=True),
        "stores": Store.objects.filter(is_active=True),
    }
    return render(request, "dashboard/production.html", context)


@login_required
def store_matrix(request):
    qs = _filter_line_items(request)

    # Get customer_id from filter
    customer_id = request.GET.get("customer")
    batch_id = request.GET.get("batch")

    # If batch is selected, get customer from batch
    selected_customer = None
    if batch_id:
        batch = PurchaseOrderBatch.objects.filter(pk=batch_id).first()
        if batch:
            selected_customer = batch.customer
    elif customer_id:
        selected_customer = Customer.objects.filter(pk=customer_id).first()

    rows = qs.values(
        "product__id", "product__barcode", "product__description",
        "product__sort_rank", "product__min_order_qty", "product__image",
        "purchase_order__store__id", "purchase_order__store__name",
    ).annotate(total_qty2=Sum("qty2"), total_line_amount=Sum("line_total"))

    money_rows = qs.values(
        "purchase_order__store__id", "purchase_order__store__name",
    ).annotate(total_amount=Sum("line_total"))

    stores = {}
    products = {}
    matrix = defaultdict(dict)
    price_matrix = defaultdict(dict)

    # Get customer-specific barcodes if customer is selected
    customer_barcodes = {}
    if selected_customer:
        from apps.core.models import CustomerProduct
        cp_list = CustomerProduct.objects.filter(
            customer=selected_customer
        ).select_related('product')
        for cp in cp_list:
            if cp.barcode_override:
                customer_barcodes[cp.product_id] = cp.barcode_override

    for row in rows:
        store_id = row["purchase_order__store__id"]
        store_name = row["purchase_order__store__name"] or "(Unmapped store)"
        product_id = row["product__id"]

        if store_id not in stores:
            stores[store_id] = store_name

        if product_id not in products:
            # Use customer-specific barcode if available
            effective_barcode = customer_barcodes.get(product_id) or row["product__barcode"] or "(unmapped)"

            products[product_id] = {
                "id": product_id,
                "barcode": effective_barcode,
                "description": row["product__description"] or "",
                "sort_rank": row["product__sort_rank"],
                "min_order_qty": row["product__min_order_qty"] or 0,
                "image": row["product__image"],
            }

        qty = row["total_qty2"]
        amount = row["total_line_amount"] or 0
        matrix[product_id][store_id] = qty

        # Calculate average unit price for this product-store combination
        if qty > 0:
            price_matrix[product_id][store_id] = amount / qty
        else:
            price_matrix[product_id][store_id] = 0

    store_money = {}
    for row in money_rows:
        store_id = row["purchase_order__store__id"]
        store_name = row["purchase_order__store__name"] or "(Unmapped store)"
        if store_id not in stores:
            stores[store_id] = store_name
        store_money[store_id] = row["total_amount"] or 0

    _, claimed_by_product_store = _claimed_totals(request)

    # A claim can turn a never-ordered product/store pair into a real qty --
    # make sure such pairs still surface as a row/column even if no
    # POLineItem exists for them.
    for pid, sid in claimed_by_product_store:
        if sid is not None and sid not in stores:
            store = Store.objects.filter(pk=sid).first()
            stores[sid] = store.name if store else "(Unmapped store)"
        if pid is not None and pid not in products:
            product = Product.objects.filter(pk=pid).first()
            if product:
                # Use customer-specific barcode if available
                effective_barcode = customer_barcodes.get(pid) or product.barcode

                products[pid] = {
                    "id": pid,
                    "barcode": effective_barcode,
                    "description": product.description,
                    "sort_rank": product.sort_rank,
                    "min_order_qty": product.min_order_qty or 0,
                    "image": product.image.url if product.image else None,
                }

    sorted_store_ids = sorted(stores, key=lambda sid: stores[sid])
    sorted_product_ids = sorted(
        products, key=lambda pid: (products[pid]["sort_rank"] is None, products[pid]["sort_rank"] or 0, products[pid]["barcode"])
    )

    single_batch_id = request.GET.get("batch") or None
    overrides = {}
    if single_batch_id:
        for o in StoreProductOverride.objects.filter(purchase_order_batch_id=single_batch_id):
            overrides[(o.product_id, o.store_id)] = o.override_qty

    # Calculate adjusted totals per store
    store_adjusted_totals = defaultdict(int)
    store_adjusted_amounts = defaultdict(Decimal)

    table_rows = []
    for pid in sorted_product_ids:
        p = products[pid]
        cells = []
        for sid in sorted_store_ids:
            qty = matrix[pid].get(sid, 0)
            claimed = claimed_by_product_store.get((pid, sid), 0)
            net_qty = qty + claimed
            minimum = p["min_order_qty"]
            unit_price = price_matrix[pid].get(sid, 0)

            overridden = (pid, sid) in overrides
            if overridden:
                display_qty = overrides[(pid, sid)]
                adjusted = False
            elif qty > 0 and net_qty > 0 and minimum > 0 and net_qty < minimum:
                # Only apply minimum if store actually ordered (qty > 0)
                display_qty = minimum
                adjusted = True
            else:
                display_qty = net_qty
                adjusted = False

            # For adjusted amount calculation: use original qty adjusted to minimum (not including claims)
            if overridden:
                adjusted_qty_for_amount = overrides[(pid, sid)]
            elif qty > 0 and minimum > 0 and qty < minimum:
                adjusted_qty_for_amount = minimum
            else:
                adjusted_qty_for_amount = qty

            # Accumulate adjusted quantity (display_qty includes claims) and amount (without claims)
            store_adjusted_totals[sid] += display_qty
            store_adjusted_amounts[sid] += Decimal(str(adjusted_qty_for_amount)) * Decimal(str(unit_price))

            cells.append({
                "qty": display_qty,
                "original_qty": qty,
                "claimed_qty": claimed,
                "adjusted": adjusted,
                "overridden": overridden,
                "product_id": pid,
                "store_id": sid,
            })
        table_rows.append({"product": p, "cells": cells})

    store_totals = [
        {
            "name": stores[sid],
            "total_amount": store_money.get(sid, 0),
            "adjusted_total": store_adjusted_totals.get(sid, 0),
            "adjusted_amount": store_adjusted_amounts.get(sid, 0)
        }
        for sid in sorted_store_ids
    ]
    grand_total = sum(store_money.values())
    grand_adjusted_total = sum(store_adjusted_totals.values())
    grand_adjusted_amount = sum(store_adjusted_amounts.values())

    # Prepare store list with id and name for claim form
    store_list = [{"id": sid, "name": stores[sid]} for sid in sorted_store_ids]

    context = {
        "store_names": [stores[sid] for sid in sorted_store_ids],
        "store_ids": sorted_store_ids,
        "store_list": store_list,
        "table_rows": table_rows,
        "store_totals": store_totals,
        "grand_total": grand_total,
        "grand_adjusted_total": grand_adjusted_total,
        "grand_adjusted_amount": grand_adjusted_amount,
        "batches": PurchaseOrderBatch.objects.order_by("-uploaded_at")[:30],
        "customers": Customer.objects.filter(is_active=True),
        "stores": Store.objects.filter(is_active=True),
        "single_batch_id": single_batch_id,
        "can_override": bool(single_batch_id) and staff_required(request.user),
    }
    return render(request, "dashboard/store_matrix.html", context)


@login_required
def set_override(request):
    if request.method != "POST" or not staff_required(request.user):
        return render(request, "claims/forbidden.html", status=403)

    batch_id = request.POST.get("batch")
    product_id = request.POST.get("product_id")
    store_id = request.POST.get("store_id")
    override_qty = request.POST.get("override_qty")

    if batch_id and product_id and store_id and override_qty is not None:
        StoreProductOverride.objects.update_or_create(
            purchase_order_batch_id=batch_id,
            product_id=product_id,
            store_id=store_id,
            defaults={"override_qty": override_qty, "updated_by": request.user},
        )

    return redirect(f"{reverse('dashboard:store_matrix')}?batch={batch_id}")


@login_required
def add_claim_inline(request):
    """Add claim directly from store matrix table."""
    if request.method != "POST":
        return redirect("dashboard:store_matrix")

    batch_id = request.POST.get("batch")
    product_id = request.POST.get("product_id")
    store_id = request.POST.get("store_id")
    claim_qty = request.POST.get("claim_qty")

    print(f"DEBUG: Received - batch_id={batch_id}, product_id={product_id}, store_id={store_id}, claim_qty={claim_qty}")

    if batch_id and product_id and store_id and claim_qty:
        try:
            from apps.claims.models import Claim

            claim_qty = int(claim_qty)
            print(f"DEBUG: Parsed claim_qty={claim_qty}")

            if claim_qty > 0:
                # Get ANY purchase order for this batch and store
                po = PurchaseOrder.objects.filter(
                    batch_id=batch_id,
                    store_id=store_id
                ).first()

                print(f"DEBUG: Found PurchaseOrder: {po}")

                if po:
                    claim = Claim.objects.create(
                        purchase_order=po,
                        store_id=store_id,
                        product_id=product_id,
                        qty=claim_qty,
                        note=f"Added from store matrix (batch #{batch_id})",
                        created_by=request.user,
                    )
                    print(f"DEBUG: Claim created successfully: {claim.id}")
                else:
                    print(f"DEBUG: No PurchaseOrder found for batch={batch_id}, store={store_id}")
            else:
                print(f"DEBUG: claim_qty is not > 0")
        except Exception as e:
            print(f"DEBUG: Exception occurred - {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    return redirect(f"{reverse('dashboard:store_matrix')}?batch={batch_id}")


@login_required
def factory_summary(request):
    """Production summary grouped by product group."""
    qs = _filter_line_items(request)

    # Get customer_id from filter
    customer_id = request.GET.get("customer")
    batch_id = request.GET.get("batch")

    # If batch is selected, get customer from batch
    selected_customer = None
    if batch_id:
        batch = PurchaseOrderBatch.objects.filter(pk=batch_id).first()
        if batch:
            selected_customer = batch.customer
    elif customer_id:
        selected_customer = Customer.objects.filter(pk=customer_id).first()

    # Get customer-specific barcodes if customer is selected
    customer_barcodes = {}
    if selected_customer:
        from apps.core.models import CustomerProduct
        cp_list = CustomerProduct.objects.filter(
            customer=selected_customer
        ).select_related('product')
        for cp in cp_list:
            if cp.barcode_override:
                customer_barcodes[cp.product_id] = cp.barcode_override

    # Filter by product group if specified
    group_filter = request.GET.get("group")
    if group_filter:
        qs = qs.filter(product__product_group=group_filter)

    # Build matrix like store_matrix to calculate adjusted quantities per store
    rows = qs.values(
        "product__id",
        "product__barcode",
        "product__description",
        "product__sort_rank",
        "product__product_group",
        "product__min_order_qty",
        "product__image",
        "purchase_order__store__id",
    ).annotate(total_qty2=Sum("qty2"))

    products = {}
    matrix = defaultdict(dict)
    stores = set()

    for row in rows:
        store_id = row["purchase_order__store__id"]
        product_id = row["product__id"]
        stores.add(store_id)

        if product_id not in products:
            # Use customer-specific barcode if available
            effective_barcode = customer_barcodes.get(product_id) or row["product__barcode"] or "(unmapped)"

            products[product_id] = {
                "id": product_id,
                "barcode": effective_barcode,
                "description": row["product__description"],
                "sort_rank": row["product__sort_rank"],
                "product_group": row["product__product_group"],
                "min_order_qty": row["product__min_order_qty"] or 0,
                "image": row["product__image"],
            }

        matrix[product_id][store_id] = row["total_qty2"]

    claimed_by_product, claimed_by_product_store = _claimed_totals(request)

    # Check for claims that create new product/store pairs
    for pid, sid in claimed_by_product_store:
        stores.add(sid)
        if pid is not None and pid not in products:
            product = Product.objects.filter(pk=pid).first()
            if product:
                # Use customer-specific barcode if available
                effective_barcode = customer_barcodes.get(pid) or product.barcode

                products[pid] = {
                    "id": pid,
                    "barcode": effective_barcode,
                    "description": product.description,
                    "sort_rank": product.sort_rank,
                    "product_group": product.product_group,
                    "min_order_qty": product.min_order_qty or 0,
                    "image": product.image.url if product.image else None,
                }

    single_batch_id = request.GET.get("batch") or None
    overrides = {}
    if single_batch_id:
        for o in StoreProductOverride.objects.filter(purchase_order_batch_id=single_batch_id):
            overrides[(o.product_id, o.store_id)] = o.override_qty

    # Calculate totals per product, applying min qty and overrides per store
    groups_data = defaultdict(lambda: {"products": [], "total_qty": 0})

    for pid, p in products.items():
        original_total = 0
        adjusted_total_before_claim = 0
        claimed_total = claimed_by_product.get(pid, 0)

        for sid in stores:
            qty = matrix[pid].get(sid, 0)
            claimed = claimed_by_product_store.get((pid, sid), 0)
            net_qty = qty + claimed
            minimum = p["min_order_qty"]

            original_total += qty

            # Apply override or minimum adjustment per store (before adding claims to final)
            if (pid, sid) in overrides:
                adjusted_total_before_claim += overrides[(pid, sid)]
            elif qty > 0 and minimum > 0 and qty < minimum:
                # Only apply minimum if store actually ordered (qty > 0)
                # Adjust based on original qty only, not including claims yet
                adjusted_total_before_claim += minimum
            else:
                adjusted_total_before_claim += qty

        # Final net qty = adjusted order qty + claims
        final_net_qty = adjusted_total_before_claim + claimed_total

        group_name = p["product_group"] or "ไม่ระบุกลุ่ม"

        product_data = {
            "id": pid,
            "barcode": p["barcode"],
            "description": p["description"],
            "image": p["image"],
            "total_qty2": adjusted_total_before_claim,  # Adjusted order qty (after min adjustment)
            "claimed_qty": claimed_total,
            "net_qty2": final_net_qty,  # Adjusted + claims
        }

        groups_data[group_name]["group_name"] = group_name
        groups_data[group_name]["products"].append(product_data)
        groups_data[group_name]["total_qty"] += final_net_qty

    # Sort products within each group
    for group_data in groups_data.values():
        group_data["products"].sort(key=lambda p: (p["barcode"] or ""))

    # Convert to list and sort by group name
    groups_list = sorted(groups_data.values(), key=lambda g: g["group_name"])

    # Get all unique product groups for filter
    all_groups = Product.objects.filter(is_active=True).exclude(product_group="").values_list("product_group", flat=True).distinct().order_by("product_group")

    unmapped_total = qs.filter(product__isnull=True).aggregate(total=Sum("qty2"))["total"] or 0

    context = {
        "groups": groups_list,
        "unmapped_total": unmapped_total,
        "batches": PurchaseOrderBatch.objects.order_by("-uploaded_at")[:30],
        "customers": Customer.objects.filter(is_active=True),
        "stores": Store.objects.filter(is_active=True),
        "all_groups": all_groups,
    }
    return render(request, "dashboard/factory_summary.html", context)


@login_required
def shipping_summary(request):
    """Shipping summary table showing all stores and products for logistics department"""
    qs = _filter_line_items(request)

    # Get filter parameters
    batch_id = request.GET.get("batch")
    customer_id = request.GET.get("customer")

    # Get selected customer
    selected_customer = None
    if batch_id:
        batch = PurchaseOrderBatch.objects.filter(pk=batch_id).first()
        if batch:
            selected_customer = batch.customer
    elif customer_id:
        selected_customer = Customer.objects.filter(pk=customer_id).first()

    # Get customer-specific barcodes if customer is selected
    customer_barcodes = {}
    if selected_customer:
        from apps.core.models import CustomerProduct
        cp_list = CustomerProduct.objects.filter(
            customer=selected_customer
        ).select_related('product')
        for cp in cp_list:
            if cp.barcode_override:
                customer_barcodes[cp.product_id] = cp.barcode_override

    rows = qs.values(
        "product__id", "product__barcode", "product__description",
        "product__sort_rank", "product__min_order_qty", "product__image",
        "purchase_order__store__id", "purchase_order__store__name",
    ).annotate(total_qty2=Sum("qty2"), total_line_amount=Sum("line_total"))

    # Initialize stores and products dictionaries
    stores = {}
    products = {}
    matrix = defaultdict(dict)

    # Load products based on customer filter
    if selected_customer:
        # If customer is selected, only show products that have orders or have CustomerProduct entries
        from apps.core.models import CustomerProduct

        # Get products from orders
        ordered_product_ids = set(qs.values_list('product_id', flat=True).distinct())

        # Get products with customer-specific settings
        customer_product_ids = set(
            CustomerProduct.objects.filter(customer=selected_customer)
            .values_list('product_id', flat=True)
        )

        # Combine both sets
        relevant_product_ids = ordered_product_ids | customer_product_ids
        all_products = Product.objects.filter(is_active=True, id__in=relevant_product_ids)
    else:
        # No customer filter - show all active products
        all_products = Product.objects.filter(is_active=True)

    for product in all_products:
        # Use customer-specific barcode if available
        effective_barcode = customer_barcodes.get(product.id) or product.barcode or "(unmapped)"

        products[product.id] = {
            "id": product.id,
            "barcode": effective_barcode,
            "description": product.description or "",
            "sort_rank": product.sort_rank,
            "min_order_qty": product.min_order_qty or 0,
            "image": product.image.name if product.image else None,
        }

    # Load all active stores based on filters
    if customer_id:
        # Show only stores for selected customer
        all_stores = Store.objects.filter(is_active=True, customer_id=customer_id)
    elif batch_id:
        # Show stores that have POs in this batch
        batch_store_ids = PurchaseOrder.objects.filter(batch_id=batch_id).values_list('store_id', flat=True).distinct()
        all_stores = Store.objects.filter(is_active=True, id__in=batch_store_ids)
    else:
        # Show all active stores
        all_stores = Store.objects.filter(is_active=True)

    for store in all_stores:
        stores[store.id] = store.name

    # Fill matrix with ordered quantities
    for row in rows:
        store_id = row["purchase_order__store__id"]
        product_id = row["product__id"]

        if product_id and store_id:
            qty = row["total_qty2"]
            matrix[product_id][store_id] = qty

    _, claimed_by_product_store = _claimed_totals(request)

    # Add stores from claims that might not be in the initial store list
    for pid, sid in claimed_by_product_store:
        if sid is not None and sid not in stores:
            store = Store.objects.filter(pk=sid).first()
            if store and store.is_active:
                stores[sid] = store.name

    sorted_store_ids = sorted(stores, key=lambda sid: stores[sid])
    sorted_product_ids = sorted(
        products, key=lambda pid: (products[pid]["sort_rank"] is None, products[pid]["sort_rank"] or 0, products[pid]["barcode"])
    )

    single_batch_id = request.GET.get("batch") or None
    overrides = {}
    if single_batch_id:
        for o in StoreProductOverride.objects.filter(purchase_order_batch_id=single_batch_id):
            overrides[(o.product_id, o.store_id)] = o.override_qty

    # Build shipping table with adjusted quantities - now shows ALL products and ALL stores
    table_rows = []
    store_totals = defaultdict(int)
    store_claim_totals = defaultdict(int)

    for pid in sorted_product_ids:
        p = products[pid]
        cells = []
        row_total = 0
        row_claim_total = 0

        for sid in sorted_store_ids:
            qty = matrix[pid].get(sid, 0)  # Will be 0 if not ordered
            claimed = claimed_by_product_store.get((pid, sid), 0)
            net_qty = qty + claimed
            minimum = p["min_order_qty"]

            # Calculate display_qty for ORDER column (not including claims in display)
            overridden = (pid, sid) in overrides
            if overridden:
                display_qty = overrides[(pid, sid)]
            elif qty > 0 and minimum > 0 and qty < minimum:
                # Apply minimum only to actual order qty if store ordered
                display_qty = minimum
            else:
                # If qty=0 (not ordered), show 0 even if there are claims
                display_qty = qty

            # Calculate net for production total (order + claims, with minimum applied)
            if overridden:
                net_for_total = overrides[(pid, sid)] + claimed
            elif qty > 0 and net_qty > 0 and minimum > 0 and net_qty < minimum:
                net_for_total = minimum
            else:
                net_for_total = net_qty

            cells.append({
                'qty': display_qty,  # Order qty only, with minimum if ordered
                'claimed': claimed,
            })
            row_total += net_for_total
            row_claim_total += claimed
            store_totals[sid] += net_for_total
            store_claim_totals[sid] += claimed

        # Add row even if row_total is 0 to show all products
        table_rows.append({
            "product": p,
            "cells": cells,
            "row_total": row_total,
            "row_claim_total": row_claim_total,
        })

    # Calculate grand total
    grand_total = sum(store_totals.values())
    grand_claim_total = sum(store_claim_totals.values())

    # Prepare store columns with totals for easier template iteration
    store_columns = [
        {
            "name": stores[sid],
            "total": store_totals[sid],
            "claim_total": store_claim_totals[sid],
        }
        for sid in sorted_store_ids
    ]

    context = {
        "store_names": [stores[sid] for sid in sorted_store_ids],
        "store_columns": store_columns,
        "table_rows": table_rows,
        "grand_total": grand_total,
        "grand_claim_total": grand_claim_total,
        "batches": PurchaseOrderBatch.objects.order_by("-uploaded_at")[:30],
        "customers": Customer.objects.filter(is_active=True),
        "stores": Store.objects.filter(is_active=True),
        "single_batch_id": single_batch_id,
    }
    return render(request, "dashboard/shipping_summary.html", context)


@login_required
def delivery_note_list(request):
    """List all delivery notes"""
    delivery_notes = DeliveryNote.objects.select_related("store", "store__customer", "batch", "created_by").all()

    # Get latest batch as default
    latest_batch = PurchaseOrderBatch.objects.order_by('-uploaded_at').first()

    # Apply filters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    batch_id = request.GET.get('batch', '')
    customer_id = request.GET.get('customer', '')
    store_id = request.GET.get('store', '')

    # Default to latest batch if no filters applied
    if not any([search, status, batch_id, customer_id, store_id]) and latest_batch:
        batch_id = str(latest_batch.pk)

    if search:
        delivery_notes = delivery_notes.filter(
            Q(dn_number__icontains=search) |
            Q(store__name__icontains=search)
        )

    if status:
        delivery_notes = delivery_notes.filter(status=status)

    if batch_id:
        delivery_notes = delivery_notes.filter(batch_id=batch_id)

    if customer_id:
        delivery_notes = delivery_notes.filter(store__customer_id=customer_id)

    if store_id:
        delivery_notes = delivery_notes.filter(store_id=store_id)

    delivery_notes = delivery_notes.order_by('-created_at')

    # Get filter options
    batches = PurchaseOrderBatch.objects.order_by('-uploaded_at')[:30]
    customers = Customer.objects.filter(is_active=True).order_by('name')
    stores = Store.objects.filter(is_active=True).order_by('name')

    context = {
        "delivery_notes": delivery_notes,
        "search": search,
        "status_filter": status,
        "batch_filter": batch_id,
        "customer_filter": customer_id,
        "store_filter": store_id,
        "batches": batches,
        "customers": customers,
        "stores": stores,
    }
    return render(request, "dashboard/delivery_note_list.html", context)


@login_required
def create_delivery_notes_from_batch(request, batch_id):
    """Create delivery notes for all stores in a batch"""
    from collections import defaultdict
    from decimal import Decimal
    from django.db.models import Sum

    batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)

    # Detect customer from batch
    selected_customer = batch.customer if hasattr(batch, 'customer') and batch.customer else None

    # Load customer-specific barcode overrides
    customer_barcodes = {}
    if selected_customer:
        from apps.core.models import CustomerProduct
        cp_list = CustomerProduct.objects.filter(
            customer=selected_customer
        ).select_related('product')
        for cp in cp_list:
            if cp.barcode_override:
                customer_barcodes[cp.product_id] = cp.barcode_override

    # Get all store quantities from the batch
    qs = POLineItem.objects.filter(purchase_order__batch=batch)

    rows = qs.values(
        "product__id", "product__barcode", "product__description",
        "product__sort_rank", "product__min_order_qty",
        "purchase_order__store__id",
    ).annotate(total_qty2=Sum("qty2"), total_line_amount=Sum("line_total"))

    stores = {}
    products = {}
    matrix = defaultdict(dict)
    price_matrix = defaultdict(dict)

    for row in rows:
        store_id = row["purchase_order__store__id"]
        product_id = row["product__id"]

        # Skip unmapped products (product_id is NULL)
        if product_id is None:
            continue

        if store_id and store_id not in stores:
            stores[store_id] = Store.objects.get(pk=store_id)

        if product_id not in products:
            effective_barcode = customer_barcodes.get(product_id) or row["product__barcode"]
            products[product_id] = {
                "id": product_id,
                "sort_rank": row["product__sort_rank"],
                "barcode": effective_barcode,
                "min_order_qty": row["product__min_order_qty"] or 0,
            }

        qty = row["total_qty2"]
        amount = row["total_line_amount"] or 0
        matrix[product_id][store_id] = qty

        # Calculate unit price
        if qty > 0:
            price_matrix[product_id][store_id] = Decimal(str(amount)) / Decimal(str(qty))
        else:
            price_matrix[product_id][store_id] = Decimal('0')

    # Get claims
    _, claimed_by_product_store = _claimed_totals(request)

    # Get overrides
    overrides = {}
    for o in StoreProductOverride.objects.filter(purchase_order_batch_id=batch_id):
        overrides[(o.product_id, o.store_id)] = o.override_qty

    sorted_product_ids = sorted(
        products, key=lambda pid: (products[pid]["sort_rank"] is None, products[pid]["sort_rank"] or 0, products[pid]["barcode"])
    )

    # If GET request, show form to select delivery dates
    if request.method != "POST":
        from datetime import date
        today = date.today()

        context = {
            "batch": batch,
            "stores": sorted(stores.values(), key=lambda s: s.name),
            "today": today,
        }
        return render(request, "dashboard/create_delivery_notes_form.html", context)

    # POST request - Create delivery notes for each store
    created_dns = []
    for store_id, store in stores.items():
        # Get delivery date for this store
        delivery_date_key = f"delivery_date_{store_id}"
        delivery_date_str = request.POST.get(delivery_date_key)

        delivery_date = None
        if delivery_date_str:
            from datetime import datetime
            try:
                delivery_date = datetime.strptime(delivery_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Calculate quantities for this store (excluding claims from delivery note)
        store_items = []
        subtotal = Decimal('0')

        for pid in sorted_product_ids:
            p = products[pid]
            qty = matrix[pid].get(store_id, 0)
            minimum = p["min_order_qty"]
            unit_price = price_matrix[pid].get(store_id, Decimal('0'))

            # Delivery note should NOT include claims - only actual orders
            # If store didn't order this product (qty = 0), don't include it at all
            if qty == 0:
                # Check if there's an override that forces quantity > 0
                if (pid, store_id) in overrides and overrides[(pid, store_id)] > 0:
                    display_qty = overrides[(pid, store_id)]
                else:
                    continue  # Skip this product - store didn't order it

            # Store ordered this product (qty > 0)
            overridden = (pid, store_id) in overrides
            if overridden:
                display_qty = overrides[(pid, store_id)]
            elif minimum > 0 and qty < minimum:
                # Apply minimum only if store actually ordered
                display_qty = minimum
            else:
                display_qty = qty

            if display_qty > 0:
                amount = Decimal(str(display_qty)) * unit_price
                subtotal += amount

                store_items.append({
                    "product_id": pid,
                    "quantity": display_qty,
                    "unit_price": unit_price,
                    "amount": amount,
                })

        # Create delivery note if store has items
        if store_items:
            # Calculate VAT and grand total
            vat_rate = Decimal('7.00')
            vat_amount = subtotal * (vat_rate / Decimal('100'))
            grand_total = subtotal + vat_amount

            # Get customer info for snapshot
            customer = store.customer
            customer_head_office_address = customer.head_office_address or ""
            customer_tax_id = customer.tax_id or ""

            # Get all PO order numbers for this batch
            po_numbers = list(
                batch.purchase_orders.filter(store=store)
                .exclude(order_no="")
                .values_list("order_no", flat=True)
                .distinct()
            )
            po_numbers_str = ", ".join(po_numbers) if po_numbers else ""

            dn = DeliveryNote.objects.create(
                store=store,
                batch=batch,
                delivery_address=store.address or store.name,
                customer_head_office_address=customer_head_office_address,
                customer_tax_id=customer_tax_id,
                po_numbers=po_numbers_str,
                delivery_date=delivery_date,
                subtotal=subtotal,
                vat_rate=vat_rate,
                vat_amount=vat_amount,
                grand_total=grand_total,
                created_by=request.user,
            )

            # Create line items (no claimed_quantity field needed)
            for idx, item in enumerate(store_items, start=1):
                DeliveryNoteItem.objects.create(
                    delivery_note=dn,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    claimed_quantity=0,  # Delivery notes don't include claims
                    unit_price=item["unit_price"],
                    amount=item["amount"],
                    line_no=idx,
                )

            created_dns.append(dn)

    return redirect("dashboard:delivery_note_list")


@login_required
def delivery_note_detail(request, dn_id):
    """View single delivery note"""
    from apps.core.models import CompanyProfile

    dn = get_object_or_404(
        DeliveryNote.objects.select_related("store", "store__customer", "batch", "created_by")
        .prefetch_related("items__product")
        , pk=dn_id
    )

    # Get company profile
    company = CompanyProfile.get_active()

    # Calculate total quantity
    total_quantity = sum(item.quantity for item in dn.items.all())

    # Paginate items - 5 per page
    items = list(dn.items.all())
    items_per_page = 5
    pages = []
    for i in range(0, len(items), items_per_page):
        pages.append(items[i:i + items_per_page])

    context = {
        "dn": dn,
        "company": company,
        "total_quantity": total_quantity,
        "pages": pages,
    }
    return render(request, "dashboard/delivery_note_detail.html", context)


@login_required
def confirm_delivery_note(request, dn_id):
    """Confirm a delivery note"""
    if request.method != "POST":
        return redirect("dashboard:delivery_note_detail", dn_id=dn_id)

    dn = get_object_or_404(DeliveryNote, pk=dn_id)

    if dn.status == DeliveryNote.Status.DRAFT:
        from django.utils import timezone
        dn.status = DeliveryNote.Status.CONFIRMED
        dn.confirmed_at = timezone.now()
        dn.save(update_fields=["status", "confirmed_at"])

    return redirect("dashboard:delivery_note_detail", dn_id=dn.id)


@login_required
def mark_delivered(request, dn_id):
    """Mark delivery note as delivered"""
    if request.method != "POST":
        return redirect("dashboard:delivery_note_detail", dn_id=dn_id)

    dn = get_object_or_404(DeliveryNote, pk=dn_id)

    if dn.status == DeliveryNote.Status.CONFIRMED:
        from django.utils import timezone
        dn.status = DeliveryNote.Status.DELIVERED
        dn.delivered_at = timezone.now()
        dn.save(update_fields=["status", "delivered_at"])

    return redirect("dashboard:delivery_note_detail", dn_id=dn.id)


@login_required
def delete_delivery_note(request, dn_id):
    """Delete a delivery note"""
    if request.method != "POST":
        return redirect("dashboard:delivery_note_list")

    dn = get_object_or_404(DeliveryNote, pk=dn_id)
    dn.delete()

    return redirect("dashboard:delivery_note_list")


@login_required
def invoice_list(request):
    """List all invoices"""
    from .models import Invoice

    invoices = Invoice.objects.select_related("customer", "created_by").order_by("-created_at")

    # Apply filters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    customer_id = request.GET.get('customer', '')
    month = request.GET.get('month', '')
    year = request.GET.get('year', '')

    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(customer__name__icontains=search)
        )

    if status:
        invoices = invoices.filter(status=status)

    if customer_id:
        invoices = invoices.filter(customer_id=customer_id)

    if month:
        invoices = invoices.filter(invoice_month=int(month))

    if year:
        invoices = invoices.filter(invoice_year=int(year))

    # Get all customers for filter dropdown
    customers = Customer.objects.filter(is_active=True).order_by('name')

    context = {
        "invoices": invoices,
        "customers": customers,
        "search": search,
        "status_filter": status,
        "customer_filter": customer_id,
        "month_filter": month,
        "year_filter": year,
    }
    return render(request, "dashboard/invoice_list.html", context)


@login_required
def create_invoice(request):
    """Create invoice from delivery notes for a customer and month"""
    from .models import Invoice, InvoiceLineItem
    from apps.core.models import Customer
    from django.db.models import Q
    from datetime import datetime, timedelta
    from decimal import Decimal

    if request.method != "POST":
        # Show form to select customer and month
        customers = Customer.objects.filter(is_active=True).order_by("name")

        # Get available months from all delivery notes (not just confirmed)
        dns = DeliveryNote.objects.all().order_by("-created_at")
        months = set()
        for dn in dns:
            months.add((dn.created_at.year, dn.created_at.month))

        months_list = sorted(months, reverse=True)

        context = {
            "customers": customers,
            "months": months_list,
        }
        return render(request, "dashboard/create_invoice.html", context)

    # Process form submission
    customer_id = request.POST.get("customer_id")
    year_month = request.POST.get("year_month", "")

    if not year_month or "-" not in year_month:
        return redirect("dashboard:create_invoice")

    year, month = year_month.split("-")
    year = int(year)
    month = int(month)

    customer = get_object_or_404(Customer, pk=customer_id)

    # Check if invoice already exists
    existing = Invoice.objects.filter(
        customer=customer,
        invoice_year=year,
        invoice_month=month
    ).first()

    if existing:
        return redirect("dashboard:invoice_detail", invoice_id=existing.id)

    # Get all delivery notes for this customer and month (any status)
    from datetime import date
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    delivery_notes = DeliveryNote.objects.filter(
        store__customer=customer,
        created_at__gte=start_date,
        created_at__lt=end_date
    ).prefetch_related("items__product").order_by("created_at")

    if not delivery_notes.exists():
        # No delivery notes found - redirect back with message
        from django.contrib import messages
        messages.warning(request, f"ไม่พบ Delivery Notes สำหรับ {customer.name} ในเดือน {month}/{year}")
        return redirect("dashboard:create_invoice")

    # Create invoice
    invoice = Invoice.objects.create(
        customer=customer,
        invoice_month=month,
        invoice_year=year,
        billing_address=customer.head_office_address or "",
        customer_tax_id=customer.tax_id or "",
        subtotal=Decimal('0'),
        vat_amount=Decimal('0'),
        grand_total=Decimal('0'),
        created_by=request.user,
    )

    # Create line items from delivery notes
    subtotal = Decimal('0')
    line_no = 1

    for dn in delivery_notes:
        # Get product groups from DN items
        items = dn.items.all()
        product_groups = set()
        total_qty = 0

        for item in items:
            if item.product.product_group:
                product_groups.add(item.product.product_group)
            total_qty += item.quantity

        # Create description from product groups
        description = " & ".join(sorted(product_groups)) if product_groups else "สินค้าทั่วไป"

        # Create invoice line item
        InvoiceLineItem.objects.create(
            invoice=invoice,
            delivery_note=dn,
            description=description,
            quantity=total_qty,
            unit="PCS",
            amount=dn.grand_total,
            line_no=line_no,
        )

        subtotal += dn.subtotal
        line_no += 1

    # Calculate totals
    vat_rate = Decimal('7.00')
    vat_amount = subtotal * (vat_rate / Decimal('100'))
    grand_total = subtotal + vat_amount

    invoice.subtotal = subtotal
    invoice.vat_amount = vat_amount
    invoice.grand_total = grand_total
    invoice.save()

    return redirect("dashboard:invoice_detail", invoice_id=invoice.id)


@login_required
def invoice_detail(request, invoice_id):
    """View single invoice"""
    from .models import Invoice
    from apps.core.models import CompanyProfile

    invoice = get_object_or_404(
        Invoice.objects.select_related("customer", "created_by")
        .prefetch_related("line_items__delivery_note")
        , pk=invoice_id
    )

    # Get company profile
    company = CompanyProfile.get_active()

    # Calculate total quantity
    total_quantity = sum(item.quantity for item in invoice.line_items.all())

    context = {
        "invoice": invoice,
        "company": company,
        "total_quantity": total_quantity,
    }
    return render(request, "dashboard/invoice_detail.html", context)


@login_required
def edit_invoice(request, invoice_id):
    """Edit invoice number and line item descriptions"""
    from .models import Invoice

    invoice = get_object_or_404(
        Invoice.objects.select_related("customer")
        .prefetch_related("line_items__delivery_note")
        , pk=invoice_id
    )

    if request.method == "POST":
        # Update invoice number
        new_invoice_number = request.POST.get("invoice_number", "").strip()
        if new_invoice_number and new_invoice_number != invoice.invoice_number:
            # Check if new number already exists
            if Invoice.objects.filter(invoice_number=new_invoice_number).exclude(pk=invoice.pk).exists():
                from django.contrib import messages
                messages.error(request, f"เลขที่ Invoice {new_invoice_number} มีอยู่แล้ว")
            else:
                invoice.invoice_number = new_invoice_number
                invoice.save(update_fields=["invoice_number"])

        # Update line item external invoice numbers
        for line_item in invoice.line_items.all():
            invoice_no_key = f"invoice_no_{line_item.id}"
            new_invoice_no = request.POST.get(invoice_no_key, "").strip()
            if new_invoice_no != line_item.external_invoice_number:
                line_item.external_invoice_number = new_invoice_no
                line_item.save(update_fields=["external_invoice_number"])

        # Update default description for all line items
        default_description = request.POST.get("default_description", "").strip()
        if default_description:
            for line_item in invoice.line_items.all():
                line_item.description = default_description
                line_item.save(update_fields=["description"])

        return redirect("dashboard:invoice_detail", invoice_id=invoice.id)

    context = {
        "invoice": invoice,
    }
    return render(request, "dashboard/edit_invoice.html", context)


@login_required
def delete_invoice(request, invoice_id):
    """Delete an invoice"""
    from .models import Invoice

    if request.method != "POST":
        return redirect("dashboard:invoice_list")

    invoice = get_object_or_404(Invoice, pk=invoice_id)
    invoice.delete()

    return redirect("dashboard:invoice_list")
