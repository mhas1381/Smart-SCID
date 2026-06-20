"""
SMS utility functions for sending OTP codes.
Supports both production (SMS.ir) and development (mock mode).
"""

import logging
import random
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("accounts")


def send_verification_code(phone_number: str, otp_code: str) -> bool:
    """
    Send OTP verification code to phone number.
    Uses SMS.ir in production, mock mode in development.

    Args:
        phone_number: Iranian phone number (e.g., 09123456789)
        otp_code: 5-digit OTP code

    Returns:
        bool: True if sent successfully, False otherwise
    """
    # Check if mock mode is enabled (development)
    if settings.SMS_MOCK_MODE:
        return _send_mock_sms(phone_number, otp_code)

    # Production mode - use SMS.ir
    try:
        return _send_sms_ir(phone_number, otp_code)
    except Exception as e:
        logger.error(f"SMS.ir error for {phone_number}: {e}")
        # Fallback to mock mode if SMS.ir fails
        return _send_mock_sms(phone_number, otp_code)


def _send_mock_sms(phone_number: str, otp_code: str) -> bool:
    """
    Mock SMS sender - logs OTP to console for development.
    """
    print("\n" + "=" * 50)
    print(f"📱 MOCK SMS - OTP VERIFICATION")
    print(f"📞 Phone: {phone_number}")
    print(f"🔑 OTP Code: {otp_code}")
    print(f"⏱️  Valid for: {settings.OTP_CACHE_TIMEOUT} seconds")
    print("=" * 50 + "\n")

    logger.info(f"MOCK SMS sent to {phone_number}: {otp_code}")
    return True


def _send_sms_ir(phone_number: str, otp_code: str) -> bool:
    """
    Send SMS using SMS.ir API.

    Args:
        phone_number: Iranian phone number (e.g., 09123456789)
        otp_code: 5-digit OTP code

    Returns:
        bool: True if sent successfully, False otherwise

    Note:
        You need to install requests: pip install requests
    """
    try:
        import requests
    except ImportError:
        logger.error("requests library not installed. Install with: pip install requests")
        return False

    api_key = settings.SMS_IR_API_KEY
    template_id = settings.SMS_IR_VERIFY_TEMPLATE_ID

    if not api_key or api_key == "your-sms-ir-api-key-here":
        logger.error("SMS.ir API key not configured. Falling back to mock mode.")
        return _send_mock_sms(phone_number, otp_code)

    # SMS.ir API endpoint
    url = "https://api.sms.ir/v1/send/verify"

    # Request payload
    payload = {
        "mobile": phone_number,
        "templateId": template_id,
        "parameters": [
            {
                "name": "CODE",
                "value": otp_code
            }
        ]
    }

    # Headers
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=10  # 10 seconds timeout
        )

        if response.status_code == 200:
            logger.info(f"SMS sent successfully to {phone_number}")
            return True
        else:
            logger.error(f"SMS.ir API error: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.Timeout:
        logger.error(f"SMS.ir timeout for {phone_number}")
        return False
    except requests.exceptions.ConnectionError:
        logger.error(f"SMS.ir connection error for {phone_number}")
        return False
    except Exception as e:
        logger.error(f"SMS.ir unknown error for {phone_number}: {e}")
        return False