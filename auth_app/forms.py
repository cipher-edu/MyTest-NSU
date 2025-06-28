# auth_app/forms.py
import logging
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

# Mavjud importlaringiz
from .models import *

logger = logging.getLogger(__name__)

# --- Foydalanuvchi autentifikatsiyasi uchun forma ---

class LoginForm(forms.Form):
    """Foydalanuvchidan login va parol olish uchun standart forma."""
    username = forms.CharField(
        label="Login (ID Raqam)",
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input', # HTMLga stil berish uchun
            'placeholder': 'Talaba ID raqamingizni kiriting'
        })
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Parolingiz'
        })
    )


# --- Test Tizimi Uchun Yangi Formalar ---
