# Generated migration to remove invoice unique constraint

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0013_alter_invoicelineitem_delivery_note'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='invoice',
            name='unique_invoice_per_customer_month_type',
        ),
    ]
