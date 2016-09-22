import logging

from .base_session import BaseSession
from .exceptions import PinkopyError, raise_requests_error

log = logging.getLogger(__name__)


class JobSession(BaseSession):
    """Methods for jobs."""
    def __init__(self, cache_methods=None, *args, **kwargs):
        cache_methods = cache_methods or ['get_job_details',
                                          'get_jobs']
        super(JobSession, self).__init__(cache_methods=cache_methods, *args, **kwargs)

    def get_jobs(self, client_id, job_filter=None, last=None):
        """Get jobs.

        Args:
            client_id (str): client id for which to get jobs
            job_filted (optional[str]): job filter, ex. backup, restore
            last (optional[int]): get this many most recent jobs

        Returns:
            list: jobs
        """
        if isinstance(client_id, int):
            log.warning('deprecated: client_id support for int for backward compatibility only')
            client_id = str(client_id)
        path = 'Job'
        qstr_vals = {
            'clientId': client_id
        }
        if job_filter is not None:
            qstr_vals['jobFilter'] = job_filter
        res = self.request('GET', path, qstr_vals=qstr_vals)
        data = res.json()
        try:
            jobs = sorted(
                data['jobs'],
                key=lambda job: job['jobSummary']['subclient']['subclientName']
            )
        except KeyError:
            jobs = sorted(
                data['JobManager_JobListResponse']['jobs'],
                key=lambda job: job['jobSummary']['subclient']['@subclientName']
            )
        if last:
            jobs = jobs[-last:]
        return jobs

    @staticmethod
    def get_subclient_jobs(jobs, subclient_id=None, subclient_name=None, last=None):
        """Get list of jobs relevant to a specific subclient.

        Args:
            jobs (list): list of jobs in which to check
            subclient_id (optional[str]): id of subclient for which to look
            subclient_name (optional[str]): name of subclient for which to look
            last (optional[int]): get this many most recent jobs

        Returns:
            list: jobs
        """
        if isinstance(subclient_id, int):
            log.warning('deprecated: subclient_id support for int for backward compatibility only')
            subclient_id = str(subclient_id) if subclient_id else None
        if subclient_id is None and subclient_name is None:
            msg = 'Cannot get subclient jobs without name or id'
            log.error(msg)
            raise PinkopyError(msg)
        elif subclient_id is not None and subclient_name is not None:
            msg = ('Cannot get subclient jobs by both name and id. '
                   'Selecting id by default.')
            log.info(msg)

        if subclient_id:
            try:
                jobs = sorted(
                    [job for job in jobs
                     if str(job['jobSummary']['subclient']['subclientId']) == subclient_id],
                    key=lambda job: job['jobSummary']['jobStartTime']
                )
            except KeyError:
                jobs = sorted(
                    [job for job in jobs
                     if str(job['jobSummary']['subclient']['@subclientId']) == subclient_id],
                    key=lambda job: job['jobSummary']['@jobStartTime']
                )
        else:
            # Could return incorrect data. If the name passed to this method
            # has more than one partial match and the correct record is not
            # first in this list, then you get the wrong jobs.
            try:
                jobs = sorted(
                    [job for job in jobs
                     if subclient_name in job['jobSummary']['subclient']['subclientName']],
                    key=lambda job: job['jobSummary']['jobStartTime']
                )
            except KeyError:
                jobs = sorted(
                    [job for job in jobs
                     if subclient_name in job['jobSummary']['subclient']['@subclientName']],
                    key=lambda job: job['jobSummary']['@jobStartTime']
                )
        if not jobs:
            msg = ('No subclient jobs found for subclient_id {} / subclient_name {}'
                   .format(subclient_id, subclient_name))
            raise_requests_error(404, msg)
        if last:
            jobs = jobs[-last:]
        return jobs

    def get_job_details(self, job_id):
        """Get details about a given job.

        Args:
            job_id (str): job id for which to get details

        Returns:
            dict: job details
        """
        if isinstance(job_id, int):
            log.warning('deprecated: job_id support for int for backward compatibility only')
            job_id = str(job_id)
        path = 'JobDetails'
        payload = {
            'JobManager_JobDetailRequest': {
                '@jobId': job_id
            }
        }
        res = self.request('POST', path, payload=payload)
        data = res.json()
        try:
            job_details = data['job']['jobDetail']
        except KeyError:
            try:
                job_details = data['JobManager_JobDetailResponse']['job']['jobDetail']
            except KeyError:
                # Make new request with xml because Commvault seems to have
                # broken the json request on this route.
                headers = self.headers.copy()
                headers['Content-type'] = 'application/xml'
                payload_nondict = ('<JobManager_JobDetailRequest jobId="{}"/>'
                                   .format(job_id))
                res = self.request('POST', path, headers=headers, payload_nondict=payload_nondict)
                data = res.json()
                job_details = data['job']['jobDetail']
        except TypeError:
            msg = 'No job details found for job {}'.format(job_id)
            raise_requests_error(404, msg)
        if not job_details:
            msg = 'No job details found for job {}'.format(job_id)
            raise_requests_error(404, msg)
        return job_details

    @staticmethod
    def get_job_vmstatus(job_details):
        """Get all vmStatus entries for a given job.

        Args:
            job_details (dict): details about a job

        Returns:
            str: vm status
        """
        try:
            vms = job_details['clientStatusInfo']['vmStatus']
        except TypeError:
            #no vmstatus
            vms = None
        if vms is not None:
            if isinstance(vms, dict):
                # Only one vmStatus
                vms = [vms]
        else:
            msg = 'No vmstatus in job details'
            raise_requests_error(404, msg)
        return vms
