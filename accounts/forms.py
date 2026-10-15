from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class RegisterForm(UserCreationForm):
    """
    Form for new user registration.
    Inherits from Django's UserCreationForm which handles:
    - Username validation and uniqueness
    - Password strength checking via configured AUTH_PASSWORD_VALIDATORS
    - Password confirmation match
    - Secure password hashing (never plaintext)
    """
    email = forms.EmailField(
        required=True,
        help_text="Required. Enter a valid email address.",
        widget=forms.EmailInput(attrs={'placeholder': 'name@example.com'})
    )

    class Meta:
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password'})

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email


class LoginForm(AuthenticationForm):
    """
    Form for user login.
    Inherits from Django's AuthenticationForm which handles:
    - Secure user authentication check via authenticate()
    - Active account status verification
    - Standardized error messages
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter your username', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password'})
    )
