import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_bulk_sms(phone_numbers, message):
    """
    Send bulk SMS via EbulkSMS API (JSON).
    Accepts a list of phone numbers and a single message to broadcast.
    """
    if not settings.EBULKSMS_USERNAME or not settings.EBULKSMS_API_KEY:
        logger.error("EbulkSMS Credentials not configured")
        return False, "SMS Configuration missing"

    if not phone_numbers:
        return False, "No phone numbers provided"

    # EbulkSMS requires a unique msgid per recipient. We can just use the index.
    # Clean phone numbers (remove +, spaces). eBulkSMS can handle international formats.
    gsm_list = []
    for i, number in enumerate(phone_numbers):
        clean_number = str(number).replace('+', '').replace(' ', '').strip()
        # They usually want standard 234 formats if Nigerian without the +
        if clean_number.startswith('0') and not clean_number.startswith('00'):
            clean_number = '234' + clean_number[1:]
        gsm_list.append({
            "msidn": clean_number,
            "msgid": str(i)
        })

    payload = {
        "SMS": {
            "auth": {
                "username": settings.EBULKSMS_USERNAME,
                "apikey": settings.EBULKSMS_API_KEY
            },
            "message": {
                "sender": settings.EBULKSMS_SENDER_ID,
                "messagetext": message,
                "flash": "0"
            },
            "recipients": {
                "gsm": gsm_list
            },
            "dndsender": 1  # 1 to enable delivery to DND numbers with a fixed sender ID
        }
    }

    url = settings.EBULKSMS_API_URL
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        # EbulkSMS JSON response for success usually contains a "status" inside a "response" object
        resp_obj = data.get('response', {})
        status_flag = resp_obj.get('status')
        
        if status_flag == 'SUCCESS':
            logger.info(f"Bulk SMS sent successfully via EbulkSMS to {len(gsm_list)} numbers. Output: {resp_obj}")
            return True, resp_obj
        else:
            logger.error(f"EbulkSMS Error: {resp_obj}")
            return False, resp_obj.get('totalsms', 'Failed to send Bulk SMS')
            
    except Exception as e:
        logger.exception("Failed to send Bulk SMS via EbulkSMS")
        return False, str(e)


def send_sms(phone_number, message):
    """
    Send single SMS via EbulkSMS by wrapping it as a bulk request of length 1.
    """
    return send_bulk_sms([phone_number], message)
