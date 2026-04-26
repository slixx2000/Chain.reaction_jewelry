from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Username',
            }
        ),
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Password',
            }
        ),
    )

class SignUpForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Username',
            }
        ),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Email address',
            }
        ),
    )
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Password',
            }
        ),
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                'class': 'w-full px-4 py-2 border rounded-lg bg-white text-black placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-chain-gold',
                'placeholder': 'Confirm password',
            }
        ),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')