"""
Ingestion pipeline: takes uploaded PDFs for a batch, runs them through the
customer's registered parser, and maps the result into PurchaseOrder /
POLineItem rows. Unmapped store codes / barcodes are recorded but never
block ingestion of the rest of the batch (mirrors the old script's tolerant
"log a warning and continue" behavior for STORE_CODE_MAP / barcode lookups).
"""
from dataclasses import dataclass

from apps.core.models import CustomerProduct, Product, Store
from apps.parsers.base import ParserError
from apps.parsers.registry import get_parser

from .models import POLineItem, PurchaseOrder, PurchaseOrderBatch


@dataclass
class IngestResult:
    purchase_order: PurchaseOrder
    unmapped_store: bool
    unmapped_barcodes: list[str]


def ingest_batch(batch: PurchaseOrderBatch, uploaded_files) -> list[IngestResult]:
    parser = get_parser(batch.customer.parser_key)
    results = []
    any_ok = False

    for uploaded_file in uploaded_files:
        po = PurchaseOrder.objects.create(
            batch=batch,
            customer=batch.customer,
            source_filename=uploaded_file.name,
            source_file=uploaded_file,
        )
        result = _ingest_single_po(po, parser)
        results.append(result)
        if po.parse_status != PurchaseOrder.ParseStatus.FAILED:
            any_ok = True

    # Don't auto-update status here, let the confirm action do it
    # batch.status = PurchaseOrderBatch.Status.PROCESSED if any_ok else PurchaseOrderBatch.Status.FAILED
    # batch.save(update_fields=["status"])
    return results


def _ingest_single_po(po: PurchaseOrder, parser) -> IngestResult:
    try:
        parsed = parser.parse(po.source_file.path)
    except ParserError as exc:
        po.parse_status = PurchaseOrder.ParseStatus.FAILED
        po.error_message = str(exc)
        po.save(update_fields=["parse_status", "error_message"])
        return IngestResult(purchase_order=po, unmapped_store=False, unmapped_barcodes=[])

    po.order_no = parsed.order_no
    po.store_code_raw = parsed.store_code
    po.store_name_raw = parsed.store_name
    po.expected_row_count = parsed.expected_row_count
    po.parsed_row_count = len(parsed.line_items)
    po.parser_used = parsed.parser_used
    po.raw_text = parsed.raw_text

    store = Store.objects.filter(customer=po.customer, store_code=parsed.store_code).first()
    po.store = store
    unmapped_store = store is None

    if not parsed.line_items:
        po.parse_status = PurchaseOrder.ParseStatus.FAILED
    elif po.parsed_row_count < po.expected_row_count:
        po.parse_status = PurchaseOrder.ParseStatus.PARTIAL
    else:
        po.parse_status = PurchaseOrder.ParseStatus.OK

    po.save()

    unmapped_barcodes = []
    line_items_to_create = []
    for item in parsed.line_items:
        # Try to find product by customer-specific barcode first
        customer_product = CustomerProduct.objects.filter(
            customer=po.customer,
            barcode_override=item.barcode
        ).select_related('product').first()

        if customer_product:
            product = customer_product.product
        else:
            # Fall back to default product barcode
            product = Product.objects.filter(barcode=item.barcode).first()

        if product is None:
            unmapped_barcodes.append(item.barcode)
        line_items_to_create.append(POLineItem(
            purchase_order=po,
            product=product,
            barcode_raw=item.barcode,
            description_raw=item.description,
            uom_raw=item.uom,
            qty=item.qty,
            qty2=item.qty2,
            unit_amount=item.unit_amount,
            line_total=item.line_total,
            line_no=item.line_no,
        ))
    POLineItem.objects.bulk_create(line_items_to_create)

    return IngestResult(
        purchase_order=po,
        unmapped_store=unmapped_store,
        unmapped_barcodes=sorted(set(unmapped_barcodes)),
    )
