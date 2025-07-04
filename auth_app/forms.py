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
class TestUploadForm(forms.ModelForm):
    """Admin panelida test yaratish va fayl yuklash uchun forma."""
    
    class Meta:
        model = Test
        fields = '__all__'

    def clean_source_file(self):
        file = self.cleaned_data.get('source_file')
        if file:
            # 1. Fayl kengaytmasini tekshirish
            ext = os.path.splitext(file.name)[1]
            if not ext.lower() == '.txt':
                raise ValidationError("Faqat .txt formatidagi fayllarni yuklash mumkin.")

            # 2. Fayl hajmini tekshirish (masalan, 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError("Fayl hajmi 5MB dan oshmasligi kerak.")

        return file