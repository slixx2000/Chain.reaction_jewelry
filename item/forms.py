from django import forms
from .models import Item

class newItemForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black focus:outline-none focus:ring-2 focus:ring-chain-gold',
            }
        ),
    )
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Item name',
            }
        ),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold resize-none',
                'placeholder': 'Item description',
                'rows': '4',
            }
        ),
    )
    price = forms.FloatField(
        widget=forms.NumberInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Price',
                'step': '0.01',
            }
        ),
    )
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'accept': 'image/*',
            }
        ),
    )

    class Meta:
        model = Item
        fields = ('category', 'name', 'description', 'price', 'image', 'is_sold')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Category
        self.fields['category'].queryset = Category.objects.all()

class EditItemForm(forms.ModelForm):
    name = forms.CharField(
        max_length=255,
         widget=forms.TextInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Item name',
            }
        ),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold resize-none',
                'placeholder': 'Item description',
                'rows': '4',
            }
        ),
    )
    price = forms.FloatField(
        widget=forms.NumberInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Price',
                'step': '0.01',
            }
        ),
    )
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'accept': 'image/*',
            }
        ),
    )

    class Meta:
        model = Item
        fields = ('name', 'description', 'price', 'image', 'is_sold')