import re
from django import forms
from django.conf import settings

class MobileMoneyPaymentForm(forms.Form):
    network = forms.ChoiceField(
        choices=settings.FLUTTERWAVE_MOBILE_MONEY_NETWORKS,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Mobile Money Network'
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 0241234567'}),
        label='Phone Number'
    )

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Normalize input by removing spaces and hyphens
            phone = re.sub(r'[\s\-]', '', phone)
            
            # Regex for Ghana phone numbers:
            # Supports local (02x, 05x, 03x), and international (+233 or 233) formats.
            gh_regex = r'^(?:\+233|233|0)[235]\d{8}$'
            if not re.match(gh_regex, phone):
                raise forms.ValidationError('Please enter a valid Ghana phone number (e.g., 0241234567).')
        return phone