from django.urls import path

from . import views
from . import product_trends
from . import product_inactivity
from . import claim_analytics
from . import compensation_analytics

app_name = "dashboard"

urlpatterns = [
    path("", views.executive_dashboard, name="executive_dashboard"),
    path("production/", views.production_summary, name="production"),
    path("stores/", views.store_matrix, name="store_matrix"),
    path("stores/override/", views.set_override, name="set_override"),
    path("stores/add-claim/", views.add_claim_inline, name="add_claim_inline"),
    path("stores/add-compensation/", views.add_compensation_inline, name="add_compensation_inline"),
    path("factory/", views.factory_summary, name="factory_summary"),
    path("shipping/", views.shipping_summary, name="shipping_summary"),
    path("delivery-notes/", views.delivery_note_list, name="delivery_note_list"),
    path("delivery-notes/create/<int:batch_id>/", views.create_delivery_notes_from_batch, name="create_delivery_notes"),
    path("delivery-notes/<int:dn_id>/", views.delivery_note_detail, name="delivery_note_detail"),
    path("delivery-notes/<int:dn_id>/confirm/", views.confirm_delivery_note, name="confirm_delivery_note"),
    path("delivery-notes/<int:dn_id>/mark-delivered/", views.mark_delivered, name="mark_delivered"),
    path("delivery-notes/<int:dn_id>/delete/", views.delete_delivery_note, name="delete_delivery_note"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/create/", views.create_invoice, name="create_invoice"),
    path("invoices/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:invoice_id>/edit/", views.edit_invoice, name="edit_invoice"),
    path("invoices/<int:invoice_id>/delete/", views.delete_invoice, name="delete_invoice"),

    # Product Trends
    path("trends/", product_trends.product_trend_list, name="product_trend_list"),
    path("trends/<int:product_id>/", product_trends.product_trend_detail, name="product_trend_detail"),
    path("trends/compare/", product_trends.product_comparison, name="product_comparison"),

    # Product Inactivity Report
    path("inactivity/", product_inactivity.product_inactivity_report, name="product_inactivity_report"),

    # Claim Analytics
    path("claims/analytics/", claim_analytics.claim_summary_dashboard, name="claim_analytics"),

    # Compensation Analytics
    path("compensations/analytics/", compensation_analytics.compensation_summary_dashboard, name="compensation_analytics"),
]
