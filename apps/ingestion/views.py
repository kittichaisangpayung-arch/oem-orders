from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.core.access import in_sales_group, staff_required
from apps.core.models import Store, Product

from .forms import BatchUploadForm, ManualPOEntryForm
from .models import PurchaseOrderBatch, PurchaseOrder, POLineItem
from .services import ingest_batch


@login_required
def upload_batch(request):
    if not in_sales_group(request.user):
        return render(request, "ingestion/forbidden.html", status=403)

    if request.method == "POST":
        form = BatchUploadForm(request.POST, request.FILES)
        if form.is_valid():
            entry_mode = form.cleaned_data.get("entry_mode")

            # If manual mode, redirect to manual entry page
            if entry_mode == "MANUAL":
                from django.utils import timezone
                from datetime import datetime, time

                upload_date = form.cleaned_data.get("upload_date")
                if upload_date:
                    uploaded_at = timezone.make_aware(
                        datetime.combine(upload_date, time(0, 0, 0))
                    )
                else:
                    uploaded_at = timezone.now()

                # Create batch for manual entry
                batch = PurchaseOrderBatch.objects.create(
                    customer=form.cleaned_data["customer"],
                    uploaded_by=request.user,
                    uploaded_at=uploaded_at,
                    status=PurchaseOrderBatch.Status.PENDING,
                    notes="Manual Entry"
                )
                return redirect("ingestion:manual_entry", batch_id=batch.pk)

            # PDF mode - existing logic
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


@login_required
def manual_entry(request, batch_id):
    """Manual PO entry page"""
    batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)

    if batch.status != PurchaseOrderBatch.Status.PENDING:
        return redirect("ingestion:batch_result", batch_id=batch.pk)

    # Get all active stores and products for this customer
    stores = Store.objects.filter(
        customer=batch.customer,
        is_active=True
    ).order_by('name')

    products = Product.objects.filter(is_active=True).order_by(
        'sort_rank', 'barcode'
    )

    context = {
        "batch": batch,
        "stores": stores,
        "products": products,
    }
    return render(request, "ingestion/manual_entry.html", context)


@login_required
@require_http_methods(["POST"])
def save_manual_po(request, batch_id):
    """Save manually entered PO data"""
    import json
    from decimal import Decimal

    batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)

    if batch.status != PurchaseOrderBatch.Status.PENDING:
        return JsonResponse({"success": False, "error": "Batch already processed"})

    try:
        data = json.loads(request.body)
        store_id = data.get('store_id')
        order_no = data.get('order_no', '')
        line_items = data.get('line_items', [])

        if not store_id:
            return JsonResponse({"success": False, "error": "กรุณาเลือกสาขา"})

        if not line_items:
            return JsonResponse({"success": False, "error": "กรุณาเพิ่มสินค้าอย่างน้อย 1 รายการ"})

        store = Store.objects.get(pk=store_id, customer=batch.customer)

        # Create PO with manual entry mode
        po = PurchaseOrder.objects.create(
            batch=batch,
            customer=batch.customer,
            store=store,
            order_no=order_no,
            store_code_raw=store.store_code,
            store_name_raw=store.name,
            source_filename=f"Manual Entry - {store.name}",
            entry_mode=PurchaseOrder.EntryMode.MANUAL,
            parse_status=PurchaseOrder.ParseStatus.OK,
            expected_row_count=len(line_items),
            parsed_row_count=len(line_items),
            parser_used="manual",
        )

        # Create line items
        for idx, item in enumerate(line_items, start=1):
            product_id = item.get('product_id')
            qty = int(item.get('qty', 0))
            qty2 = int(item.get('qty2', 0))
            price = Decimal(str(item.get('price', 0)))

            product = Product.objects.get(pk=product_id)

            # Calculate line total: price * quantity (use qty if > 0, otherwise qty2)
            total_quantity = qty if qty > 0 else qty2
            line_total = price * Decimal(str(total_quantity))

            POLineItem.objects.create(
                purchase_order=po,
                product=product,
                barcode_raw=product.barcode,
                description_raw=product.description,
                uom_raw=product.uom,
                qty=qty,
                qty2=qty2,
                unit_amount=price,
                line_total=line_total,
                line_no=idx,
            )

        return JsonResponse({
            "success": True,
            "po_id": po.pk,
            "message": f"บันทึก PO สำหรับ {store.name} สำเร็จ"
        })

    except Store.DoesNotExist:
        return JsonResponse({"success": False, "error": "ไม่พบสาขาที่เลือก"})
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "error": "ไม่พบสินค้าที่เลือก"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_http_methods(["POST"])
def finish_manual_entry(request, batch_id):
    """Finish manual entry and redirect to preview"""
    batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)

    if batch.status == PurchaseOrderBatch.Status.PENDING:
        # Check if at least one PO was created
        if not batch.purchase_orders.exists():
            return JsonResponse({
                "success": False,
                "error": "กรุณาเพิ่ม PO อย่างน้อย 1 รายการ"
            })

        return JsonResponse({
            "success": True,
            "redirect_url": f"/ingestion/batch/{batch.pk}/preview/"
        })

    return JsonResponse({"success": False, "error": "Batch already processed"})
