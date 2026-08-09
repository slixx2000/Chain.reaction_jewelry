from django import forms
from .models import Item

INPUT = (
    'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 '
    'focus:outline-none focus:ring-2 focus:ring-chain-gold'
)


class ItemForm(forms.ModelForm):
    """Used for both create and edit."""

    class Meta:
        model = Item
        fields = ('category', 'name', 'description', 'price', 'image', 'is_sold')
        widgets = {
            'category': forms.Select(attrs={'class': INPUT}),
            'name': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Item name'}),
            'description': forms.Textarea(attrs={
                'class': INPUT + ' resize-none',
                'placeholder': 'Item description',
                'rows': '4',
            }),
            'price': forms.NumberInput(attrs={
                'class': INPUT,
                'placeholder': 'Price',
                'step': '0.01',
                'min': '0',
            }),
            'image': forms.FileInput(attrs={'class': INPUT, 'accept': 'image/*'}),
            'is_sold': forms.CheckboxInput(attrs={'class': 'w-5 h-5 accent-chain-gold'}),
        }
        labels = {'is_sold': 'Mark as sold'}

    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError('Price must be greater than zero.')
        return price
