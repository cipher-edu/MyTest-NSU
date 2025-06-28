from django.contrib import admin, messages
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.db.models import Count
import logging
import os
from .models import *
logger = logging.getLogger(__name__)
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_max_show_all = 1000
    list_display = (
        'username', 'student_id_number', 'api_user_hash',
        'first_name', 'last_name', 'patronymic', 'full_name_api', 'short_name_api',
        'get_image_preview', 'birth_date_timestamp', 'passport_pin', 'passport_number', 'email', 'phone',
        'gender_code', 'gender_name', 'university_name_api',
        'specialty_id_api', 'specialty_code_api', 'specialty_name_api',
        'student_status_code', 'student_status_name',
        'education_form_code', 'education_form_name',
        'education_type_code', 'education_type_name',
        'payment_form_code', 'payment_form_name',
        'group_id_api', 'group_name_api', 'group_education_lang_code', 'group_education_lang_name',
        'faculty_id_api', 'faculty_name_api', 'faculty_code_api',
        'education_lang_code', 'education_lang_name',
        'level_code', 'level_name',
        'semester_id_api', 'semester_code_api', 'semester_name_api', 'semester_is_current',
        'semester_education_year_code', 'semester_education_year_name', 'semester_education_year_is_current',
        'avg_gpa', 'password_is_valid_api', 'address_api',
        'country_code_api', 'country_name_api',
        'province_code_api', 'province_name_api',
        'district_code_api', 'district_name_api',
        'social_category_code', 'social_category_name',
        'accommodation_code', 'accommodation_name',
        'validate_url_api', 'last_login_api', 'created_at', 'updated_at'
    )
    list_filter = (
        'faculty_name_api', 
        'level_name', 
        'education_form_name', 
        'student_status_name',
        'last_login_api',
        'updated_at',
        'created_at'
    )
    search_fields = (
        'username', 
        'first_name', 
        'last_name', 
        'student_id_number', 
        'full_name_api',
        'faculty_name_api', 
        'group_name_api',
        'email',
        'phone'
    )
    ordering = ('-updated_at', 'last_name', 'first_name')
    readonly_fields_list = [
        'username', 'student_id_number', 'api_user_hash',
        'first_name', 'last_name', 'patronymic', 'full_name_api', 'short_name_api',
        'get_image_preview',
        'birth_date_timestamp', 'get_birth_date_display_admin',
        'passport_pin', 'passport_number', 'email', 'phone', 
        'gender_code', 'gender_name', 'university_name_api',
        'specialty_id_api', 'specialty_code_api', 'specialty_name_api',
        'student_status_code', 'student_status_name', 'education_form_code',
        'education_form_name', 'education_type_code', 'education_type_name',
        'payment_form_code', 'payment_form_name', 'group_id_api', 'group_name_api',
        'group_education_lang_code', 'group_education_lang_name', 'faculty_id_api',
        'faculty_name_api', 'faculty_code_api', 'education_lang_code',
        'education_lang_name', 'level_code', 'level_name', 'semester_id_api',
        'semester_code_api', 'semester_name_api', 'semester_is_current',
        'semester_education_year_code', 'semester_education_year_name',
        'semester_education_year_is_current', 'avg_gpa', 'password_is_valid_api',
        'address_api', 'country_code_api', 'country_name_api', 'province_code_api',
        'province_name_api', 'district_code_api', 'district_name_api',
        'social_category_code', 'social_category_name', 'accommodation_code',
        'accommodation_name', 'validate_url_api', 
        'last_login_api_formatted_detail',
        'created_at_formatted_detail', 
        'updated_at_formatted_detail'
    ]
    readonly_fields = tuple(readonly_fields_list)

    fieldsets = (
        ('Asosiy Login Ma\'lumotlari', {
            'fields': ('username', 'student_id_number', 'api_user_hash')
        }),
        ('Shaxsiy Ma\'lumotlar (API)', {
            'fields': (
                'get_image_preview', 
                ('full_name_api', 'short_name_api'), 
                ('first_name', 'last_name', 'patronymic'),
                ('birth_date_timestamp', 'get_birth_date_display_admin'),
                'gender_name', 
                ('passport_pin', 'passport_number'), 
                'email', 'phone', 'address_api'
            )
        }),
        ('Universitet Ma\'lumotlari (API)', {
            'fields': (
                'university_name_api', 
                ('faculty_name_api', 'faculty_code_api'),
                ('specialty_name_api', 'specialty_code_api'), 
                'education_type_name', 'education_form_name',
                'education_lang_name', 'level_name', 
                ('group_name_api', 'group_education_lang_name'),
                ('semester_name_api', 'semester_is_current', 'semester_education_year_name'),
                'payment_form_name', 'student_status_name', 'avg_gpa', 
                'password_is_valid_api'
            )
        }),
        ('Manzil va Ijtimoiy Holat (API)', {
            'fields': (
                'country_name_api', 'province_name_api', 'district_name_api',
                'social_category_name', 'accommodation_name'
            )
        }),
        ('Tizim Ma\'lumotlari', {
            'fields': (
                'last_login_api_formatted_detail', 
                ('created_at_formatted_detail', 'updated_at_formatted_detail'), 
                'validate_url_api_link'
            ),
            'classes': ('collapse',),
        }),
    )

    def _format_datetime_for_admin(self, dt_value):
        if dt_value:
            local_tz = timezone.get_current_timezone()
            return timezone.localtime(dt_value, local_tz).strftime('%d-%m-%Y %H:%M:%S')
        return "Noma'lum"

    @admin.display(description='Oxirgi Kirish (API)', ordering='last_login_api')
    def last_login_api_formatted(self, obj):
        return self._format_datetime_for_admin(obj.last_login_api)
    
    @admin.display(description='Oxirgi Kirish (API)')
    def last_login_api_formatted_detail(self, obj):
        return self._format_datetime_for_admin(obj.last_login_api)

    @admin.display(description='Yaratilgan Vaqti')
    def created_at_formatted_detail(self, obj):
        return self._format_datetime_for_admin(obj.created_at)

    @admin.display(description='Yangilangan Vaqti', ordering='updated_at')
    def updated_at_formatted(self, obj):
        return self._format_datetime_for_admin(obj.updated_at)

    @admin.display(description='Yangilangan Vaqti')
    def updated_at_formatted_detail(self, obj):
        return self._format_datetime_for_admin(obj.updated_at)

    @admin.display(description='To\'liq F.I.Sh.', ordering='last_name')
    def get_full_name_display(self, obj):
        return obj.full_name_api or f"{obj.last_name or ''} {obj.first_name or ''}".strip() or obj.username

    @admin.display(description='Talabning surati ', empty_value="-Rasm yo'q-")
    def get_image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 5px;" />', obj.image_url)
        return self.get_image_preview.empty_value
    
    @admin.display(description='Tug\'ilgan sana (Formatlangan)', ordering='birth_date_timestamp')
    def get_birth_date_display_admin(self, obj):
        if obj.birth_date_timestamp:
            try:
                dt_object = timezone.datetime.fromtimestamp(obj.birth_date_timestamp, tz=timezone.get_current_timezone())
                return dt_object.strftime('%d-%m-%Y')
            except (ValueError, TypeError, OSError):
                return "Noma'lum sana (xato)"
        return "-"


    @admin.display(description='API Validatsiya Havolasi')
    def validate_url_api_link(self, obj):
        if obj.validate_url_api:
            return format_html('<a href="{0}" target="_blank">Havola</a>', obj.validate_url_api)
        return "-"

    @admin.display(description='Profil To\'liqligi', boolean=True)
    def is_profile_complete(self, obj):
        required_fields = [
            obj.first_name, obj.last_name, 
            obj.student_id_number,
            obj.faculty_name_api, obj.level_name
        ]
        return all(field is not None and str(field).strip() != '' for field in required_fields)

    actions = ['refresh_selected_students_data_from_api_action']

    @admin.action(description="Tanlangan talabalar ma'lumotlarini API dan yangilash")
    def refresh_selected_students_data_from_api_action(self, request, queryset):
        admin_api_token = getattr(settings, 'HEMIS_ADMIN_API_TOKEN', None)        
        if not admin_api_token:
            self.message_user(request, "Ma'muriy API tokeni (HEMIS_ADMIN_API_TOKEN) sozlanmalarda topilmadi.", messages.ERROR)
            return
        
        updated_count = 0
        failed_students_info = []

        if updated_count > 0:
            self.message_user(request, f"{updated_count} ta talaba ma'lumotlari muvaffaqiyatli yangilandi.", messages.SUCCESS)
        elif queryset.exists():
             self.message_user(request, "Talaba ma'lumotlarini yangilash funksiyasi to'liq sozlanmagan yoki xatolik yuz berdi.", messages.WARNING)
        else:
            self.message_user(request, "Yangilash uchun talabalar tanlanmadi.", messages.INFO)

