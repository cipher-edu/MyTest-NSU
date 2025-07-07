import ipaddress
import logging
import qrcode
from io import BytesIO
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
from .models import *
from .services.hemis_api_service import HemisAPIClient, APIClientException

logger = logging.getLogger(__name__)
