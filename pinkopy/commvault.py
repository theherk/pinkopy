from base64 import b64encode
from collections import namedtuple
from datetime import datetime, timedelta
import logging
import requests
import time
from urllib.parse import urlencode
import xmltodict

log = logging.getLogger(__name__)


class PinkopyError(Exception):
    pass


def raise_requests_error(status_code, msg):
    """Raise a requests error.

    Commvault is not smart enough to return the proper error,
    specifically in the case of 404.
    """
    log.error(msg)
    res = requests.Response()
    res.status_code = status_code
    _e = requests.exceptions.HTTPError(msg)
    _e.response = res
    raise _e


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
                headers=None, payload=None, **kwargs):
        """Make a request to Commvault."""
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
            if res.status_code == 401 and headers['Authtoken'] is not None:
                # token went bad, login again
                log.info('Commvault token logged out. Logging back in.')
                # delay is so I don't get into recursion trouble if I can't login right away
                time.sleep(5)
                self.get_token()
                # We need to recall with the same request to continue.
                # Must pop self because it is passed implicitly and cannot
                # be passed twice.
                _ = locals()
                del _['self']
                return self.request(**_)
            elif res.status_code != 200:
                res.raise_for_status()
            else:
                return res
        except requests.exceptions.HTTPError as e:
            raise
        except Exception as e:
            msg = 'Pinkopy request failed.'
            log.exception(msg)
            raise PinkopyError(msg)

    def get_token(self):
        """Login to Commvault and get token."""
        path = 'Login'
        headers = self.headers
        payload = {
            'DM2ContentIndexing_CheckCredentialReq': {
                '@mode': 'Webconsole',
                '@username': self.user, 
                '@password': b64encode(self.pw.encode('UTF-8')).decode('UTF-8')
            }
        }
        res = self.request('POST', path, headers=headers, payload=payload)
        data = res.json()
        if data['DM2ContentIndexing_CheckCredentialResp'] is not None:
            self.headers['Authtoken'] = data['DM2ContentIndexing_CheckCredentialResp']['@token']
            return self.headers['Authtoken']
        else:
            msg = 'Commvault user or pass incorrect'
            raise_requests_error(401, msg)

    def get_clients(self):
        """Get list of clients from Commvault."""
        def get_from_source(**kwargs):
            log.info('Getting client list from source')
            path = 'Client'
            res = self.request('GET', path)
            data = res.json()
            return data['App_GetClientPropertiesResponse']['clientProperties']

        # Update this list at least once per hour.
        if (not self.clients
            or datetime.now() > self.clients_last_updated + timedelta(hours=1)):
            try:
                self.clients = get_from_source(**locals())
                if not self.clients:
                    msg = 'No clients found in Commvault'
                    raise_requests_error(404, msg)
                self.clients_last_updated = datetime.now()
            except Exception as e:
                msg = 'Could not retrieve clients from Commvault.'
                log.exception(msg)
                raise PinkopyError(msg)
        return self.clients

    def get_client(self, client_id):
        """Get info for one client from clients."""
        client_id = str(client_id)
        if not self.clients:
            self.get_clients()
        try:
            return list(filter(
                lambda x: x['client']['clientEntity']['@clientId'] == client_id,
                self.clients
            ))[0]
        except IndexError as e:
            msg = 'Client {} not in client list.'.format(client_id)
            raise_requests_error(404, msg)

    def get_client_properties(self, client_id):
        """Get client properties.
 
        This call replies in XML, because who cares about Accept headers right.
        So, we must take the reply in XML and convert it to JSON to maintain sanity.
        """
        client_id = str(client_id)
        def get_from_source(**kwargs):
            log.info('Getting client properties from source')
            path = 'Client/{}'.format(client_id)
            res = self.request('GET', path)
            # If you are using a version < SP12 this call will respond in
            # xml even though we are requesting json.
            if not res.json():
                # turn wrong xml into json
                data = xmltodict.parse(res.text)
            else:
                data = res.json()
            return data['App_GetClientPropertiesResponse']['clientProperties']

        if (client_id not in self.client_properties
            or datetime.now() > self.client_properties[client_id]['last_updated'] + timedelta(hours=1)):
            try:
                self.client_properties[client_id] = {
                    'properties': get_from_source(**locals()),
                    'last_updated': datetime.now()
                }
            except Exception as e:
                msg = 'Unable to get client properties for client {}'.format(client_id)
                log.exception(msg)
                raise PinkopyError(msg)
            # If receive an empty data set, send 404.
            if not self.client_properties[client_id]['properties']:
                self.client_properties.pop(client_id, None)
                msg = 'No client properties found for client {}'.format(client_id)
                raise_requests_error(404, msg)
        else:
            # We already have a good dataset. Return it.
            log.info('Using cached client properties')
        return self.client_properties[client_id]['properties']

    def get_subclients(self, client_id):
        """Get list of subclients for given client."""
        client_id = str(client_id)
        def get_from_source(**kwargs):
            log.info('Getting subclients list from source for client {}'
                     .format(client_id))
            path = 'Subclient'
            qstr_vals = {
                'clientId': client_id
            }
            res = self.request('GET', path, qstr_vals=qstr_vals)
            data = res.json()
            return data['App_GetSubClientPropertiesResponse']['subClientProperties']

        if (client_id not in self.subclients
            or datetime.now() > self.subclients[client_id]['last_updated'] + timedelta(hours=1)):
            try:
                self.subclients[client_id] = {
                    'subclients': get_from_source(**locals()),
                    'last_updated': datetime.now()
                }
            except Exception as e:
                msg = 'Unable to get subclients for client {}'.format(client_id)
                raise_requests_error(404, msg)
            if not self.subclients[client_id]['subclients']:
                self.subclients.pop(clients_id, None)
                msg = 'No subclients for client {}'.format(client_id)
                raise_requests_error(404, msg)
        else:
            # We already have a good dataset. Return it.
            log.info('Using cached subclients')
            return self.subclients[client_id]['subclients']

    def get_jobs(self, client_id, job_filter=None, last=None):
        """Get list of jobs for a given client and filter."""
        client_id = str(client_id)
        def get_from_source(**kwargs):
            log.info('Getting client jobs from source')
            path = 'Job'
            qstr_vals = {
                'clientId': client_id
            }
            if job_filter is not None:
                qstr_vals['jobFilter'] = job_filter
            res = self.request('GET', path, qstr_vals=qstr_vals)
            data = res.json()
            self.client_jobs[client_id] = {}
            self.client_jobs[client_id]['job_filter'] = job_filter
            self.client_jobs[client_id]['last'] = last
            self.client_jobs[client_id]['jobs'] = sorted(
                data['JobManager_JobListResponse']['jobs'],
                key=lambda job: job['jobSummary']['subclient']['@subclientName'],
                reverse=True
            )[:last]

        if client_id not in self.client_jobs:
            get_from_source(**locals())
        elif (self.client_jobs[client_id]['job_filter'] != job_filter
              or self.client_jobs[client_id]['last'] != last):
            get_from_source(**locals())
        else:
            # We already have a good dataset. Return it.
            log.info('Using cached client jobs')
        return self.client_jobs[client_id]['jobs']

    def get_subclient_jobs(self, jobs, subclient_id=None,
                           subclient_name=None, last=None):
        """Get list of jobs relevant to a specific subclient."""
        subclient_id = str(subclient_id) if subclient_id else None
        if (subclient_id is None and subclient_name is None):
            msg = 'Cannot get subclient jobs without name or id'
            log.error(msg)
            raise PinkopyError(msg)
        elif (subclient_id is not None and subclient_name is not None):
            msg = ('Cannot get subclient jobs by both name and id. '
                   'Selecting id by default.')
            log.info(msg)

        Subclient = namedtuple('Subclient', ['id', 'name'])

        def get_from_source_by_id(**kwargs):
            """Retrieve new data.

            Since we do not yet have a matching dataset, we must go to
            the source.
            """
            log.info('Getting subclient jobs from source using id {}'
                     .format(subclient_id))
            return sorted(
                [
                    job for job in jobs
                    if job['jobSummary']['subclient']['@subclientId'] == subclient_id
                ],
                key=lambda job: job['jobSummary']['@jobStartTime'],
                reverse=True
            )[:last]

        def get_from_source_by_name(**kwargs):
            """Retrieve new data.

            Since we do not yet have a matching dataset, we must go to
            the source.
            """
            log.info('Getting subclient jobs from source using name {}'
                     .format(subclient_name))
            return sorted(
                [
                    job for job in jobs
                    if subclient_name in job['jobSummary']['subclient']['@subclientName']
                ],
                key=lambda job: job['jobSummary']['@jobStartTime'],
                reverse=True
            )[:last]

        if subclient_id:
            try:
                subclient = [_ for _ in self.subclient_jobs if _.id == subclient_id][0]
            except IndexError as e:
                # subclient not yet cached
                subclient = None
        elif subclient_name:
            try:
                subclient = [_ for _ in self.subclient_jobs if _.name == subclient_name][0]
            except IndexError as e:
                # subclient not yet cached
                subclient = None
        if (not subclient
            or subclient['last'] != last
            or datetime.now() > subclient['last_updated'] + timedelta(hours=1)):
            _subclient_jobs = {
                'jobs': get_from_source_by_id(**locals()) if subclient_id else get_from_source_by_name(**locals()),
                'last': last,
                'last_updated': datetime.now()
            }
            try:
                subclient = Subclient(
                    id=_subclient_jobs['jobs'][0]['jobSummary']['subclient']['@subclientId'],
                    name=_subclient_jobs['jobs'][0]['jobSummary']['subclient']['@subclientName']
                )
                self.subclient_jobs[subclient] = _subclient_jobs
            except IndexError as e:
                msg = ('No subclient jobs found for subclient_id {} / subclient_name {}'
                       .format(subclient_id, subclient_name))
                raise_requests_error(404, msg)
        else:
            # We already have a good dataset. Return it.
            log.info('Using cached subclient jobs')
        return self.subclient_jobs[subclient]['jobs']

    def get_job_details(self, client_id, job_id):
        """Get details about a given job."""
        client_id = str(client_id)
        job_id = str(job_id)
        path = 'JobDetails'
        payload = {
            'JobManager_JobDetailRequest': {
                '@jobId': job_id
            }
        }
        #<JobManager_JobDetailRequest jobId="2575"/>
        res = self.request('POST', path, payload=payload)
        data = res.json()
        try:
            job_details = data['JobManager_JobDetailResponse']['job']['jobDetail']
        except TypeError as e:
            msg = 'No job details found for job {}'.format(job_id)
            raise_requests_error(404, msg)
        if not job_details:
            msg = 'No job details found for job {}'.format(job_id)
            raise_requests_error(404, msg)
        return job_details

    def get_job_vmstatus(self, job_details):
        """Get all vmStatus entries for a given job."""
        try:
            vms = job_details['clientStatusInfo']['vmStatus']
        except TypeError as e:
            #no vmstatus
            vms = None
        if vms is not None:
            if isinstance(vms, dict):
                # Only one vmStatus
                vms = [vms]
        else:
            msg = 'No vmstatus in job details'
            raise_requests_error(404, msg)
        self.job_vmstatus = vms
        return self.job_vmstatus

    def logout(self):
        """End session."""
        path = 'Logout'
        res = self.request('POST', path)
        self.headers['Authtoken'] = None
        return None
