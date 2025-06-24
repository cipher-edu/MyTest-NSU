# auth_app/services/base_api_service.py
import requests
import logging
from django.conf import settings
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class APIClientException(Exception):
    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class BaseAPIClient:
    def __init__(self, base_url, timeout=15, verify_ssl=None, default_headers=None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl if verify_ssl is not None else settings.REQUESTS_VERIFY_SSL
        
        self.session = requests.Session()
        if default_headers:
            self.session.headers.update(default_headers)
        
        # Qayta urinishlar strategiyasi (Retry strategy)
        retry_strategy = Retry(
            total=3, # Umumiy qayta urinishlar soni
            backoff_factor=1, # Qayta urinishlar orasidagi kutish vaqti (1s, 2s, 4s)
            status_forcelist=[429, 500, 502, 503, 504], # Qaysi status kodlarda qayta urinish
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"] # POST ni ham qo'shdik, ehtiyotkorlik bilan
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _request(self, method, endpoint, data=None, json=None, params=None, headers=None, files=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        log_extra = {"url": url, "method": method, "params": params, "data_head": str(data)[:100] if data else None, "json_head": str(json)[:100] if json else None}
        logger.debug(f"API Request: {log_extra}")

        try:
            response = self.session.request(
                method, url,
                data=data, json=json, params=params,
                headers=request_headers, files=files,
                timeout=self.timeout, verify=self.verify_ssl
            )
            logger.debug(f"API Response: Status {response.status_code}, URL: {url}, Content head: {response.text[:200]}")
            response.raise_for_status() # HTTP xatolar uchun exception chiqaradi
            
            # Content-Type ni tekshirish (agar javob bo'sh bo'lmasa)
            if response.content and 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            elif response.ok and not response.content: # Muvaffaqiyatli, lekin bo'sh javob (masalan, 204 No Content)
                return None
            return response.text # Agar JSON bo'lmasa, matnni qaytaradi
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            response_data = None
            try:
                response_data = e.response.json() if e.response and e.response.content else e.response.text[:200]
            except ValueError: # Javob JSON emas
                response_data = e.response.text[:200] if e.response else "No response body"
            
            error_message = f"API HTTP Error {status_code} on {url}"
            if response_data:
                 api_err = response_data.get('error') or response_data.get('message') or response_data.get('detail')
                 if api_err:
                     error_message = str(api_err) # API xabarini ishlatamiz

            logger.error(f"{error_message}. Response data: {response_data}", exc_info=True, extra=log_extra)
            raise APIClientException(error_message, status_code=status_code, response_data=response_data) from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"API Connection Error on {url}: {e}", exc_info=True, extra=log_extra)
            raise APIClientException(f"API serveriga ulanishda xatolik: {url}", status_code=503) from e # 503 Service Unavailable
        except requests.exceptions.Timeout as e:
            logger.error(f"API Timeout on {url}: {e}", exc_info=True, extra=log_extra)
            raise APIClientException(f"API serveridan javob kutish vaqti tugadi: {url}", status_code=504) from e # 504 Gateway Timeout
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request Exception on {url}: {e}", exc_info=True, extra=log_extra)
            raise APIClientException(f"API so'rovida noma'lum xatolik: {url}", status_code=500) from e

    def get(self, endpoint, params=None, headers=None):
        return self._request("GET", endpoint, params=params, headers=headers)

    def post(self, endpoint, data=None, json=None, params=None, headers=None, files=None):
        return self._request("POST", endpoint, data=data, json=json, params=params, headers=headers, files=files)

    # Boshqa metodlar (PUT, DELETE, ...) ham qo'shilishi mumkin