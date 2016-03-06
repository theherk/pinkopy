from base64 import b64encode
from collections import namedtuple
from datetime import datetime, timedelta
import logging
import requests
import time
from urllib.parse import urlencode
import xmltodict

log = logging.getLogger(__name__)





    """


class CommvaultSession(object):
    def __init__(self, service, user, pw):
        self.service = service
        self.user = user
        self.pw = pw
        self.headers = {
            'Authtoken': None,
            'Accept': 'application/json',
            'Content-type': 'application/json'
        }
        self.clients = None
        self.clients_last_updated = None
        self.client_jobs = {}
        self.client_properties = {}
        self.subclients = {}
        self.subclient_jobs = {}
        self.job_vmstatus = None
        self.get_token()
        self.get_clients()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.logout()

    def request(self, method, path, qstr_vals=None, service=None,
                headers=None, payload=None, attempt=None, **kwargs):
        """Make a request to Commvault."""
        # We may need to recall the same request.
        # Must pop self because it is passed implicitly and cannot
        # be passed twice.
        _context = {k: v for k, v in locals().items() if k is not 'self'}
        allowed_attempts = 3
        attempt = 1 if not attempt else attempt

        service = service if service else self.service
        headers = headers if headers else self.headers
        try:
            if method == 'POST':
                res = requests.post(service + path, headers=headers, json=payload)
            elif method == 'GET':
                if qstr_vals is not None:
                    path += '?' + urlencode(qstr_vals)
                res = requests.get(service + path, headers=headers, params=payload)
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
                return res
        except requests.exceptions.HTTPError:
            raise
        except Exception:
            msg = 'Pinkopy request failed.'
            log.exception(msg)
            raise PinkopyError(msg)

    def get_token(self):
        """Login to Commvault and get token."""
        path = 'Login'
        payload = {
            'DM2ContentIndexing_CheckCredentialReq': {
                '@mode': 'Webconsole',
                '@username': self.user, 
                '@password': b64encode(self.pw.encode('UTF-8')).decode('UTF-8')
            }
        }
        res = self.request('POST', path, payload=payload)
        data = res.json()
        if data['DM2ContentIndexing_CheckCredentialResp'] is not None:
            self.headers['Authtoken'] = data['DM2ContentIndexing_CheckCredentialResp']['@token']
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
