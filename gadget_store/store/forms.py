import re
from django import forms
from django.contrib.auth.models import User
from django.conf import settings
from .models import Profile

class SignupForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    phone = forms.CharField(max_length=20, label='Phone Number')
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already in use.')
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Normalize input by removing spaces and hyphens
        phone = re.sub(r'[\s\-]', '', phone)
        
        # Regex for Ghana phone numbers:
        # Supports local (02x, 05x, 03x), and international (+233 or 233) formats.
        gh_regex = r'^(?:\+233|233|0)[235]\d{8}$'
        
        if not re.match(gh_regex, phone):
            raise forms.ValidationError('Please enter a valid Ghana phone number (e.g., 0241234567).')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data

class ProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically populate region choices from settings
        regions = getattr(settings, 'DELIVERY_REGIONS', {})
        self.fields['region'].widget = forms.Select(
            choices=[('', 'Select region')] + [(r, r) for r in regions.keys()],
            attrs={'class': 'form-select', 'id': 'id_region'}
        )

    class Meta:
        model = Profile
        fields = ['profile_picture', 'phone', 'address', 'city', 'region']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/*', 'id': 'id_profile_picture'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter delivery address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter city'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = re.sub(r'[\s\-]', '', phone)
            gh_regex = r'^(?:\+233|233|0)[235]\d{8}$'
            if not re.match(gh_regex, phone):
                raise forms.ValidationError('Please enter a valid Ghana phone number.')
        return phone