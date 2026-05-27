from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_payment_gateway_transaction_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='gateway',
            field=models.CharField(choices=[('flutterwave', 'Flutterwave'), ('paystack', 'Paystack')], default='flutterwave', max_length=20),
        ),
    ]
