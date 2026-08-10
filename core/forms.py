from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

# Editorial input: a single hairline under the field, no box. Shared by every
# form on the site — auth, checkout and the item forms all import this.
INPUT = (
    'w-full bg-transparent border-0 border-b border-ivory/30 px-0 py-2 '
    'text-ivory placeholder-ivory/25 focus:border-antique focus:outline-none '
    'focus:ring-0 transition-colors'
)


class StyledFormMixin:
    """Stamp the shared input styling on every widget instead of per field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', INPUT)
            field.widget.attrs.setdefault('placeholder', field.label or name)


class LoginForm(StyledFormMixin, AuthenticationForm):
    pass


class SignUpForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email
