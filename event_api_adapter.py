import requests
import logging
from commons import get_env_var

logger = logging.getLogger(__file__)

BASE_API_URL = get_env_var("API_URL") + "/internal"

def api_request(fun):
    def wrap(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except Exception as e:
            logger.error(f"Event API request failed: {str(e)}")
        
    return wrap

class EventAPIAdapter:
    def __init__(self, authorization):
        self.secret_key = authorization
    
    @api_request
    def post_created(self, post_id):
        res = requests.post(f"{BASE_API_URL}/post/created/{post_id}", headers=self.authorization_header)
        return res

    @property
    def authorization_header(self):
        return {
            "Authorization": f"Bearer {self.secret_key}"
        }
    @authorization_header.setter
    def authorization_header(self, value):
        pass