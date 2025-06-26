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

class TestForm(forms.ModelForm):
    """O'qituvchi uchun yangi test yaratish yoki tahrirlash formasi."""
    class Meta:
        model = Test
        fields = ['title', 'description', 'time_limit_minutes', 'pass_percentage', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'time_limit_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'pass_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class QuestionForm(forms.ModelForm):
    """Savol yaratish formasi."""
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'image', 'points']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': "Savol matnini kiriting"}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

# Savolga javob variantlarini qo'shish uchun formset
AnswerFormSet = inlineformset_factory(
    Question,  # Asosiy model
    Answer,    # Inline model
    fields=('text', 'is_correct'),
    extra=4,   # Yangi savol uchun 4 ta bo'sh javob maydoni
    can_delete=True,
    widgets={
        'text': forms.TextInput(attrs={'class': 'form-control mb-2', 'placeholder': 'Javob varianti'}),
        'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    }
)