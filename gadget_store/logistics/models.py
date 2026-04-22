from django.db import models
from django.conf import settings


class DeliveryZone(models.Model):
    region = models.CharField(max_length=100, unique=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_days = models.CharField(max_length=50, default='2-5 business days')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.region} - GHS {self.fee}"

    class Meta:
        ordering = ['region']
