# Generated manually for adding entry_mode field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorder',
            name='entry_mode',
            field=models.CharField(
                choices=[('PDF', 'PDF Upload'), ('MANUAL', 'Manual Entry')],
                default='PDF',
                max_length=10
            ),
        ),
    ]
