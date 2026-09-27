# Generated migration to add invoice status tracking fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0014_merge_20260927_1223'),
    ]

    operations = [
        # Update status choices
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'แบบร่าง'),
                    ('SENT', 'ส่งเอกสารแล้ว'),
                    ('WAITING_PAYMENT', 'รอเงิน'),
                    ('PAID', 'จ่ายแล้ว'),
                    ('CANCELLED', 'ยกเลิก')
                ],
                default='DRAFT',
                max_length=20
            ),
        ),
        # Add status tracking fields
        migrations.AddField(
            model_name='invoice',
            name='sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='cancellation_reason',
            field=models.TextField(blank=True),
        ),
    ]
