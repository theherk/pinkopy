from base64 import b64encode
import inspect
import logging
import time

try:
    from urllib.parse import urlencode, urljoin
except ImportError:
    from urllib import urlencode
    from urlparse import urljoin

import xmltodict
from cachetools.func import ttl_cache
import requests
from pinkopy.exceptions import PinkopyError, raise_requests_error

log = logging.getLogger(__name__)

class BaseSession:
    """
    BaseSession class for interacting with the Commvault API.

    This class will not be instantiated directly. Other classes will inherit from this.

    Args:
        service (str): URL and path to root of API.
        user (str): Commvault username.
        pw (str): Commvault password.
        use_cache (bool, optional): Use cache? Defaults to True.
        cache_ttl (int, optional): Duration cache lives. Defaults to 1200 seconds.
        cache_methods (list, optional): List of methods to cache. Defaults to an empty list.
        token (str, optional): Auth token for headers.

    Returns:
        BaseSession: An instance of BaseSession or its subclass.
    """

    def __init__(self, service, user, pw, use_cache=True, cache_ttl=1200, cache_methods=None, token=None):
        self.service = service
        self.user = user
        self.pw = pw
        self.headers = {
            'Authtoken': token,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        if not self.headers['Authtoken']:
            self.get_token()

        self.__use_cache = use_cache
        self.__cache_ttl = cache_ttl
        self.__cache_methods = cache_methods or []

        if self.use_cache:
            for method_name in set(self.cache_methods):
                self.__enable_method_cache(method_name)

    def __enable_method_cache(self, method_name):
        """
        Enable cache for a method.

        Args:
            method_name (str): Name of the method for which to enable cache.

        Returns:
            bool: True if success, False if failed.
        """
        try:
            method = getattr(self, method_name)
            if not inspect.isfunction(method.cache_info):
                setattr(self, method_name, ttl_cache(ttl=self.cache_ttl)(method))
                return True
            return False
        except AttributeError:
            # Method doesn't exist on the class
            return False

    @property
    def use_cache(self):
        """Boolean to use cache or not."""
        return self.__use_cache

    @property
    def cache_ttl(self):
        """Duration cache lives."""
        return self.__cache_ttl

    @property
    def cache_methods(self):
        """List of methods to cache."""
        return self.__cache_methods

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.logout()

    def request(self, method, path, attempt=None, headers=None, payload=None, payload_nondict=None, qstr_vals=None, service=None):
        """
        Make an HTTP request.

        Args:
            method (str): HTTP method.
            path (str): Request path.
            attempt (int, optional): Number of request attempts.
            headers (dict, optional): Request headers. Defaults to self.headers.
            payload (dict, optional): Request payload as a dictionary.
            payload_nondict (str, optional): Request raw data payload.
            qstr_vals (dict, optional): Query string parameters to add.
            service (str, optional): URL and path to root of API. Defaults to self.service.

        Returns:
            requests.Response: Response object.

        Raises:
            PinkopyError: If an error occurs during the request.
        """
        _context = {k: v for k, v in locals().items() if k != 'self'}
        allowed_attempts = 3
        attempt = attempt or 1
        service = service or self.service
        headers = headers or self.headers
        url = urljoin(service, path)

        try:
            if method == 'POST':
                res = requests.post(url, headers=headers, data=payload_nondict) if payload_nondict else requests.post(url, headers=headers, json=payload)
            elif method == 'GET':
                if qstr_vals:
                    url += '?' + urlencode(qstr_vals)
                res = requests.get(url, headers=headers, params=payload)
            elif method == 'PUT':
                res = requests.put(url, headers=headers, json=payload)
            elif method == 'DELETE':
                res = requests.delete(url, headers=headers)
            else:
                raise ValueError(f'HTTP method {method} not supported')

            if res.status_code == 401 and headers['Authtoken'] and attempt <= allowed_attempts:
                log.info('Commvault token expired. Logging in again.')
                time.sleep(5)
                self.get_token()
                attempt += 1
                _context['attempt'] = attempt
                return self.request(**_context)
            elif attempt > allowed_attempts:
                msg = f'Could not log back into Commvault after {allowed_attempts} attempts. It could be down.'
                raise_requests_error(401, msg)
            elif res.status_code != 200:
                res.raise_for_status()
            else:
                log.info(f'request: {method} {url}')
                return res

        except requests.HTTPError as err:
            log.error(err)
            raise
        except Exception as e:
            log.exception('Pinkopy request failed.')
            raise PinkopyError('Pinkopy request failed.') from e

    def get_token(self):
        """
        Login to Commvault and get the token.

        Returns:
            str: Auth token.
        """
        path = 'Login'
        payload = {
            'mode': 4,
            'username': self.user,
            'password': b64encode(self.pw.encode('UTF-8')).decode('UTF-8')
        }
        res = self.request('POST', path, payload=payload)
        data = res.json()
        if 'token' in data and data['token']:
            self.headers['Authtoken'] = data['token']
            return self.headers['Authtoken']
        else:
            msg = 'Commvault username or password incorrect'
            raise_requests_error(401, msg)

    def logout(self):
        """
        End the session.

        Returns:
            None
        """
        path = 'Logout'
        self.request('POST', path)
        self.headers['Authtoken'] = None
        return None
