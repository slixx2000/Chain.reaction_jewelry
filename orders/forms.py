from django import forms

from core.forms import INPUT
from . import bila
from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('full_name', 'email', 'phone', 'delivery_address')
        widgets = {
            'full_name': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Your full name'}),
            'email': forms.EmailInput(attrs={'class': INPUT, 'placeholder': 'you@example.com (optional)'}),
            'phone': forms.TextInput(attrs={
                'class': INPUT, 'placeholder': '0977123456', 'inputmode': 'tel', 'autocomplete': 'tel',
            }),
            'delivery_address': forms.Textarea(attrs={
                'class': INPUT + ' resize-none', 'rows': '3',
                'placeholder': 'Where should we deliver? Include area and any landmarks.',
            }),
        }
        labels = {
            'phone': 'Mobile money number',
            'email': 'Email (optional)',
            'delivery_address': 'Delivery details',
        }
        help_texts = {
            'phone': 'MTN, Airtel or Zamtel. You will get a prompt on this phone to approve the payment.',
            'email': 'We send your receipt here. Leave it blank and you can still track the order on this device.',
        }

    def clean_phone(self):
        try:
            phone = bila.normalise_phone(self.cleaned_data['phone'])
            # Validate the operator here so checkout fails before we create an order.
            bila.detect_operator(phone)
        except ValueError as exc:
            raise forms.ValidationError(str(exc))
        return phone

    @property
    def operator(self):
        return bila.detect_operator(self.cleaned_data['phone'])
