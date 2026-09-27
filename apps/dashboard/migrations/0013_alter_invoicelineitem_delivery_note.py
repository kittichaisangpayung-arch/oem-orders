# Generated migration to allow null delivery_note in InvoiceLineItem

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0012_alter_invoice_constraint'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoicelineitem',
            name='delivery_note',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='invoice_items', to='dashboard.deliverynote'),
        ),
    ]
