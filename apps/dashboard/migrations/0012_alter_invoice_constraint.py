# Generated migration to update invoice unique constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0011_fix_invoice_numbers'),
    ]

    operations = [
        # Remove old constraint
        migrations.RemoveConstraint(
            model_name='invoice',
            name='unique_invoice_per_customer_month',
        ),
        # Add new constraint with invoice_type
        migrations.AddConstraint(
            model_name='invoice',
            constraint=models.UniqueConstraint(
                fields=['customer', 'invoice_year', 'invoice_month', 'invoice_type'],
                name='unique_invoice_per_customer_month_type'
            ),
        ),
    ]
