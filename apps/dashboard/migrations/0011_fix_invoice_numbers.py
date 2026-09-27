# Generated migration to fix existing invoice numbers

from django.db import migrations


def fix_invoice_numbers(apps, schema_editor):
    """Update existing invoice numbers to use correct prefix based on type"""
    Invoice = apps.get_model('dashboard', 'Invoice')

    # Get all invoices that start with INV- or BS-
    invoices = Invoice.objects.all().order_by('created_at')

    # Track counters for each type per month
    billing_counters = {}  # {year_month: counter}
    invoice_counters = {}  # {year_month: counter}

    for invoice in invoices:
        year_month = f"{invoice.invoice_year}{invoice.invoice_month:02d}"

        # Determine correct prefix based on invoice_type
        if invoice.invoice_type == 'BILLING_STATEMENT':
            prefix = f"BS-{year_month}-"
            if year_month not in billing_counters:
                billing_counters[year_month] = 1
            else:
                billing_counters[year_month] += 1
            new_number = f"{prefix}{billing_counters[year_month]:06d}"
        else:  # DETAILED_INVOICE
            prefix = f"INV-{year_month}-"
            if year_month not in invoice_counters:
                invoice_counters[year_month] = 1
            else:
                invoice_counters[year_month] += 1
            new_number = f"{prefix}{invoice_counters[year_month]:06d}"

        # Update invoice number if it's different
        if invoice.invoice_number != new_number:
            invoice.invoice_number = new_number
            invoice.save(update_fields=['invoice_number'])


def reverse_fix(apps, schema_editor):
    """Reverse migration - not needed as we can't safely reverse this"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0010_invoice_invoice_type'),
    ]

    operations = [
        migrations.RunPython(fix_invoice_numbers, reverse_fix),
    ]
