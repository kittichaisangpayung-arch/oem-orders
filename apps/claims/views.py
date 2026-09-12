from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.access import in_sales_group
from apps.ingestion.models import POLineItem, PurchaseOrder, PurchaseOrderBatch

from .forms import BatchSelectForm, ClaimForm
from .models import Claim


@login_required
def claim_list_create(request):
    if not in_sales_group(request.user):
        return render(request, "claims/forbidden.html", status=403)

    selected_batch = None
    batch_pos = []
    selected_po = None
    po_line_items = []

    batch_id = request.GET.get("batch")
    po_id = request.GET.get("store") or request.POST.get("purchase_order")

    if batch_id:
        selected_batch = get_object_or_404(PurchaseOrderBatch, pk=batch_id)
        batch_pos = list(selected_batch.purchase_orders.select_related("store").all())

    if po_id:
        selected_po = get_object_or_404(PurchaseOrder, pk=po_id, batch=selected_batch)
        po_line_items = list(selected_po.line_items.select_related("product").all())

    if request.method == "POST":
        form = ClaimForm(request.POST, po_line_items=po_line_items)
        if selected_po and form.is_valid():
            line_item = get_object_or_404(
                POLineItem, pk=form.cleaned_data["line_item"], purchase_order=selected_po
            )
            claim = Claim(
                purchase_order=selected_po,
                store=selected_po.store,
                product=line_item.product,
                qty=form.cleaned_data["qty"],
                note=form.cleaned_data["note"],
                created_by=request.user,
            )
            claim.save()
            return redirect(f"{request.path}?batch={selected_batch.pk}&store={selected_po.pk}")
    else:
        form = ClaimForm(po_line_items=po_line_items) if selected_po else None

    batch_select_form = BatchSelectForm(initial={"batch": selected_batch})
    recent_batches = PurchaseOrderBatch.objects.order_by("-uploaded_at")[:30]
    claims = Claim.objects.select_related("store", "product", "purchase_order", "purchase_order__batch").all()[:50]

    return render(
        request,
        "claims/list_create.html",
        {
            "batch_select_form": batch_select_form,
            "recent_batches": recent_batches,
            "selected_batch": selected_batch,
            "batch_pos": batch_pos,
            "selected_po": selected_po,
            "form": form,
            "claims": claims,
        },
    )
