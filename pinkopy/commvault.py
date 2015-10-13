from base64 import b64encode
from datetime import datetime, timedelta
import logging
import requests
import time
from urllib.parse import urlencode
import xmltodict

log = logging.getLogger(__name__)


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
        self.subclient_jobs = {}
        self.job_details = None
        self.job_vmstatus = None
        self.get_token()
        self.get_clients()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.logout()

    def request(self, method, path, qstr_vals=None, service=None,
                headers=None, payload=None, **kwargs):
        """
        Make a request to Commvault
        """
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
        except requests.exceptions.RequestException as e:
            log.error(e)

    def get_token(self):
        """
        Login to Commvault and get token
        """
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
            log.error('Commvault user or pass incorrect')
            raise ValueError('Commvault user or pass incorrect')

    def get_clients(self):
        """
        Get list of clients from Commvault
        """
        def get_from_source(**kwargs):
            log.info('Getting client list from source')
            path = 'Client'
            res = self.request('GET', path)
            data = res.json()
            self.clients_last_updated = datetime.now()
            return data['App_GetClientPropertiesResponse']['clientProperties']

        if not self.clients:
            self.clients = get_from_source(**locals())
        elif datetime.now() > self.clients_last_updated + timedelta(hours=1):
            pass

        return self.clients

    def get_client_properties(self, client_id):
        """
        Get list of clients from Commvault

        This call replies in XML, because who cares about Accept headers right.
        So, we must take the reply in XML and convert it to JSON to maintain sanity.
        """
        path = 'Client/{}'.format(client_id)
        res = self.request('GET', path)

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
            self.client_properties[client_id] = {}
            self.client_properties[client_id]['properties'] = data['App_GetClientPropertiesResponse']['clientProperties']

        if client_id not in self.client_properties:
            get_from_source(**locals())
        else:
            # We already have a good dataset. Return it.
            log.info('Using cached client jobs')

        return self.client_properties[client_id]['properties']

    def get_jobs(self, client_id, job_filter=None, last=None):
        """
        Get list of jobs for a given client and filter
        """
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

    def get_subclient_jobs(self, jobs, cust_num, last=None):
        """
        Get list of jobs relevant to a specific subclient
        given a list of jobs and Cherwell customer number
        """
        def get_from_source(**kwargs):
            """
            Retrieve new data since we do not yet
            have a matching dataset.
            """
            log.info('Getting subclient jobs from source')
            self.subclient_jobs[cust_num] = {}
            self.subclient_jobs[cust_num]['last'] = last
            self.subclient_jobs[cust_num]['jobs'] = sorted(
                [
                    job for job in jobs
                    if job['jobSummary']['subclient']['@subclientName'].split(' - ')[0] == cust_num
                ],
                key=lambda job: job['jobSummary']['@jobStartTime'],
                reverse=True
            )[:last]

        if cust_num not in self.subclient_jobs:
            get_from_source(**locals())
        elif self.subclient_jobs[cust_num]['last'] != last:
            get_from_source(**locals())
        else:
            # We already have a good dataset. Return it.
            log.info('Using cached subclient jobs')
        return self.subclient_jobs[cust_num]['jobs']

    def get_job_details(self, client_id, job_id):
        """
        Get details about a given job
        """
        path = 'JobDetails'
        payload = {
            'JobManager_JobDetailRequest': {
                '@jobId': job_id
            }
        }
        #<JobManager_JobDetailRequest jobId="2575"/>
        res = self.request('POST', path, payload=payload)
        data = res.json()
        self.job_details = data['JobManager_JobDetailResponse']['job']['jobDetail']
        return self.job_details

    def get_job_vmstatus(self, job_details):
        """
        Get all vmStatus entries for a given job
        """
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
                # Already a list, populate it
                vms = [s for s in vms]
        self.job_vmstatus = vms
        return self.job_vmstatus

    def logout(self):
        """
        End session
        """
        path = 'Logout'
        res = self.request('POST', path)
        self.headers['Authtoken'] = None
        return None
