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

from .exceptions import PinkopyError, raise_requests_error

log = logging.getLogger(__name__)


class BaseSession(object):
    """BaseSession

    This will not be instantiated directly. Other classes will inherit from this.

    Args:
        service (optional[str]): URL and path to root of api
        user (str): Commvault username
        pw (str): Commvault password
        use_cache (optional[bool]): Use cache? Defaults to False
        cache_ttl (optional[int]): Duration cache lives. Defaults to 1200.
        cache_methods (optional[int]): List of methods to cache.
            Defaults provided by the inheriting classes.
        token (optional[str]): Authtoken for header

    Returns:
        session object
    """
    def __init__(self, service, user, pw, use_cache=True, cache_ttl=1200,
                 cache_methods=None, token=None):
        self.service = service
        self.user = user
        self.pw = pw
        self.headers = {
            'Authtoken': token,
            'Accept': 'application/json',
            'Content-type': 'application/json'
        }
        if not self.headers['Authtoken']:
            self.get_token()
        self.__use_cache = bool(use_cache)
        self.__cache_ttl = cache_ttl
        self.__cache_methods = cache_methods or []

        if self.use_cache:
            for method_name in set(self.cache_methods):
                self.__enable_method_cache(method_name)

    def __enable_method_cache(self, method_name):
        """Enable cache for a method.

        Args:
            method_name (str): name of method for which to enable cache

        Returns:
            bool: True is success, False if failed
        """
        try:
            method = getattr(self, method_name)
            try:
                return not inspect.isfunction(method.cache_info)
            except AttributeError:
                setattr(self, method_name, ttl_cache(ttl=self.cache_ttl)(method))
                return True
        except AttributeError:
            # method doesn't exist on initializing class
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

    def request(self, method, path, attempt=None, headers=None, payload=None,
                payload_nondict=None, qstr_vals=None, service=None):
        """Make request.

        Args:
            method (str): HTTP method
            path (str): request path
            attempt (int): Number of request attempts
            headers (optional[dict]): headers if provided else self.headers
            payload (optional[dict]): payload as dictionary
            payload_nondict (optional[str]): payload raw data
            qstr_vals (optional[dict]): query string parameters to add
            service (optional[str]): URL and path to root of api

        Returns:
            response object
        """
        # We may need to recall the same request.
        # Must pop self because it is passed implicitly and cannot be passed twice.
        _context = {k: v for k, v in locals().items() if k is not 'self'}
        allowed_attempts = 3
        attempt = 1 if not attempt else attempt
        service = service if service else self.service
        headers = headers if headers else self.headers
        url = urljoin(service, path)
        try:
            if method == 'POST':
                if payload_nondict:
                    res = requests.post(url, headers=headers, data=payload_nondict)
                else:
                    res = requests.post(url, headers=headers, json=payload)
            elif method == 'GET':
                if qstr_vals is not None:
                    url += '?' + urlencode(qstr_vals)
                res = requests.get(url, headers=headers, params=payload)
            elif method == 'PUT':
                res = requests.put(url, headers=headers, json=payload)
            elif method == 'DELETE':
                res = requests.delete(url, headers=headers)
            else:
                raise ValueError('HTTP method {} not supported'.format(method))
            if (res.status_code == 401
                and headers['Authtoken'] is not None
                and attempt <= allowed_attempts):
                # Token went bad, login again.
                log.info('Commvault token logged out. Logging back in.')
                # Delay is so I don't get into recursion trouble if I can't login right away.
                time.sleep(5)
                self.get_token()
                # Recall the same function, after having logged back into Commvault.
                attempt += 1
                _context['attempt'] = attempt
                return self.request(**_context)
            elif attempt > allowed_attempts:
                # Commvault probably down, raise exception.
                msg = ('Could not log back into Commvault after {} '
                       'attempts. It could be down.'
                       .format(allowed_attempts))
                raise_requests_error(401, msg)
            elif res.status_code != 200:
                res.raise_for_status()
            else:
                log.info('request: {} {}'.format(method, url))
                return res
        except requests.HTTPError as err:
            log.error(err)
            raise
        except Exception:
            msg = 'Pinkopy request failed.'
            log.exception(msg)
            raise PinkopyError(msg)

    def get_token(self):
        """Login to Commvault and get token.

        Returns:
            str: token
                Also, sets Authtoken in default headers.
        """
        path = 'Login'
        payload = {
            'mode': 4,
            'username': self.user,
            'password': b64encode(self.pw.encode('UTF-8')).decode('UTF-8')}
        res = self.request('POST', path, payload=payload)
        data = res.json()
        if 'token' in data and data['token']:
            self.headers['Authtoken'] = data['token']
            return self.headers['Authtoken']
        else:
            msg = 'Commvault user or pass incorrect'
            raise_requests_error(401, msg)

    def logout(self):
        """End session."""
        path = 'Logout'
        self.request('POST', path)
        self.headers['Authtoken'] = None
        return None
