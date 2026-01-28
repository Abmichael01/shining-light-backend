import requests
from django.conf import settings

class Paystack:
    """
    Utility class for interacting with the Paystack API
    """
    PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
    BASE_URL = "https://api.paystack.co"

    def initialize_transaction(self, email, amount, reference, callback_url, metadata=None):
        """
        Initialize a transaction on Paystack
        
        Args:
            email (str): Customer's email
            amount (float): Amount to charge (in Naira). Will be converted to kobo (x100).
            reference (str): Unique transaction reference
            callback_url (str): URL to redirect to after payment
            metadata (dict, optional): Custom metadata
            
        Returns:
            dict: Initialization response (authorization_url, access_code, etc.) or None if failed
        """
        url = f"{self.BASE_URL}/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        
        # Paystack expects amount in Kobo (Naira * 100)
        amount_kobo = int(float(amount) * 100)
        
        data = {
            "email": email,
            "amount": amount_kobo,
            "reference": reference,
            "callback_url": callback_url,
        }
        
        if metadata:
            data['metadata'] = metadata
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('status'):
                return response_data['data']
            else:
                print(f"Paystack Init Error: {response_data}")
                return None
        except Exception as e:
            print(f"Paystack Init Exception: {e}")
            return None

    def verify_transaction(self, reference):
        """
        Verify a transaction on Paystack
        
        Args:
            reference (str): Transaction reference to verify
            
        Returns:
            dict: Transaction data if successful and verified, None otherwise
        """
        url = f"{self.BASE_URL}/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
        }
        
        try:
            response = requests.get(url, headers=headers)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('status'):
                data = response_data['data']
                if data.get('status') == 'success':
                    return data
            return None
        except Exception as e:
            print(f"Paystack Verify Exception: {e}")
            return None
    def create_customer(self, email, first_name, last_name, phone):
        """
        Create or fetch a customer on Paystack
        """
        url = f"{self.BASE_URL}/customer"
        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response_data = response.json()
            
            if response.status_code in [200, 201] and response_data.get('status'):
                return response_data['data'] # Contains customer_code
            return None
        except Exception as e:
            print(f"Paystack Custoemr Create Exception: {e}")
            return None

    def create_dedicated_account(self, customer_code, preferred_bank=None):
        """
        Create a dedicated virtual account (NUBAN) for a customer
        """
        url = f"{self.BASE_URL}/dedicated_account"
        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "customer": customer_code,
            "preferred_bank": "wema-bank" # Defaulting to Wema as it's common for Paystack VAs
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('status'):
                return response_data['data']
            else:
                 print(f"Paystack DVA Error: {response_data}")
                 return None
        except Exception as e:
            print(f"Paystack DVA Exception: {e}")
            return None

    def list_banks(self):
        """
        Fetch list of banks from Paystack
        """
        url = f"{self.BASE_URL}/bank"
        headers = {"Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}"}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    return data['data']
            return []
        except Exception as e:
            print(f"Paystack List Banks Error: {e}")
            return []

    def resolve_account_number(self, account_number, bank_code):
        """
        Resolve account number to get account name
        """
        url = f"{self.BASE_URL}/bank/resolve"
        headers = {"Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}"}
        params = {
            "account_number": account_number,
            "bank_code": bank_code
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    return data['data'] # Contains account_name, account_number
            return None
        except Exception as e:
            print(f"Paystack Resolve Account Error: {e}")
            return None

    def create_transfer_recipient(self, name, account_number, bank_code):
        """
        Create a transfer recipient on Paystack
        """
        url = f"{self.BASE_URL}/transferrecipient"
        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response_data = response.json()
            if response.status_code in [200, 201] and response_data.get('status'):
                return response_data['data'] # Contains recipient_code
            print(f"Paystack Recipient Error: {response_data}")
            return None
        except Exception as e:
            print(f"Paystack Recipient Exception: {e}")
            return None

    def initiate_transfer(self, amount, recipient_code, reference, reason="Staff Wallet Withdrawal"):
        """
        Initiate a transfer on Paystack
        """
        url = f"{self.BASE_URL}/transfer"
        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        
        # Paystack expects amount in Kobo
        amount_kobo = int(float(amount) * 100)
        
        data = {
            "source": "balance",
            "amount": amount_kobo,
            "recipient": recipient_code,
            "reference": reference,
            "reason": reason
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response_data = response.json()
            if response.status_code == 200 and response_data.get('status'):
                return response_data['data'] # Contains transfer_code, status
            print(f"Paystack Transfer Error: {response_data}")
            return None
        except Exception as e:
            print(f"Paystack Transfer Exception: {e}")
            return None
