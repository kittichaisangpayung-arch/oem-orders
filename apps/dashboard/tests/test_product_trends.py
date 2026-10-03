from django.test import RequestFactory, TestCase

from apps.dashboard.product_trends import _year_groups, product_trend_list


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
