from datetime import datetime

from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.core.models import Customer, Product, Store
from apps.dashboard.models import DeliveryNote, DeliveryNoteItem
from apps.dashboard.product_trends import (
    MAX_COMPARE_PRODUCTS,
    _year_groups,
    product_comparison,
    product_trend_list,
)
from apps.ingestion.models import POLineItem, PurchaseOrder, PurchaseOrderBatch


def _dn(store, product, qty, price, created_at):
    dn = DeliveryNote.objects.create(store=store, delivery_address=store.name)
    DeliveryNote.objects.filter(pk=dn.pk).update(created_at=created_at)
    DeliveryNoteItem.objects.create(
        delivery_note=dn, product=product, quantity=qty,
        unit_price=price, amount=qty * price, line_no=1,
    )


class YearGroupsTests(TestCase):
    def test_groups_by_year_newest_first_with_all_months(self):
        groups = _year_groups({'2025-11', '2026-02'}, ['2026-02'])

        self.assertEqual([g['year'] for g in groups], [2026, 2025])
        self.assertEqual(groups[0]['label'], 2569)
        self.assertEqual(len(groups[0]['months']), 12)

        feb = groups[0]['months'][1]
        self.assertEqual(feb['value'], '2026-02')
        self.assertTrue(feb['selected'])
        self.assertTrue(feb['enabled'])
        self.assertFalse(groups[0]['months'][0]['enabled'])
        self.assertTrue(groups[1]['months'][10]['enabled'])

    def test_selected_month_without_data_stays_enabled(self):
        groups = _year_groups(set(), ['2024-05'])

        self.assertEqual([g['year'] for g in groups], [2024])
        self.assertTrue(groups[0]['months'][4]['enabled'])


class ProductTrendListTests(TestCase):
    def test_renders_year_tabs_without_submit_button(self):
        request = RequestFactory().get('/', {'month': ['2025-12', '2026-01']})
        html = product_trend_list(request).content.decode()

        self.assertIn('data-year="2026"', html)
        self.assertIn('data-year="2025"', html)
        self.assertIn('<noscript><button type="submit"', html)

    def test_totals_come_from_delivery_notes_not_po_lines(self):
        customer = Customer.objects.create(name='Donki', code='DONKI', parser_key='donki_v1')
        store = Store.objects.create(customer=customer, store_code='S1', name='Store 1')
        product = Product.objects.create(barcode='111', description='Product A')
        tz = timezone.get_current_timezone()

        # PO ordered 10, but the DN bumped it to the minimum of 30.
        batch = PurchaseOrderBatch.objects.create(customer=customer)
        PurchaseOrderBatch.objects.filter(pk=batch.pk).update(
            uploaded_at=datetime(2026, 1, 31, tzinfo=tz)
        )
        po = PurchaseOrder.objects.create(
            batch=batch, customer=customer, store=store,
            store_code_raw=store.store_code, store_name_raw=store.name, source_filename='t.pdf',
        )
        POLineItem.objects.create(
            purchase_order=po, product=product, barcode_raw=product.barcode,
            qty=10, qty2=10, unit_amount=5, line_total=50, line_no=1,
        )
        dn = DeliveryNote.objects.create(
            store=store, batch=batch, delivery_address=store.name,
        )
        # Uploaded in January, DN created in February.
        DeliveryNote.objects.filter(pk=dn.pk).update(created_at=datetime(2026, 2, 2, tzinfo=tz))
        DeliveryNoteItem.objects.create(
            delivery_note=dn, product=product, quantity=30,
            unit_price=5, amount=150, line_no=1,
        )

        response = product_trend_list(RequestFactory().get('/', {'month': ['2026-01', '2026-02']}))
        html = response.content.decode()

        # DN quantity (30), not the raw PO quantity (10); counted in February.
        self.assertIn('>30<', html)
        self.assertNotIn('>10<', html)
        self.assertIn('฿150', html)
        self.assertIn('กุมภาพันธ์ 2569', html)
        self.assertIn('<strong>30</strong>', html)

    def test_customer_filter_keeps_only_that_customers_notes(self):
        donki = Customer.objects.create(name='Donki', code='DONKI', parser_key='donki_v1')
        lopia = Customer.objects.create(name='Lopia', code='LOPIA', parser_key='lopia_v1')
        donki_store = Store.objects.create(customer=donki, store_code='D1', name='Donki 1')
        lopia_store = Store.objects.create(customer=lopia, store_code='L1', name='Lopia 1')
        product = Product.objects.create(barcode='111', description='Product A')
        when = datetime(2026, 2, 10, tzinfo=timezone.get_current_timezone())
        _dn(donki_store, product, 10, 5, when)
        _dn(lopia_store, product, 40, 5, when)

        html = product_trend_list(RequestFactory().get('/', {
            'month': '2026-02', 'customer': str(donki.pk),
        })).content.decode()

        self.assertIn('>10<', html)
        self.assertNotIn('>40<', html)
        self.assertNotIn('>50<', html)
        self.assertIn(f'value="{donki.pk}" selected', html)


class ProductComparisonTests(TestCase):
    def setUp(self):
        customer = Customer.objects.create(name='Donki', code='DONKI', parser_key='donki_v1')
        store = Store.objects.create(customer=customer, store_code='S1', name='Store 1')
        self.a = Product.objects.create(barcode='111', description='Product A')
        self.b = Product.objects.create(barcode='222', description='Product B')
        tz = timezone.get_current_timezone()
        _dn(store, self.a, 10, 5, datetime(2026, 1, 15, tzinfo=tz))
        _dn(store, self.a, 4, 5, datetime(2026, 2, 10, tzinfo=tz))
        _dn(store, self.b, 7, 20, datetime(2026, 2, 20, tzinfo=tz))

    def _get(self, params):
        response = product_comparison(RequestFactory().get('/', params))
        return response, response.content.decode()

    def test_monthly_series_per_product_in_selected_order(self):
        response, html = self._get({
            'products': [str(self.b.id), str(self.a.id)],
            'month': ['2026-01', '2026-02'],
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('"values": [0.0, 7.0]', html)
        self.assertIn('"values": [10.0, 4.0]', html)
        self.assertLess(html.index('"label": "Product B"'), html.index('"label": "Product A"'))

    def test_value_metric_charts_baht(self):
        _, html = self._get({'products': [str(self.b.id)], 'month': ['2026-02'], 'metric': 'value'})

        self.assertIn('"values": [140.0]', html)

    def test_defaults_to_months_with_data_and_ignores_bad_ids(self):
        _, html = self._get({'products': ['abc', '99999', str(self.a.id)]})

        self.assertIn('"values": [10.0, 4.0]', html)
        self.assertNotIn('"label": "Product B"', html)

    def test_no_products_shows_picker_without_chart(self):
        response, html = self._get({})

        self.assertEqual(response.status_code, 200)
        self.assertIn('name="products"', html)
        self.assertNotIn('id="compareChart"', html)

    def test_product_count_is_capped(self):
        extra = [
            Product.objects.create(barcode=f'9{i}', description=f'P{i}').id
            for i in range(MAX_COMPARE_PRODUCTS + 2)
        ]
        _, html = self._get({'products': [str(i) for i in extra]})

        self.assertEqual(html.count('class="summary-card"'), MAX_COMPARE_PRODUCTS)
