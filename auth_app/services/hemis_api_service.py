# auth_app/services/hemis_api_service.py
from django.conf import settings
from django.core.cache import cache
from .base_api_service import BaseAPIClient, APIClientException
import logging

logger = logging.getLogger(__name__)

class HemisAPIClient(BaseAPIClient):
    def __init__(self, api_token=None):
        super().__init__(base_url=settings.EXTERNAL_API_BASE_URL)
        if api_token:
            self.session.headers.update({'Authorization': f'Bearer {api_token}'})

    def login(self, username, password):
        """Talabani login qiladi va token qaytaradi."""
        payload = {'login': username, 'password': password}
        try:
            response_data = self.post(settings.EXTERNAL_API_LOGIN_ENDPOINT.replace(self.base_url, ''), json=payload)
            # API javobini tekshirish
            if response_data and response_data.get('success') and response_data.get('data', {}).get('token'):
                return response_data['data']['token'], response_data.get('data', {}).get('refresh_token_cookie_data') # Refresh token uchun cookie
            else:
                error_msg = (response_data.get('error') if response_data else None) or "Login muvaffaqiyatsiz (API)."
                raise APIClientException(error_msg, response_data=response_data)
        except APIClientException as e:
            # Xatolikni loglash va qayta chiqarish (yoki boshqacha qayta ishlash)
            logger.warning(f"HEMIS API Login failed for {username}: {e.args[0]}", extra={'response': e.response_data})
            raise # Xatolikni yuqoriga uzatish

    def get_account_me(self, api_token_override=None):
        """Joriy talabaning ma'lumotlarini oladi."""
        headers = {}
        if api_token_override: # Agar maxsus token berilsa (masalan, yangi olingan)
            headers['Authorization'] = f'Bearer {api_token_override}'
        
        # Cache kaliti
        # Foydalanuvchiga xos cache kaliti (agar api_token_override foydalanuvchini unikal aniqlasa)
        # Yoki, agar bu funksiya faqat o'zining tokeni bilan chaqirilsa, sessiyadagi student ID dan foydalanish mumkin
        # Hozircha oddiy cache, har bir token uchun alohida
        # cache_key = f"hemis_account_me_{hash(api_token_override or self.session.headers.get('Authorization'))}"
        # cached_data = cache.get(cache_key)
        # if cached_data:
        #     logger.debug(f"Returning cached account_me data for token hash.")
        #     return cached_data

        try:
            response_data = self.get(settings.EXTERNAL_API_ACCOUNT_ME_ENDPOINT.replace(self.base_url, ''), headers=headers)
            if response_data and response_data.get('success') and response_data.get('data'):
                # cache.set(cache_key, response_data['data'], timeout=60*15) # 15 daqiqaga keshlash
                return response_data['data']
            else:
                error_msg = (response_data.get('error') if response_data else None) or "Talaba ma'lumotlarini olishda xatolik (API)."
                raise APIClientException(error_msg, response_data=response_data)
        except APIClientException as e:
            logger.warning(f"HEMIS API get_account_me failed: {e.args[0]}", extra={'response': e.response_data})
            raise

    def refresh_auth_token(self, refresh_cookie_value):
        """Refresh token yordamida yangi access token oladi."""
        # Swaggerga ko'ra, refresh_token cookie sifatida yuboriladi.
        # Bu qism API bilan qanday ishlashiga bog'liq.
        # `requests` kutubxonasi `cookies` parametrini qo'llab-quvvatlaydi.
        # Masalan: cookies={'refresh-token': refresh_cookie_value}
        # Yoki header orqali: headers={'Cookie': f'refresh-token={refresh_cookie_value}'}
        
        # Swaggerda "Cookie" headeri ko'rsatilgan
        headers = {'Cookie': refresh_cookie_value}
        try:
            response_data = self.post(settings.EXTERNAL_API_REFRESH_TOKEN_ENDPOINT.replace(self.base_url, ''), headers=headers)
            if response_data and response_data.get('success') and response_data.get('data', {}).get('token'):
                new_access_token = response_data['data']['token']
                # Yangi refresh token cookie'si ham kelishi mumkin, uni ham qaytarish kerak
                new_refresh_cookie = response_data.get('headers', {}).get('Set-Cookie') # Yoki API javobiga qarab
                return new_access_token, new_refresh_cookie
            else:
                error_msg = (response_data.get('error') if response_data else None) or "Tokenni yangilashda xatolik (API)."
                logger.warning(f"Failed to refresh token: {error_msg}", extra={'response_data': response_data})
                raise APIClientException(error_msg, response_data=response_data)
        except APIClientException as e:
            logger.warning(f"HEMIS API refresh_auth_token failed: {e.args[0]}", extra={'response': e.response_data})
            raise
    
    # Boshqa HEMIS API endpointlari uchun metodlar shu yerga qo'shilishi mumkin
    # Masalan: get_student_schedule, get_student_grades, va hokazo.
    # Har bir metodda keshlashni ham o'ylab ko'rish kerak.