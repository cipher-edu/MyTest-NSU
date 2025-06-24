from django.utils import timezone
import logging
logger = logging.getLogger(__name__)
def get_nested(data, keys, default=None):
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current and current[key] is not None:
            current = current[key]
        else:
            return default
    return current
def map_api_data_to_student_model_defaults(api_data, current_username_or_id_number):
    if not isinstance(api_data, dict):
        logger.error(f"map_api_data_to_student_model_defaults kutgan ma'lumot dict emas, balki: {type(api_data)}. Ma'lumot: {str(api_data)[:200]}")
        return {}
    defaults = {
        'student_id_number': api_data.get('student_id_number', current_username_or_id_number),
        'api_user_hash': api_data.get('hash'),
        'first_name': api_data.get('first_name'),
        'last_name': api_data.get('second_name'),
        'patronymic': api_data.get('third_name'),
        'full_name_api': api_data.get('full_name'),
        'short_name_api': api_data.get('short_name'),
        'image_url': api_data.get('image'),
        'birth_date_timestamp': api_data.get('birth_date'),
        'passport_pin': api_data.get('passport_pin'),
        'passport_number': api_data.get('passport_number'),
        'email': api_data.get('email'),
        'phone': api_data.get('phone'),
        'gender_code': get_nested(api_data, ['gender', 'code']),
        'gender_name': get_nested(api_data, ['gender', 'name']),
        'address_api': api_data.get('address'),
        'university_name_api': api_data.get('university'),
        'specialty_id_api': get_nested(api_data, ['specialty', 'id']),
        'specialty_code_api': get_nested(api_data, ['specialty', 'code']),
        'specialty_name_api': get_nested(api_data, ['specialty', 'name']),
        'student_status_code': get_nested(api_data, ['studentStatus', 'code']),
        'student_status_name': get_nested(api_data, ['studentStatus', 'name']),
        'education_form_code': get_nested(api_data, ['educationForm', 'code']),
        'education_form_name': get_nested(api_data, ['educationForm', 'name']),
        'education_type_code': get_nested(api_data, ['educationType', 'code']),
        'education_type_name': get_nested(api_data, ['educationType', 'name']),
        'payment_form_code': get_nested(api_data, ['paymentForm', 'code']),
        'payment_form_name': get_nested(api_data, ['paymentForm', 'name']),
        'group_id_api': get_nested(api_data, ['group', 'id']),
        'group_name_api': get_nested(api_data, ['group', 'name']),
        'group_education_lang_code': get_nested(api_data, ['group', 'educationLang', 'code']),
        'group_education_lang_name': get_nested(api_data, ['group', 'educationLang', 'name']),
        'faculty_id_api': get_nested(api_data, ['faculty', 'id']),
        'faculty_name_api': get_nested(api_data, ['faculty', 'name']),
        'faculty_code_api': get_nested(api_data, ['faculty', 'code']),
        'education_lang_code': get_nested(api_data, ['educationLang', 'code']),
        'education_lang_name': get_nested(api_data, ['educationLang', 'name']),
        'level_code': get_nested(api_data, ['level', 'code']),
        'level_name': get_nested(api_data, ['level', 'name']),
        'semester_id_api': get_nested(api_data, ['semester', 'id']),
        'semester_code_api': get_nested(api_data, ['semester', 'code']),
        'semester_name_api': get_nested(api_data, ['semester', 'name']),
        'semester_is_current': get_nested(api_data, ['semester', 'current']),
        'semester_education_year_code': get_nested(api_data, ['semester', 'education_year', 'code']),
        'semester_education_year_name': get_nested(api_data, ['semester', 'education_year', 'name']),
        'semester_education_year_is_current': get_nested(api_data, ['semester', 'education_year', 'current']),
        'avg_gpa': api_data.get('avg_gpa'),
        'password_is_valid_api': api_data.get('password_valid'),
        'country_code_api': get_nested(api_data, ['country', 'code']),
        'country_name_api': get_nested(api_data, ['country', 'name']),
        'province_code_api': get_nested(api_data, ['province', 'code']),
        'province_name_api': get_nested(api_data, ['province', 'name']),
        'district_code_api': get_nested(api_data, ['district', 'code']),
        'district_name_api': get_nested(api_data, ['district', 'name']),
        'social_category_code': get_nested(api_data, ['socialCategory', 'code']),
        'social_category_name': get_nested(api_data, ['socialCategory', 'name']),
        'accommodation_code': get_nested(api_data, ['accommodation', 'code']),
        'accommodation_name': get_nested(api_data, ['accommodation', 'name']),
        'validate_url_api': api_data.get('validateUrl'),
        'last_login_api': timezone.now(),
    }
    return defaults
def update_student_instance_with_defaults(student_instance, defaults):
    has_changed = False
    for key, value in defaults.items():
        if hasattr(student_instance, key) and getattr(student_instance, key) != value:
            setattr(student_instance, key, value)
            has_changed = True
    if has_changed:
        student_instance.save() 
        logger.info(f"Student instance {student_instance.username} (ID: {student_instance.id}) updated with new API data.")
    else:
        if defaults.get('last_login_api') and student_instance.last_login_api != defaults.get('last_login_api'):
             student_instance.last_login_api = defaults.get('last_login_api')
             student_instance.save(update_fields=['last_login_api', 'updated_at'])
             logger.info(f"Student instance {student_instance.username} (ID: {student_instance.id}) last_login_api updated.")
        else:
            logger.info(f"No changes detected for student instance {student_instance.username} (ID: {student_instance.id}) based on API data.")
    return student_instance
import logging
from django.utils import timezone
from django.conf import settings
from .services.hemis_api_service import HemisAPIClient, APIClientException
def _handle_api_token_refresh(request):
    refresh_cookie = request.session.get('hemis_refresh_cookie')
    current_token_expiry = request.session.get('api_token_expiry_timestamp')
    needs_refresh = not current_token_expiry or \
                    current_token_expiry <= timezone.now().timestamp() + getattr(settings, 'API_TOKEN_REFRESH_THRESHOLD_SECONDS', 300)
    if not refresh_cookie or not needs_refresh:
        return True
    logger.info(f"Attempting to refresh API token for session: {request.session.session_key}")
    api_client = HemisAPIClient()
    try:
        new_access_token, new_refresh_cookie_data = api_client.refresh_auth_token(refresh_cookie)
        request.session['api_token'] = new_access_token
        expires_in = settings.SESSION_COOKIE_AGE
        if isinstance(new_refresh_cookie_data, dict) and 'expires_in' in new_refresh_cookie_data:
            try:
                expires_in = int(new_refresh_cookie_data['expires_in'])
            except (ValueError, TypeError):
                logger.warning("Invalid 'expires_in' value from API response.")
        request.session['api_token_expiry_timestamp'] = timezone.now().timestamp() + expires_in
        if isinstance(new_refresh_cookie_data, str):
            request.session['hemis_refresh_cookie'] = new_refresh_cookie_data
        elif isinstance(new_refresh_cookie_data, dict) and 'refresh_cookie' in new_refresh_cookie_data:
            request.session['hemis_refresh_cookie'] = new_refresh_cookie_data['refresh_cookie']
        logger.info("API token successfully refreshed.")
        return True
    except APIClientException as e:
        logger.error(f"Failed to refresh API token: {e}")
        request.session.flush()
        return False
    except Exception as e:
        logger.critical(f"Unexpected error during token refresh: {e}", exc_info=True)
        request.session.flush()
        return False
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

def generate_qr_code_image(data, prefix=""):
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    filename = f"{prefix}{data}_qr.png"
    return ContentFile(buffer.getvalue(), name=filename)