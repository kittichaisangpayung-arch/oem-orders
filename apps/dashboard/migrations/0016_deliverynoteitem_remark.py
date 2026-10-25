from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0015_add_invoice_status_tracking'),
    ]

    operations = [
        migrations.AddField(
            model_name='deliverynoteitem',
            name='remark',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
