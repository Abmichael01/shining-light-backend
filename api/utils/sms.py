import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_sms(phone_number, message):
    """
    Send SMS via Termii API.
    phone_number should be in format with country code (e.g. 2348012345678)
    """
    if not settings.TERMII_API_KEY:
        logger.error("Termii API Key not configured")
        return False, "SMS Configuration missing"

    url = f"{settings.TERMII_BASE_URL}/sms/send"
    
    # Clean phone number (remove +, spaces, leading 0 if country code present)
    clean_number = phone_number.replace('+', '').replace(' ', '').strip()
    if clean_number.startswith('0') and not clean_number.startswith('00'):
        # Usually Nigerian numbers, replace leading 0 with 234
        clean_number = '234' + clean_number[1:]
    
    payload = {
        "api_key": settings.TERMII_API_KEY,
        "to": clean_number,
        "from": settings.TERMII_SENDER_ID,
        "sms": message,
        "type": "plain",
        "channel": "generic"  # or 'dnd'
    }
    
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        if response.status_code == 200:
            logger.info(f"SMS sent successfully to {clean_number}")
            return True, data
        else:
            logger.error(f"Termii Error: {data.get('message', 'Unknown error')}")
            return False, data.get('message', 'Failed to send SMS')
            
    except Exception as e:
        logger.exception("Failed to send SMS via Termii")
        return False, str(e)

def send_bulk_sms(phone_numbers, message):
    """
    Send bulk SMS via Termii API.
    Termii bulk SMS often uses the same endpoint or a specialized one.
    For simplicity, we can loop or use Termii's bulk feature if available.
    Termii's /sms/send supports single 'to'. For bulk, they have other endpoints but looping is simpler for now or use their bulk API if needed.
    """
    results = []
    for number in phone_numbers:
        success, res = send_sms(number, message)
        results.append({"number": number, "success": success, "response": res})
    return results
