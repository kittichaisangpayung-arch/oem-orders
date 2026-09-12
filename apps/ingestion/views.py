from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.access import in_sales_group, staff_required

from .forms import BatchUploadForm
from .models import PurchaseOrderBatch
from .services import ingest_batch


@login_required
def upload_batch(request):
    if not in_sales_group(request.user):
        return render(request, "ingestion/forbidden.html", status=403)

    if request.method == "POST":
        form = BatchUploadForm(request.POST, request.FILES)
        if form.is_valid():
            from django.utils import timezone
            from datetime import datetime, time
            import logging
            logger = logging.getLogger(__name__)

            # Get upload date from form or use current time
            upload_date = form.cleaned_data.get("upload_date")
            logger.warning(f"Upload date from form: {upload_date}")
            if upload_date:
                # Convert date to datetime at midnight (start of day)
                uploaded_at = timezone.make_aware(
                    datetime.combine(upload_date, time(0, 0, 0))
                )
                logger.warning(f"Using selected date: {uploaded_at}")
            else:
                uploaded_at = timezone.now()
                logger.warning(f"Using current time: {uploaded_at}")

            # Create batch with PENDING status
            batch = PurchaseOrderBatch.objects.create(
                customer=form.cleaned_data["customer"],
                uploaded_by=request.user,
                uploaded_at=uploaded_at,
                status=PurchaseOrderBatch.Status.PENDING,
            )

            # Store files temporarily in session for preview
            request.session[f'batch_{batch.pk}_files'] = [f.name for f in request.FILES.getlist("files")]

            # Process files immediately for preview
            results = ingest_batch(batch, request.FILES.getlist("files"))

            # Redirect to preview page
            return redirect("ingestion:batch_preview", batch_id=batch.pk)
    else:
        form = BatchUploadForm()

    recent_batches = PurchaseOrderBatch.objects.select_related("customer").order_by("-uploaded_at")[:30]
    return render(request, "ingestion/upload.html", {"form": form, "recent_batches": recent_batches})


@login_required
def batch_preview(request, batch_id):
    """Preview batch before confirming to save to DB"""
    batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)

    # Only allow preview for PENDING batches
    if batch.status != PurchaseOrderBatch.Status.PENDING:
        return redirect("ingestion:batch_result", batch_id=batch.pk)

    purchase_orders = batch.purchase_orders.prefetch_related("line_items", "store").all()

    # Collect unmapped barcodes
    unmapped_barcodes = set()
    for po in purchase_orders:
        for li in po.line_items.all():
            if li.product_id is None:
                unmapped_barcodes.add(li.barcode_raw)

    # Collect stores found in this batch
    stores_in_batch = set()
    unmapped_stores = []
    for po in purchase_orders:
        if po.store:
            stores_in_batch.add(po.store.id)
        else:
            unmapped_stores.append({
                'store_code': po.store_code_raw,
                'store_name': po.store_name_raw,
                'order_no': po.order_no,
            })

    # Get all active stores for this customer
    from apps.core.models import Store
    all_customer_stores = Store.objects.filter(
        customer=batch.customer,
        is_active=True
    ).order_by('name')

    # Find missing stores
    missing_stores = []
    for store in all_customer_stores:
        if store.id not in stores_in_batch:
            missing_stores.append(store)

    # Check for parsing errors
    failed_pos = [po for po in purchase_orders if po.parse_status == 'FAILED']
    partial_pos = [po for po in purchase_orders if po.parse_status == 'PARTIAL']

    context = {
        "batch": batch,
        "purchase_orders": purchase_orders,
        "unmapped_barcodes": sorted(unmapped_barcodes),
        "unmapped_stores": unmapped_stores,
        "missing_stores": missing_stores,
        "failed_pos": failed_pos,
        "partial_pos": partial_pos,
        "has_warnings": bool(unmapped_barcodes or unmapped_stores or missing_stores or failed_pos or partial_pos),
        "is_preview": True,
    }
    return render(request, "ingestion/batch_preview.html", context)


@login_required
def confirm_batch(request, batch_id):
    """Confirm and save batch data to DB"""
    if request.method != "POST":
        return redirect("ingestion:batch_preview", batch_id=batch_id)

    batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)

    # Only allow confirm for PENDING batches
    if batch.status == PurchaseOrderBatch.Status.PENDING:
        # Update status to PROCESSED
        batch.status = PurchaseOrderBatch.Status.PROCESSED
        batch.save(update_fields=["status"])

    return redirect("ingestion:batch_result", batch_id=batch.pk)


@login_required
def cancel_batch(request, batch_id):
    """Cancel and delete pending batch"""
    if request.method != "POST":
        return redirect("ingestion:batch_preview", batch_id=batch_id)

    batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)

    # Only allow cancel for PENDING batches
    if batch.status == PurchaseOrderBatch.Status.PENDING:
        batch.delete()

    return redirect("ingestion:upload")


@login_required
def batch_result(request, batch_id):
    batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)
    purchase_orders = batch.purchase_orders.prefetch_related("line_items", "store").all()

    # Collect unmapped barcodes
    unmapped_barcodes = set()
    for po in purchase_orders:
        for li in po.line_items.all():
            if li.product_id is None:
                unmapped_barcodes.add(li.barcode_raw)

    # Collect stores found in this batch
    stores_in_batch = set()
    unmapped_stores = []
    for po in purchase_orders:
        if po.store:
            stores_in_batch.add(po.store.id)
        else:
            unmapped_stores.append({
                'store_code': po.store_code_raw,
                'store_name': po.store_name_raw,
                'order_no': po.order_no,
            })

    # Get all active stores for this customer
    from apps.core.models import Store
    all_customer_stores = Store.objects.filter(
        customer=batch.customer,
        is_active=True
    ).order_by('name')

    # Find missing stores (stores that exist but not in this batch)
    missing_stores = []
    for store in all_customer_stores:
        if store.id not in stores_in_batch:
            missing_stores.append(store)

    # Check for parsing errors
    failed_pos = [po for po in purchase_orders if po.parse_status == 'FAILED']
    partial_pos = [po for po in purchase_orders if po.parse_status == 'PARTIAL']

    context = {
        "batch": batch,
        "purchase_orders": purchase_orders,
        "unmapped_barcodes": sorted(unmapped_barcodes),
        "unmapped_stores": unmapped_stores,
        "missing_stores": missing_stores,
        "failed_pos": failed_pos,
        "partial_pos": partial_pos,
        "has_warnings": bool(unmapped_barcodes or unmapped_stores or missing_stores or failed_pos or partial_pos),
    }
    return render(request, "ingestion/batch_result.html", context)


@login_required
def delete_batch(request, batch_id):
    if request.method != "POST" or not staff_required(request.user):
        return render(request, "ingestion/forbidden.html", status=403)

    batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)
    batch.delete()
    return redirect("ingestion:upload")
