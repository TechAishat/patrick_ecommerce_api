# apiApp/paystack.py
import requests
from django.conf import settings

class Paystack:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = settings.PAYSTACK_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }

    def initialize_transaction(self, **kwargs):
        endpoint = "/transaction/initialize"
        return self._make_request("POST", endpoint, kwargs)

    def verify_transaction(self, reference):
        """Verify a transaction using the reference"""
        endpoint = f"/transaction/verify/{reference}"
        return self._make_request("GET", endpoint)

    def _make_request(self, method, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers)
            else:
                response = requests.post(url, json=data, headers=self.headers)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': False,
                'message': str(e)
            }