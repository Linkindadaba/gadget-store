from django import forms
from .models import Order
from django.conf import settings


class CheckoutForm(forms.ModelForm):
    REGION_CHOICES = [('', 'Select Region')] + [(r, r) for r in sorted(settings.DELIVERY_REGIONS.keys())]
    region = forms.ChoiceField(choices=REGION_CHOICES)

    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'region', 'notes']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Any special instructions?'}),
        }
