from django.contrib import admin, messages
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.db.models import Count
import logging
import os
from .models import *


from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from .models import *
from .forms import TestUploadForm # Keyingi qadamda yaratiladi
from .tasks import process_test_file_task # Keyingi qadamda yaratiladi
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

# admin.py fayliga qo'shiladi


# Mavjud StudentAdmin sinfi o'zgarishsiz qoldiriladi
# ...

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('name', 'code')

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name', 'id')

@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name', 'id')

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name', 'id')

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1
    fields = ('text', 'is_correct')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'test', 'question_type', 'points')
    list_filter = ('test', 'question_type')
    search_fields = ('text', 'test__title')
    inlines = [AnswerInline]

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('text', 'question_type', 'points', 'order')
    show_change_link = True
    readonly_fields = ('text',) # Savollar fayldan yaratiladi, qo'lda o'zgartirilmaydi

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    form = TestUploadForm # Fayl yuklash logikasi uchun maxsus forma
    list_display = ('title', 'status', 'creator', 'start_time', 'end_time', 'time_limit', 'question_count', 'max_score_display')
    list_filter = ('status', 'creator', 'created_at', 'faculties', 'specialties')
    search_fields = ('title', 'description', 'creator__username')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('title', 'description', 'creator', 'status')}),
        ("Fayl orqali savollarni yuklash", {'fields': ('source_file',)}),
        ("Vaqt va qoidalar", {'fields': ('start_time', 'end_time', 'time_limit', 'allow_once', 'randomize_questions', 'allowed_ips')}),
        ("Ruxsatlar (Fakultet, Yo'nalish, Guruh, Kurs)", {'fields': ('faculties', 'specialties', 'groups', 'levels')}),
    )
    
    # Katta hajmdagi ma'lumotlar uchun `raw_id_fields` yoki `filter_horizontal`
    filter_horizontal = ('faculties', 'specialties', 'groups', 'levels')
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            num_questions=models.Count('questions')
        )
    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'allowed_ips':
            field.help_text += " Masalan: 192.168.1.1, 192.168.1.2"
        return field

    @admin.display(description="Savollar soni", ordering='num_questions')
    def question_count(self, obj):
        return obj.num_questions

    @admin.display(description="Maksimal ball")
    def max_score_display(self, obj):
        return obj.max_score

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Faqat yangi obyekt yaratilganda
            obj.creator = request.user
        
        # Fayl yuklangan bo'lsa, Celery vazifasini ishga tushiramiz
        if 'source_file' in form.changed_data and form.cleaned_data['source_file']:
            obj.status = Test.Status.PROCESSING # Holatni "qayta ishlanmoqda" ga o'tkazamiz
            super().save_model(request, obj, form, change) # Avval testni saqlaymiz
            
            # Celery task ni chaqirish
            process_test_file_task.delay(obj.id)
            
            self.message_user(request, "Fayl qabul qilindi va savollarni yaratish uchun navbatga qo'yildi. "
                                       "Jarayon bir necha daqiqa vaqt olishi mumkin.", messages.INFO)
        else:
            super().save_model(request, obj, form, change)

class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    readonly_fields = ('question', 'chosen_answer', 'is_correct_display')
    can_delete = False

    @admin.display(description="To'g'rimi?", boolean=True)
    def is_correct_display(self, obj):
        if obj.chosen_answer:
            return obj.chosen_answer.is_correct
        return None

@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('student', 'test', 'score', 'start_time', 'end_time', 'is_completed')
    list_filter = ('test', 'is_completed', 'student__faculty_name_api')
    search_fields = ('student__full_name_api', 'student__username', 'test__title')
    readonly_fields = ('student', 'test', 'start_time', 'end_time', 'score')
    inlines = [StudentAnswerInline]
    actions = ['mark_responses_as_completed']

    @admin.action(description="Отметить выбранные ответы как завершенные")
    def mark_responses_as_completed(self, request, queryset):
        not_completed_count = queryset.filter(is_completed=False).count()
        updated = queryset.filter(is_completed=False).update(
            is_completed=True, 
            end_time=timezone.now()
        )

        # Пересчитываем баллы для каждого ответа
        for response in queryset.filter(is_completed=True):
            response.calculate_score()
            response.save()

        if updated:
            self.message_user(
                request, 
                f"{updated} ответов на тест успешно отмечены как завершенные и оценены.", 
                messages.SUCCESS
            )
        elif not_completed_count == 0:
            self.message_user(
                request, 
                "Выбранные ответы уже были отмечены как завершенные.", 
                messages.INFO
            )
        else:
            self.message_user(
                request, 
                "Произошла ошибка при обновлении статуса ответов.", 
                messages.ERROR
            )