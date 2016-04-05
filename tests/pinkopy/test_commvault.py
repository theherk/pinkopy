import unittest

import requests_mock

from pinkopy import CommvaultSession
from tests.pinkopy import test_helper


class TestCommvaultSessionMethods(unittest.TestCase):
    def test__init__(self):
        expected = test_helper.mock_session(CommvaultSession)
        commvault = expected['Session']

        # validate shim
        assert commvault.get_client == commvault.clients.get_client
        assert commvault.get_client_properties == commvault.clients.get_client_properties
        assert commvault.get_clients == commvault.clients.get_clients
        assert commvault.get_subclients == commvault.subclients.get_subclients
        assert commvault.get_job_details == commvault.jobs.get_job_details
        assert commvault.get_job_vmstatus == commvault.jobs.get_job_vmstatus
        assert commvault.get_jobs == commvault.jobs.get_jobs
        assert commvault.get_subclient_jobs == commvault.jobs.get_subclient_jobs
        assert commvault.clients.__class__.__name__ == 'ClientSession'
        assert commvault.jobs.__class__.__name__ == 'JobSession'
        assert commvault.subclients.__class__.__name__ == 'SubclientSession'
        test_helper.validate_base_session(expected, commvault.clients)
        test_helper.validate_base_session(expected, commvault.jobs)
        test_helper.validate_base_session(expected, commvault.subclients)

    def test__enter__(self):
        session = test_helper.mock_session(CommvaultSession)['Session']
        assert session == session.__enter__()

    def test_logout(self):
        test_data = test_helper.mock_session(CommvaultSession)
        session = test_data['Session']
        with requests_mock.mock() as m:
            service = test_data['Service']
            m.post(service + '/Logout', headers={}, json={})
            result = session.logout()
            assert result is None
            assert session.headers['Authtoken'] is None


if __name__ == '__main__':
    unittest.main()
